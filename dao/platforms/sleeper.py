__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import datetime
import json
import logging
from collections import defaultdict, Counter
from copy import deepcopy
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from statistics import median
from typing import Union, Callable

from dao.base import BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from dao.platforms.base.base import BaseLeagueData
from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)

# Suppress Sleeper API debug logging
logger.setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class LeagueData(BaseLeagueData):

    def __init__(self, base_dir: Union[Path, None], data_dir: Path, league_id: str,
                 season: int, start_week: int, week_for_report: int, get_current_nfl_week_function: Callable,
                 week_validation_function: Callable, save_data: bool = True, offline: bool = False):
        super().__init__(
            "Sleeper",
            f"https://api.sleeper.app",
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

        self.api_base_url = f"{self.base_url}/v1"
        self.api_stats_and_projections_base_url = self.base_url

        self.league_scoring = None
        self.standings = None
        self.player_data = None
        self.player_stats_data_by_week = None
        self.player_projected_stats_data_by_week = None

    def query_with_delayed_refresh(self, url: str, save_file: Path, check_for_saved_data: bool = False,
                                   refresh_days_delay: int = 1):
        if check_for_saved_data:
            if not Path(save_file).exists():
                logger.debug(f"File {save_file.name} does not exist... attempting data retrieval.")
            else:
                file_modified_timestamp = datetime.fromtimestamp(Path(save_file).stat().st_mtime)
                if file_modified_timestamp < (datetime.today() - timedelta(days=refresh_days_delay)):
                    if not self.league.offline:
                        logger.debug(
                            f"Data in {save_file.name} over {refresh_days_delay} "
                            f"day{'s' if refresh_days_delay > 1 else ''} old... refreshing."
                        )
                    else:
                        logger.debug(
                            f"Data in {save_file.name} over {refresh_days_delay} "
                            f"day{'s' if refresh_days_delay > 1 else ''} old but offline=True... skipping refresh."
                        )
                else:
                    logger.debug(f"Data in {save_file.name} still recent... skipping refresh.")
                    with open(save_file, "r") as saved_data:
                        response_json = json.load(saved_data)
                    return response_json

        response_json = self.query(url, save_file)
        return response_json

    def _fetch_player_data(self, player_id, week, starter=False):
        # handle the move of the Raiders from Oakland (OAK) to Las Vegas (LV) between the 2019 and 2020 seasons
        if player_id == "OAK":
            player_id = "LV"
        player = deepcopy(self.player_data.get(str(player_id)))
        if int(week) <= self.league.week_for_report:
            player["stats"] = deepcopy(self.player_stats_data_by_week.get(str(week)).get(str(player_id)))
            player["projected"] = deepcopy(self.player_projected_stats_data_by_week[str(week)].get(str(player_id)))
            player["starter"] = starter
        return player

    def _map_player_data_to_matchup(self, matchup, week):
        for team in matchup:
            for ranked_team in self.standings:
                if ranked_team.get("roster_id") == team.get("roster_id"):
                    team["info"] = {
                        k: v for k, v in ranked_team.items() if k not in ["taxi", "starters", "reserve", "players"]
                    }

            if team["starters"] and team["players"]:
                team["roster"] = [
                    self._fetch_player_data(player_id, week, True) if player_id in team["starters"] else
                    self._fetch_player_data(player_id, week) for player_id in team["players"]
                ]
            elif not team["starters"] and team["players"]:
                team["roster"] = [
                    self._fetch_player_data(player_id, week) for player_id in team["players"]
                ]
            else:
                team["roster"] = []

        return matchup

    def _get_player_points(self, stats, projected_stats):
        points = 0
        if stats:
            for stat, value in stats.items():
                if stat in self.league_scoring.keys():
                    points += (value * self.league_scoring.get(stat))

        projected_points = 0
        if projected_stats:
            for stat, value in projected_stats.items():
                if stat in self.league_scoring.keys():
                    projected_points += (value * self.league_scoring.get(stat))

        return round(points, 2), round(projected_points, 2)

    def map_data_to_base(self):
        logger.debug(f"Retrieving {self.platform_display} league data and mapping it to base objects.")

        league_info = self.query_with_delayed_refresh(
            f"{self.api_base_url}/league/{self.league.league_id}",
            (Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id)
             / f"{self.league.league_id}-league_info.json")
        )

        league_settings = league_info.get("settings")
        self.league_scoring = league_info.get("scoring_settings")

        num_regular_season_weeks: int = (
            (int(league_settings.get("playoff_week_start")) - 1)
            if league_settings.get("playoff_week_start") > 0
            else settings.num_regular_season_weeks
        )

        league_managers = {
            manager.get("user_id"): manager for manager in self.query_with_delayed_refresh(
                f"{self.api_base_url}/league/{self.league.league_id}/users",
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-league_managers.json")
            )
        }

        self.standings = sorted(
            self.query_with_delayed_refresh(
                f"{self.api_base_url}/league/{self.league.league_id}/rosters",
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-league_standings.json")
            ),
            key=lambda x: (
                x.get("settings").get("wins"),
                -x.get("settings").get("losses"),
                x.get("settings").get("ties"),
                float(str(x.get("settings").get("fpts")) + "." + (str(x.get("settings").get("fpts_decimal") if x.get(
                    "settings").get("fpts_decimal") else "0")))
            ),
            reverse=True
        )

        for team in self.standings:
            team["owner"] = league_managers.get(team.get("owner_id"))
            team["co_owners"] = [league_managers.get(co_owner) for co_owner in team.get("co_owners")] if team.get(
                "co_owners") else []

        self.player_data = self.query_with_delayed_refresh(
            f"{self.api_base_url}/players/nfl",
            (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
             / f"{self.league.league_id}-player_data.json"),
            check_for_saved_data=True,
            refresh_days_delay=7
        )

        self.player_stats_data_by_week = {}
        self.player_projected_stats_data_by_week = {}
        for week_for_player_stats in range(self.start_week, num_regular_season_weeks + 1):
            if int(week_for_player_stats) <= self.league.week_for_report:
                self.player_stats_data_by_week[str(week_for_player_stats)] = {
                    player["player_id"]: player["stats"] for player in self.query_with_delayed_refresh(
                        (f"{self.api_stats_and_projections_base_url}"
                         f"/stats/nfl/{self.league.season}/{week_for_player_stats}?season_type=regular"),
                        (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                         / f"week_{week_for_player_stats}" / f"week_{week_for_player_stats}-player_stats_by_week.json"),
                        check_for_saved_data=True,
                        refresh_days_delay=1
                    )
                }

            self.player_projected_stats_data_by_week[str(week_for_player_stats)] = {
                player["player_id"]: player["stats"] for player in self.query_with_delayed_refresh(
                    (f"{self.api_stats_and_projections_base_url}"
                     f"/projections/nfl/{self.league.season}/{week_for_player_stats}?season_type=regular"),
                    (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                     / f"week_{week_for_player_stats}"
                     / f"week_{week_for_player_stats}-player_projected_stats_by_week.json"),
                    check_for_saved_data=True,
                    refresh_days_delay=1
                )
            }

        matchups_by_week = {}
        median_score_by_week = {}
        for week_for_matchups in range(self.start_week, num_regular_season_weeks + 1):
            matchups_by_week[str(week_for_matchups)] = [
                self._map_player_data_to_matchup(list(group), week_for_matchups) for key, group in groupby(
                    sorted(
                        self.query_with_delayed_refresh(
                            f"{self.api_base_url}/league/{self.league.league_id}/matchups/{week_for_matchups}",
                            (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                             / f"week_{week_for_matchups}" / f"week_{week_for_matchups}-matchups_by_week.json")
                        ),
                        key=lambda x: x["matchup_id"]
                    ),
                    key=lambda x: x["matchup_id"]
                )
            ]

            if int(week_for_matchups) <= self.league.week_for_report:
                scores = []
                for matchup in matchups_by_week[str(week_for_matchups)]:
                    for team in matchup:

                        team_custom_points = team["custom_points"]
                        if team_custom_points:
                            team_custom_points = round(team_custom_points, 2)
                            logger.warning(
                                f"Team \"{team['info']['owner']['metadata']['team_name']}\" points manually overridden "
                                f"by commissioner for week {week_for_matchups}: {team['points']} "
                                f"-> {team_custom_points}"
                            )
                            matchup[matchup.index(team)]["points"] = team_custom_points
                            team_score = team_custom_points
                        else:
                            team_score = team["points"]
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    median_score_by_week[str(week_for_matchups)] = weekly_median
                else:
                    median_score_by_week[str(week_for_matchups)] = 0

        rosters_by_week = {}
        for week_for_rosters in range(self.start_week, self.league.week_for_report + 1):
            team_rosters = {}
            for matchup in matchups_by_week[str(week_for_rosters)]:
                for team in matchup:
                    team_rosters[team["roster_id"]] = team["roster"]

            rosters_by_week[str(week_for_rosters)] = team_rosters

        league_transactions_by_week = {}
        for week_for_transactions in range(self.start_week, self.league.week_for_report + 1):
            league_transactions_by_week[str(week_for_transactions)] = defaultdict(lambda: defaultdict(list))
            weekly_transactions = self.query_with_delayed_refresh(
                f"{self.api_base_url}/league/{self.league.league_id}/transactions/{week_for_transactions}",
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"week_{week_for_transactions}" / f"week_{week_for_transactions}-transactions_by_week.json")
            )

            for transaction in weekly_transactions:
                if transaction.get("status") == "complete":
                    transaction_type = transaction.get("type")
                    if transaction_type in ["waiver", "free_agent", "trade"]:
                        for team_roster_id in transaction.get("consenter_ids"):
                            if transaction_type == "waiver":
                                league_transactions_by_week[str(week_for_transactions)][str(team_roster_id)][
                                    "moves"].append(transaction)
                            elif transaction_type == "free_agent":
                                league_transactions_by_week[str(week_for_transactions)][str(team_roster_id)][
                                    "moves"].append(transaction)
                            elif transaction_type == "trade":
                                league_transactions_by_week[str(week_for_transactions)][str(team_roster_id)][
                                    "trades"].append(transaction)

        player_season_stats = {
            player["player_id"]: player["stats"] for player in self.query_with_delayed_refresh(
                f"{self.api_stats_and_projections_base_url}/stats/nfl/{self.league.season}?season_type=regular",
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-player_season_stats.json"),
                check_for_saved_data=True,
                refresh_days_delay=1
            )
        }

        player_season_projected_stats = {
            player["player_id"]: player["stats"] for player in self.query_with_delayed_refresh(
                (f"{self.api_stats_and_projections_base_url}/projections/nfl/{self.league.season}"
                 f"?season_type=regular"),
                (Path(self.league.data_dir) / str(self.league.season) / self.league.league_id
                 / f"{self.league.league_id}-player_season_projected_stats.json"),
                check_for_saved_data=True,
                refresh_days_delay=1
            )
        }

        self.league.name = league_info.get("name")
        self.league.week = self.current_week
        # TODO: figure out how to get league starting week
        self.league.start_week = self.start_week
        self.league.season = int(league_info.get("season"))  # this gets set already in BaseLeague by the run parameters
        self.league.num_teams = int(league_settings.get("num_teams"))
        self.league.num_playoff_slots = int(league_settings.get("playoff_teams"))
        self.league.num_regular_season_weeks = num_regular_season_weeks
        self.league.num_divisions = int(league_settings.get("divisions", 0))
        # TODO: missing division names
        self.league.divisions = {}
        self.league.has_divisions = self.league.num_divisions > 0
        self.league.has_median_matchup = bool(league_settings.get("league_average_match"))
        self.league.median_score = 0
        self.league.faab_budget = int(league_settings.get("waiver_budget"))
        self.league.is_faab = self.league.faab_budget > 0
        self.league.url = f"https://sleeper.app/leagues/{self.league.league_id}"

        # TODO: hook up to collected player stats by week
        # self.league.player_data_by_week_function = None
        # self.league.player_data_by_week_key = None

        for position, count in dict(Counter(league_info.get("roster_positions"))).items():
            pos_attributes = self.position_mapping.get(position)
            pos_name = pos_attributes.get("base")
            pos_count = count

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

        league_median_records_by_team = {}
        for week, matchups in matchups_by_week.items():
            matchups_week = str(week)
            self.league.teams_by_week[str(week)] = {}
            self.league.matchups_by_week[str(week)] = []

            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = int(matchups_week)
                # TODO: because Sleeper doesn't tell current week of selected season, check current vs. previous season
                #  and use month to determine if it's first or second year within same season and mark matchups from
                #  previous years complete by default for the sake of this functionality working
                current_date = datetime.today()
                if current_date.month < 9 and self.league.season < (current_date.year - 1):
                    base_matchup.complete = True
                elif self.league.season < current_date.year:
                    base_matchup.complete = True
                else:
                    base_matchup.complete = int(week) <= self.league.week
                base_matchup.tied = True if matchup[0].get("points") and matchup[1].get("points") and float(
                    matchup[0].get("points")) == float(matchup[1].get("points")) else False

                for team in matchup:
                    team_info = team.get("info")
                    team_settings = team_info.get("settings")
                    base_team = BaseTeam()

                    base_team.team_id = team.get("roster_id")

                    opposite_key = 1 if matchup.index(team) == 0 else 0
                    team_standings_info = None
                    opposite_team_standings_info = None
                    team_rank = None
                    for roster in self.standings:
                        if int(roster.get("roster_id")) == int(base_team.team_id):
                            team_standings_info = roster
                            team_rank = int(self.standings.index(roster) + 1)
                        elif int(roster.get("roster_id")) == int(matchup[opposite_key].get("roster_id")):
                            opposite_team_standings_info = roster

                    team_division = None
                    if self.league.has_divisions:
                        team_division = team_standings_info.get("settings").get("division")
                        opponent_division = opposite_team_standings_info.get("settings").get("division")
                        if team_division and opponent_division and team_division == opponent_division:
                            base_matchup.division_matchup = True

                    base_team.week = int(matchups_week)

                    if team_info.get("owner"):
                        base_team.name = team_info.get("owner").get("metadata").get("team_name") if team_info.get(
                            "owner").get("metadata").get("team_name") else team_info.get("owner").get("display_name")
                    else:
                        base_team.name = f"Team #{team_info.get('roster_id')}"

                    if team_info.get("owner"):
                        for manager in [team_info.get("owner")] + team_info.get("co_owners"):
                            base_manager = BaseManager()

                            base_manager.manager_id = manager.get("user_id")
                            base_manager.email = None
                            base_manager.name = manager.get("display_name")

                            base_team.managers.append(base_manager)
                    else:
                        base_manager = BaseManager()

                        base_manager.manager_id = "N/A"
                        base_manager.email = None
                        base_manager.name = "N/A"

                        base_team.managers.append(base_manager)

                    # base_team.manager_str = ", ".join([manager.name for manager in base_team.managers])
                    base_team.manager_str = (
                        team_info.get("owner").get("display_name") if team_info.get("owner") else "N/A"
                    )
                    base_team.points = round(float(team.get("points")), 2) if team.get("points") else 0
                    base_team.num_moves = sum(
                        len(league_transactions_by_week
                            .get(str(week), {})
                            .get(str(base_team.team_id), {})
                            .get("moves", []))
                        for week in range(self.start_week, int(week) + 1)
                    )
                    base_team.num_trades = sum(
                        len(league_transactions_by_week
                            .get(str(week), {})
                            .get(str(base_team.team_id), {})
                            .get("trades", []))
                        for week in range(self.start_week, int(week) + 1)
                    )

                    base_team.waiver_priority = team_settings.get("waiver_position")
                    self.league.has_waiver_priorities = base_team.waiver_priority > 0
                    base_team.faab = self.league.faab_budget - int(team_settings.get("waiver_budget_used", 0))
                    base_team.url = None

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(team_settings.get("wins")),
                        losses=int(team_settings.get("losses")),
                        ties=int(team_settings.get("ties")),
                        percentage=(
                            round(
                                float(
                                    int(team_settings.get("wins")) /
                                    (int(team_settings.get("wins"))
                                     + int(team_settings.get("losses"))
                                     + int(team_settings.get("ties")))
                                ), 3
                            )
                            if (int(team_settings.get("wins"))
                                + int(team_settings.get("losses"))
                                + int(team_settings.get("ties"))) > 0
                            else 0.0
                        ),
                        points_for=float(
                            f"{team_settings.get('fpts')}.{team_settings.get('fpts_decimal')}"
                            if team_settings.get("fpts_decimal")
                            else "0"
                        ),
                        points_against=float(
                            f"{team_settings.get('fpts_against') if team_settings.get('fpts_against') else '0'}"
                            f"."
                            f"{team_settings.get('fpts_against_decimal') if team_settings.get('fpts_against_decimal') else '0'}"
                        ),
                        streak_type=None,
                        streak_len=0,
                        team_id=base_team.team_id,
                        team_name=base_team.name,
                        rank=team_rank
                    )
                    if self.league.has_divisions:
                        base_team.current_record.division = base_team.division

                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if self.league.has_divisions:
                        if base_matchup.division_matchup:
                            base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = median_score_by_week.get(matchups_week)

                    median_record: BaseRecord = league_median_records_by_team.get(str(base_team.team_id))
                    if not median_record:
                        median_record = BaseRecord(
                            team_id=base_team.team_id,
                            team_name=base_team.name
                        )
                        league_median_records_by_team[str(base_team.team_id)] = median_record

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
                        if base_team.team_id == matchup[0].get("roster_id"):
                            if matchup[0].get("points") and matchup[1].get("points") and float(
                                    matchup[0].get("points")) > float(matchup[1].get("points")):
                                base_matchup.winner = base_team
                            else:
                                base_matchup.loser = base_team
                        elif base_team.team_id == matchup[1].get("roster_id"):
                            if matchup[1].get("points") and matchup[0].get("points") and float(
                                    matchup[1].get("points")) > float(matchup[0].get("points")):
                                base_matchup.winner = base_team
                            else:
                                base_matchup.loser = base_team

                # add matchup to league matchups by week
                self.league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in rosters_by_week.items():
            self.league.players_by_week[str(week)] = {}
            team_count = 1
            for team_id, roster in rosters.items():
                league_team: BaseTeam = self.league.teams_by_week.get(str(week)).get(str(team_id))

                team_filled_positions = []
                for position in league_info.get("roster_positions"):
                    team_filled_positions.append(self.get_mapped_position(position))

                for player in roster:
                    if player:
                        base_player = BasePlayer()

                        base_player.week_for_report = int(week)
                        base_player.player_id = player.get("player_id")
                        # TODO: use week WITHOUT projections (Ex.: 11: null) to determine player bye week
                        base_player.bye_week = None
                        base_player.display_position = self.get_mapped_position(player.get("position"))
                        base_player.nfl_team_id = None
                        base_player.nfl_team_abbr = player.get("team")
                        # TODO: no full team name for player
                        base_player.nfl_team_name = player.get("team")
                        if base_player.display_position == "D/ST":
                            base_player.first_name = f"{player.get('first_name')} {player.get('last_name')}"
                            base_player.full_name = base_player.first_name
                            base_player.nfl_team_name = base_player.first_name
                            base_player.headshot_url = (
                                f"https://sleepercdn.com/images/team_logos/nfl/{str(base_player.player_id).lower()}.png"
                            )
                        else:
                            base_player.first_name = player.get("first_name")
                            base_player.last_name = player.get("last_name")
                            base_player.full_name = player.get("full_name")
                            base_player.headshot_url = (
                                f"https://sleepercdn.com/content/nfl/players/thumb/{str(base_player.player_id)}.jpg"
                            )
                        base_player.owner_team_id = None
                        base_player.owner_team_id = None
                        base_player.percent_owned = None

                        player_stats = player.get("stats")
                        base_player.points, base_player.projected_points = self._get_player_points(
                            stats=player_stats,
                            projected_stats=player.get("projected")
                        )

                        base_player.season_points, base_player.season_projected_points = self._get_player_points(
                            stats=player_season_stats[str(base_player.player_id)]
                            if str(base_player.player_id) in player_season_stats.keys() else [],
                            projected_stats=player_season_projected_stats[str(base_player.player_id)]
                            if str(base_player.player_id) in player_season_projected_stats.keys() else []
                        )

                        base_player.position_type = (
                            "O" if base_player.display_position in self.league.offensive_positions else "D"
                        )
                        base_player.primary_position = self.get_mapped_position(player.get("position"))

                        eligible_positions = player.get("fantasy_positions")
                        if len(eligible_positions) > 1:
                            player["multiple_non_flex_positions"] = True
                        for position in eligible_positions:
                            base_position = self.get_mapped_position(position)
                            base_player.eligible_positions.add(base_position)
                            for flex_position, positions in self.league.get_flex_positions_dict().items():
                                if base_position in positions:
                                    base_player.eligible_positions.add(flex_position)

                        if player["starter"]:

                            if (not player.get("roster_assignation_delayed", False)
                                    and player.get("multiple_non_flex_positions", False)):
                                player["roster_assignation_delayed"] = True
                                roster.append(player)
                                continue

                            available_primary_slots = list(
                                base_player.eligible_positions
                                .intersection(set(team_filled_positions))
                                .difference(set([
                                    pos.get("base")
                                    for pos in self.position_mapping.values()
                                    if pos.get("is_flex")
                                ]))
                            )

                            available_wrrb_flex_slots = list(
                                base_player.eligible_positions
                                .intersection(set(self.league.flex_positions_rb_wr))
                            )

                            available_rec_flex_slots = list(
                                base_player.eligible_positions
                                .intersection(set(self.league.flex_positions_te_wr))
                            )

                            available_flex_slots = list(
                                base_player.eligible_positions
                                .intersection(set(self.league.flex_positions_rb_te_wr))
                            )

                            available_super_flex_slots = list(
                                base_player.eligible_positions
                                .intersection(set(self.league.flex_positions_qb_rb_te_wr))
                            )

                            available_idp_flex_slots = list(
                                base_player.eligible_positions
                                .intersection(set(self.league.flex_positions_idp))
                            )

                            if len(available_primary_slots) > 0:
                                if base_player.primary_position in available_primary_slots:
                                    base_player.selected_position = base_player.primary_position
                                else:
                                    base_player.selected_position = available_primary_slots[0]
                                base_player.selected_position_is_flex = False
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            elif len(available_wrrb_flex_slots) > 0 and "FLEX_RB_WR" in team_filled_positions:
                                base_player.selected_position = "FLEX_RB_WR"
                                base_player.selected_position_is_flex = True
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            elif len(available_rec_flex_slots) > 0 and "FLEX_TE_WR" in team_filled_positions:
                                base_player.selected_position = "FLEX_TE_WR"
                                base_player.selected_position_is_flex = True
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            elif len(available_flex_slots) > 0 and "FLEX" in team_filled_positions:
                                base_player.selected_position = "FLEX"
                                base_player.selected_position_is_flex = True
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            elif len(available_super_flex_slots) > 0 and "SUPERFLEX" in team_filled_positions:
                                base_player.selected_position = "SUPERFLEX"
                                base_player.selected_position_is_flex = True
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            elif len(available_idp_flex_slots) > 0 and "FLEX_IDP" in team_filled_positions:
                                base_player.selected_position = "FLEX_IDP"
                                base_player.selected_position_is_flex = True
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            else:
                                logger.debug(f"\n{json.dumps(player, indent=2)}")
                                raise ValueError("Player position missing! Check data!")
                            league_team.projected_points += base_player.projected_points
                        else:
                            base_player.selected_position = "BN"
                            base_player.selected_position_is_flex = False

                        base_player.status = player.get("status")

                        if player_stats:
                            for stat, value in player_stats.items():
                                base_stat = BaseStat()

                                base_stat.stat_id = None
                                base_stat.name = stat
                                base_stat.value = value

                                base_player.stats.append(base_stat)

                        # add player to team roster
                        league_team.roster.append(base_player)

                        # add player to league players by week
                        self.league.players_by_week[str(week)][base_player.player_id] = base_player

                team_count += 1

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
