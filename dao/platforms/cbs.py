import json
import logging
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Callable, Dict, Any

import requests

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseManager, BaseRecord, BasePlayer, BaseStat
from dao.platforms.base.base import BaseLeagueData
from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)

# Suppress gitpython debug logging
logging.getLogger("git.cmd").setLevel(level=logging.WARNING)
logging.getLogger("git.cmd.cmd.execute").setLevel(level=logging.WARNING)


# noinspection DuplicatedCode
class LeagueData(BaseLeagueData):

    def __init__(self, base_dir: Path, data_dir: Path, league_id: str, season: int,
                 start_week: int, week_for_report: int, get_current_nfl_week_function: Callable,
                 week_validation_function: Callable, save_data: bool = True, offline: bool = False):
        super().__init__(
            "CBS",
            f"https://{league_id}.football.cbssports.com",
            base_dir,
            data_dir,
            league_id,
            season,
            start_week,
            week_for_report,
            get_current_nfl_week_function,
            week_validation_function,
            save_data,
            offline
        )

        # the mobile authentication API endpoint uses the old API base URL
        self.auth_base_url = "https://api.cbssports.com"
        # the old API URL is not currently used but is included for informational purposes
        self.old_api_base_url = f"{self.auth_base_url}/fantasy"
        # the new API uses the league ID and sport in the base URL
        self.api_base_url = f"{self.base_url}/api"

        self.access_token = self.check_auth()

        self.query_headers = {
            "User-Agent": "Fantasy FB/5 CFNetwork/1410.0.3 Darwin/22.6.0",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Authorization": self.access_token
        }

    def check_auth(self) -> str:

        auth_json = None
        cbs_auth_file = Path(self.base_dir) / settings.platform_settings.cbs_auth_dir_local_path / "private.json"
        if Path(cbs_auth_file).is_file():
            with open(cbs_auth_file, "r") as auth_file:
                auth_json = json.load(auth_file)

        if auth_json.get("access_token"):
            return auth_json.get("access_token")
        else:
            auth_query_headers = {
                "User-Agent": "Fantasy FB/5 CFNetwork/1410.0.3 Darwin/22.6.0",
                "Content-Type": "application/json",
                "Accept": "*/*"
            }

            auth_query_data = json.dumps({
                "client_id": "cbssports",
                "client_secret": "sportsallthetime",
                "user_id": auth_json.get("user_id"),
                "password": auth_json.get("password")
            })

            auth_url = f"{self.auth_base_url}/general/oauth/mobile/login?response_format=json"

            response_json = requests.post(auth_url, headers=auth_query_headers, data=auth_query_data).json()

            access_token = response_json.get("body").get("access_token")
            auth_json["access_token"] = access_token

            with open(cbs_auth_file, "w") as auth_file:
                json.dump(auth_json, auth_file, indent=2)

            return access_token

    def build_api_url(self, route: str, additional_parameters: Dict[str, Any] = None):
        api_url_query_parameters = f"version=3.0&response_format=json&sport=football&league_id={self.league.league_id}"

        if additional_parameters:
            additional_parameters_str = "&".join([f"{k}={v}" for k, v in additional_parameters.items()])
            return f"{self.api_base_url}{route}?{api_url_query_parameters}&{additional_parameters_str}"
        else:
            return f"{self.api_base_url}{route}?{api_url_query_parameters}"

    @staticmethod
    def extract_integer(input_with_embedded_int: Any):
        return int("".join(filter(str.isdigit, str(input_with_embedded_int))))

    def map_data_to_base(self) -> BaseLeague:
        logger.debug(f"Retrieving {self.platform_display} league data and mapping it to base objects.")

        league_details = self.query(
            self.build_api_url("/league/details"),
            (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
             / f"{self.league.league_id}-details.json"),
            self.query_headers
        ).get("body").get("league_details")

        league_rules = self.query(
            self.build_api_url("/league/rules"),
            (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
             / f"{self.league.league_id}-rules.json"),
            self.query_headers
        ).get("body").get("rules")

        self.league.name = league_details.get("name")
        self.league.week = int(league_details.get("current_period")) or self.current_week
        # TODO: figure out how to get CBS league start week
        self.league.start_week = self.start_week
        self.league.num_teams = int(league_details.get("num_teams"))
        self.league.num_playoff_slots = int(
            league_rules.get("schedule").get("num_playoff_teams", {"value": 0}).get("value")
        )
        self.league.num_regular_season_weeks = int(league_details.get("regular_season_periods"))
        self.league.num_divisions = int(league_details.get("num_divisions", 0))
        self.league.divisions = {}
        self.league.has_divisions = self.league.num_divisions > 0
        # self.league.has_median_matchup = self.has_median_matchup
        self.league.median_score = 0
        self.league.faab_budget = self.extract_integer(
            league_rules.get("transactions").get("add_drop_faab_starting_budget", {"value": 0}).get("value")
        )
        self.league.is_faab = self.league.faab_budget > 0
        self.league.url = self.base_url

        # self.league.player_data_by_week_function = None
        # self.league.player_data_by_week_key = None

        # add bench/IR positions to roster
        for position in league_rules.get("roster").get("statuses"):
            if position.get("description") == "Reserve Players":
                self.league.roster_positions.append("BN")
                self.league.roster_position_counts["BN"] = int(position.get("max"))

            if position.get("description") == "Injured Players":
                self.league.roster_positions.append("IR")
                self.league.roster_position_counts["IR"] = int(position.get("max"))

        # add starting positions to roster
        for position in league_rules.get("roster").get("positions"):
            pos_attributes = self.position_mapping.get(position.get("abbr"))
            pos_name = pos_attributes.get("base")
            pos_count = int(position.get("max_active"))

            if pos_attributes.get("is_flex"):
                self.league.__setattr__(
                    pos_attributes.get("league_positions_attribute"),
                    pos_attributes.get("positions")
                )

            self.league.roster_positions.append(pos_name)
            self.league.roster_position_counts[pos_name] = pos_count
            self.league.roster_active_slots.extend(
                [pos_name] * pos_count
                if pos_name not in self.league.bench_positions
                else []
            )

        league_schedule = self.query(
            self.build_api_url("/league/schedules", additional_parameters={"period": "all"}),
            (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
             / f"{self.league.league_id}-season_matchup_schedule.json"),
            self.query_headers
        ).get("body").get("schedule").get("periods")

        league_teams = {
            t.get("id"): t for t in self.query(
                self.build_api_url("/league/teams"),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-teams.json"),
                self.query_headers
            ).get("body").get("teams")
        }

        waiver_key = "faab_order" if self.league.is_faab else "waiver_order"
        league_waivers = {
            t.get("id"): t for t in self.query(
                self.build_api_url("/league/transactions/waiver-order"),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-waivers.json"),
                self.query_headers
            ).get("body").get(waiver_key).get("teams")
        }

        league_team_rosters_weekly_scoring = {
            str(p.get("id")): p for p in self.query(
                self.build_api_url(
                    "/league/fantasy-points/weekly-scoring",
                    additional_parameters={"team_type": "roster", "team_id": "all"}
                ),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-weekly_scoring.json"),
                self.query_headers
            ).get("body").get("weekly_scoring").get("players")
        }

        league_transactions = self.query(
            self.build_api_url(
                "/league/transaction-list/log", additional_parameters={"filter": "all_but_lineup"}
            ),
            (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
             / f"{self.league.league_id}-transactions.json"),
            self.query_headers
        ).get("body").get("transaction_log")

        league_stat_categories = {
            s.get("abbr"): s for s in self.query(
                self.build_api_url("/stats/categories"),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-stat_categories.json"),
                self.query_headers
            ).get("body").get("stats_categories")
        }

        nfl_teams = {
            t.get("abbr"): t for t in self.query(
                self.build_api_url("/pro-teams"),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-nfl_teams.json"),
                self.query_headers
            ).get("body").get("pro_teams")
        }

        nfl_player_injuries = {
            str(p.get("player").get("id")): p for p in self.query(
                self.build_api_url("/players/injuries"),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-nfl_player_injuries.json"),
                self.query_headers
            ).get("body").get("injuries")
        }

        rosters_by_week: Dict[str, Dict] = defaultdict(dict)
        matchups_by_week: Dict[str, Dict] = defaultdict(dict)
        standings_by_week: Dict[str, Dict] = defaultdict(dict)
        median_score_by_week: Dict[str, float] = {}
        for wk in range(self.start_week, self.league.num_regular_season_weeks + 1):

            if wk <= int(self.league.week_for_report):

                league_rosters = self.query(
                    self.build_api_url("/league/rosters", additional_parameters={"team_id": "all", "period": wk}),
                    (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id / f"week_{wk}"
                     / f"week_{wk}-rosters.json"),
                    self.query_headers
                ).get("body").get("rosters").get("teams")

                league_player_stats = self.query(
                    self.build_api_url(
                        "/stats",
                        additional_parameters={"timeframe": self.league.season, "period": wk}
                    ),
                    (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id / f"week_{wk}"
                     / f"week_{wk}-player_stats.json"),
                    self.query_headers
                ).get("body").get("player_stats")

                for team in league_rosters:
                    for player in team.get("players", []):
                        player["weekly_scoring"] = league_team_rosters_weekly_scoring.get(str(player.get("id")))
                        player["stats"] = league_player_stats.get(str(player.get("id")), {})

                rosters_by_week[str(wk)] = {str(team.get("id")): team for team in league_rosters}

                league_weekly_matchups = None
                for weekly_matchups in league_schedule:
                    if self.extract_integer(weekly_matchups.get("label")) == wk:
                        league_weekly_matchups = weekly_matchups

                matchups_by_week[str(wk)] = league_weekly_matchups

                league_standings = self.query(
                    self.build_api_url("/league/standings/overall", additional_parameters={"period": wk}),
                    (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id / f"week_{wk}"
                     / f"week_{wk}-standings.json"),
                    self.query_headers
                ).get("body").get("overall_standings")
                if self.league.has_divisions:
                    league_standings = [
                        team for division in league_standings.get("divisions") for team in division.get("teams")
                    ]
                else:
                    league_standings = league_standings.get("teams")

                standings_by_week[str(wk)] = {str(team.get("id")): team for team in league_standings}

                scores = []
                for matchup in league_weekly_matchups.get("matchups"):
                    for key in ["home_team", "away_team"]:
                        if "points" in matchup.get(key):
                            scores.append(float(matchup.get(key).get("points")))
                        if "division" in matchup.get(key):
                            division = matchup.get(key).get("division")
                            self.league.divisions[division] = division

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    median_score_by_week[str(wk)] = weekly_median
                else:
                    median_score_by_week[str(wk)] = 0

        team_records_with_median = {}
        for week, matchups in matchups_by_week.items():
            matchups_week = self.extract_integer(matchups.get("label"))
            matchups = matchups.get("matchups")

            self.league.teams_by_week[str(week)] = {}
            self.league.matchups_by_week[str(week)] = []

            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = matchups_week
                base_matchup.complete = matchups_week < self.league.week
                base_matchup.tied = matchup.get("home_team").get("points") == matchup.get("away_team").get("points")

                for key in ["home_team", "away_team"]:
                    team_data: Dict = matchup.get(key)
                    team_id = str(team_data.get("id"))
                    base_team = BaseTeam()

                    opposite_key = "away_team" if key == "home_team" else "home_team"

                    base_team.division = str(team_data.get("division", None))

                    team_division = league_teams[team_id].get("division")
                    opponent_division = league_teams[matchup.get(opposite_key).get("id")].get("division")
                    if (team_division is not None
                            and opponent_division is not None
                            and team_division == opponent_division
                    ):
                        base_matchup.division_matchup = True

                    base_team.week = matchups_week
                    base_team.name = team_data.get("name")

                    managers = league_teams[team_id].get("owners")
                    if managers:
                        for manager in managers:
                            base_manager = BaseManager()

                            base_manager.manager_id = str(manager.get("id"))
                            base_manager.email = None
                            base_manager.name = manager.get("name")

                            base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name_str for manager in base_team.managers])

                    base_team.team_id = team_id
                    base_team.points = float(matchup.get(key).get("points", 0.0))
                    base_team.projected_points = 0.0
                    for p in rosters_by_week[week][team_id].get("players", []):
                        if p.get("roster_status") == "A":
                            base_team.projected_points += float(p.get("projected_points"))

                    base_team.num_moves = 0
                    base_team.num_trades = 0
                    for tx in league_transactions:
                        if tx.get("team").get("id") == team_id:
                            for move in tx.get("moves"):
                                if move.get("type") == "won" or move.get("type") == "drop":
                                    base_team.num_moves += 1
                                elif move.get("type") == "trade":
                                    base_team.num_trades += 1

                    base_team.waiver_priority = league_waivers.get(team_id).get("order", 0)
                    self.league.has_waiver_priorities = base_team.waiver_priority > 0
                    base_team.faab = self.extract_integer(league_waivers.get(team_id).get("budget_remaining", "0"))
                    base_team.url = f"{self.league.url}/teams/{team_id}"

                    team_standings = standings_by_week[week].get(team_id)
                    if str(team_standings.get("streak")).startswith("W"):
                        streak_type = "W"
                    elif str(team_standings.get("streak")).startswith("L"):
                        streak_type = "L"
                    elif str(team_standings.get("streak")).startswith("T"):
                        streak_type = "T"
                    else:
                        streak_type = "T"

                    base_team.current_record = BaseRecord(
                        wins=int(team_standings.get("wins", 0)),
                        losses=int(team_standings.get("losses", 0)),
                        ties=int(team_standings.get("ties", 0)),
                        percentage=round(float(team_standings.get("winning_pct", 0.0)), 3),
                        points_for=float(team_standings.get("points_scored", 0)),
                        points_against=float(team_standings.get("points_against", 0)),
                        streak_type=streak_type,
                        streak_len=int(self.extract_integer(team_standings.get("streak", "0"))),
                        team_id=base_team.team_id,
                        team_name=base_team.name,
                        rank=int(team_standings.get("order", 0)),
                        division=base_team.division,
                        division_wins=int(team_standings.get("division_wins", 0)),
                        division_losses=int(team_standings.get("division_losses", 0)),
                        division_ties=int(team_standings.get("division_ties", 0)),
                        division_percentage=round(
                            float(
                                team_standings.get("division_wins", 0)
                                / (team_standings.get("division_wins")
                                   + team_standings.get("division_ties")
                                   + team_standings.get("division_losses"))
                            ), 3
                        ) if (team_standings.get("division_wins")
                              + team_standings.get("division_ties")
                              + team_standings.get("division_losses")
                              ) > 0 else 0.0
                    )
                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if base_matchup.division_matchup:
                        base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median: float = median_score_by_week[str(week)]

                    median_record: BaseRecord = team_records_with_median.get(base_team.team_id)
                    if not median_record:
                        median_record = BaseRecord(
                            team_id=base_team.team_id,
                            team_name=base_team.name
                        )
                        team_records_with_median[base_team.team_id] = median_record

                    if week_median:
                        # use this if you want the tie-break to be season total points over/under median score
                        median_record.add_points_for(base_team.points - week_median)
                        # use this if you want the tie-break to be current week points over/under median score
                        # median_record.add_points_for(
                        #     (median_record.get_points_for() * -1) + (base_team.points - week_median))
                        median_record.add_points_against((median_record.get_points_against() * -1) + week_median)
                        if base_team.points > week_median:
                            median_record.add_win()
                        elif base_team.points < week_median:
                            median_record.add_loss()
                        else:
                            median_record.add_tie()

                        base_team.current_median_record = median_record

                    # add team to matchup teams
                    base_matchup.teams.append(base_team)

                    # add team to league teams by week
                    self.league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # no winner/loser if matchup is tied
                    if not base_matchup.tied:
                        if team_data.get("result") == "W":
                            base_matchup.winner = base_team
                        elif team_data.get("result") == "L":
                            base_matchup.loser = base_team

                # add matchup to league matchups by week
                self.league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in rosters_by_week.items():
            self.league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():

                league_team: BaseTeam = self.league.teams_by_week.get(str(week)).get(team_id)
                for player in roster.get("players"):
                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = player.get("id")
                    base_player.bye_week = int(player.get("bye_week"))
                    base_player.display_position = self.get_mapped_position(player.get("position"))
                    base_player.nfl_team_id = None
                    base_player.nfl_team_abbr = player.get("pro_team")
                    base_player.nfl_team_name = (
                        f"{nfl_teams.get(player.get('pro_team')).get('name')} "
                        f"{nfl_teams.get(player.get('pro_team')).get('nickname')}"
                    )
                    base_player.first_name = player.get("firstname")
                    base_player.last_name = player.get("lastname")
                    base_player.full_name = player.get("fullname")
                    base_player.headshot_url = player.get("photo")

                    if player.get("owned_by_team_id", None):
                        base_player.owner_team_id = player.get("owned_by_team_id")
                        base_player.owner_team_name = league_teams.get(str(player.get("owned_by_team_id"))).get("name")
                    else:
                        base_player.owner_team_id = team_id
                        base_player.owner_team_id = league_teams.get(team_id).get("name")
                    base_player.percent_owned = self.extract_integer(player.get("percentowned", "0"))

                    if not player.get("weekly_scoring"):
                        player["weekly_scoring"] = {
                            str(p.get("id")): p for p in self.query(
                                self.build_api_url(
                                    "/league/fantasy-points/weekly-scoring",
                                    additional_parameters={"player_id": base_player.player_id}
                                ),
                                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                                 / f"team_{league_team.team_id}"
                                 / f"player_{base_player.player_id}-weekly_scoring.json"),
                                self.query_headers
                            ).get("body").get("weekly_scoring").get("players")
                        }.get(base_player.player_id)

                    for weekly_points in player.get("weekly_scoring").get("periods"):
                        if int(weekly_points.get("period")) == int(week):
                            base_player.points = float(weekly_points.get("score"))

                    base_player.projected_points = float(player.get("projected_points"))
                    base_player.season_points = float(player.get("weekly_scoring").get("total"))
                    base_player.season_average_points = round(float(player.get("weekly_scoring").get("avg")), 2)

                    for position in player.get("weekly_scoring").get("player").get("eligible_positions"):
                        base_player.eligible_positions.add(self.get_mapped_position(position))

                    base_player.primary_position = self.get_mapped_position(player.get("position"))
                    base_player.position_type = (
                        "O" if self.get_mapped_position(player.get("position")) in self.league.offensive_positions
                        else "D"
                    )

                    player_roster_status = player.get("roster_status")
                    if player_roster_status in ["RS", "I"]:
                        player_selected_position = player.get("roster_status")
                    else:
                        player_selected_position = player.get("roster_pos")
                    base_player.selected_position = self.get_mapped_position(player_selected_position)
                    base_player.selected_position_is_flex = (
                        self.position_mapping.get(player_selected_position).get("is_flex")
                    )

                    if base_player.player_id in nfl_player_injuries:
                        base_player.status = nfl_player_injuries.get(base_player.player_id).get("status_full")

                    for stat_abbr, stat_value in player.get("stats").items():
                        base_stat = BaseStat()

                        if stat_abbr in league_stat_categories:
                            stat_name = league_stat_categories.get(stat_abbr).get("name")
                        else:
                            stat_name = stat_abbr

                        base_stat.stat_id = None
                        base_stat.name = stat_name
                        base_stat.abbreviation = stat_abbr
                        base_stat.value = stat_value

                        base_player.stats.append(base_stat)

                    # add player to team roster
                    league_team.roster.append(base_player)

                    # add player to league players by week
                    self.league.players_by_week[str(week)][base_player.player_id] = base_player

        self.league.current_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: x.current_record.rank
        )

        self.league.current_median_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: (
                x.current_median_record.get_wins(),
                -x.current_median_record.get_losses(),
                x.current_median_record.get_ties(),
                x.current_median_record.get_points_for()
            ),
            reverse=True
        )

        return self.league
