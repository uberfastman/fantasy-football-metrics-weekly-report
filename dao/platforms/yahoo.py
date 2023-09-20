__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import logging
from copy import deepcopy
from pathlib import Path
# from collections import defaultdict
# from concurrent.futures import ThreadPoolExecutor
from statistics import median
from typing import List

from yfpy.data import Data
from yfpy.models import Game, League, Manager, Matchup, Team, Player
from yfpy.query import YahooFantasySportsQuery

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from report.logger import get_logger

logger = get_logger(__name__)

# Suppress YFPY debug logging
logging.getLogger("yfpy.query").setLevel(level=logging.INFO)
logging.getLogger("yfpy.data").setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class LeagueData(object):

    def __init__(self,
                 week_for_report,
                 start_week,
                 league_id,
                 game_id,
                 config,
                 base_dir,
                 data_dir,
                 week_validation_function,
                 save_data=True,
                 dev_offline=False):

        logger.debug("Initializing Yahoo league.")

        self.league_id = league_id
        self.game_id = game_id
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        logger.debug("Retrieving Yahoo league data.")
        self.yahoo_data = Data(self.data_dir, save_data=save_data, dev_offline=dev_offline)
        yahoo_auth_dir = Path(base_dir) / Path(config.get("Yahoo", "yahoo_auth_dir"))
        self.yahoo_query = YahooFantasySportsQuery(
            yahoo_auth_dir, self.league_id, self.game_id, offline=dev_offline, browser_callback=False
        )

        if self.game_id and self.game_id != "nfl":
            yahoo_fantasy_game: Game = self.yahoo_data.retrieve(
                str(self.game_id) + "-game-metadata",
                self.yahoo_query.get_game_metadata_by_game_id,
                params={"game_id": self.game_id},
                data_type_class=Game
            )
        else:
            yahoo_fantasy_game: Game = self.yahoo_data.retrieve(
                "current-game-metadata",
                self.yahoo_query.get_current_game_metadata,
                data_type_class=Game
            )

        self.league_key = yahoo_fantasy_game.game_key + ".l." + self.league_id
        self.season = yahoo_fantasy_game.season

        # YAHOO API QUERY: run query to retrieve all league information, including current standings
        self.league_info: League = self.yahoo_data.retrieve(
            str(self.league_id) + "-league-info",
            self.yahoo_query.get_league_info,
            data_type_class=League,
            new_data_dir=(self.data_dir / str(self.season) / str(self.league_id)))

        self.season = self.league_info.season
        self.start_week = start_week or self.league_info.start_week
        self.current_week = self.league_info.current_week
        self.num_playoff_slots = self.league_info.settings.num_playoff_teams
        self.num_regular_season_weeks = int(self.league_info.settings.playoff_start_week) - 1
        self.num_divisions = len(self.league_info.settings.divisions)

        self.divisions = {
            str(division.division_id): division.name for
            division in self.league_info.settings.divisions
        }
        self.roster_positions = self.league_info.settings.roster_positions
        self.has_median_matchup = bool(self.league_info.settings.uses_median_score)
        self.median_score_by_week = {}

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week, self.season)

        # # YAHOO API QUERY: run yahoo queries for season team roster stats
        # self.rosters = {
        #     str(team.get("team").team_id): {
        #         str(player.get("player").player_id): player.get("player") for player in self.yahoo_data.retrieve(
        #             str(team.get("team").team_id) + "-" +
        #             str(team.get("team").name.decode("utf-8")).replace(" ", "_") + "-roster_stats",
        #             self.yahoo_query.get_team_roster_player_stats,
        #             params={"team_id": str(team.get("team").team_id)},
        #             new_data_dir=Path(self.data_dir) / str(self.season) / str(self.league_id) / "rosters"
        #         )
        #     } for team in self.league_info.standings.teams
        # }

        # if not self.save_data:
        #     # YAHOO API QUERY: run yahoo queries to retrieve matchups by week for the entire season
        #     with ThreadPoolExecutor() as executor:
        #         def _get_week(week):
        #             return {
        #                 "week": week,
        #                 "result": self.yahoo_data.retrieve(
        #                     "week_" + str(week) + "-matchups_by_week",
        #                     self.yahoo_query.get_league_matchups_by_week,
        #                     params={"chosen_week": week},
        #                     new_data_dir=Path(self.data_dir) / str(self.season) / str(self.league_id) / f"week_{week}"
        #             }
        #
        #         self.matchups_by_week = {}
        #         weeks = range(1, self.num_regular_season_weeks + 1)
        #
        #         for response in executor.map(_get_week, weeks):
        #             self.matchups_by_week[response["week"]] = response["result"]
        #
        #     # YAHOO API QUERY: run yahoo queries to retrieve team rosters by week up to the current week
        #     with ThreadPoolExecutor() as executor:
        #         def _get_roster(query):
        #             team = query["team"]
        #             week = query["week"]
        #             team_id = str(team.get("team").team_id)
        #             return {
        #                 "week": week,
        #                 "team": team,
        #                 "result": self.yahoo_data.retrieve(
        #                         team_id + "-" +
        #                         str(team.get("team").name.decode("utf-8")).replace(" ", "_") + "-roster",
        #                         self.yahoo_query.get_team_roster_player_stats_by_week,
        #                         params={"team_id": team_id, "chosen_week": week},
        #                         new_data_dir=(
        #                           Path(self.data_dir) / str(self.season) / str(self.league_id) / f"week_{week}" / "rosters"
        #                         )
        #                     )
        #             }
        #
        #         self.rosters_by_week = defaultdict(dict)
        #
        #         weeks = [str(w) for w in range(1, int(self.week_for_report) + 1)]
        #
        #         # build combinations of teams/weeks to query
        #         query_list = [{"week": w, "team": t} for w in weeks for t in self.league_info.standings.teams]
        #
        #         for response in executor.map(_get_roster, query_list):
        #             self.rosters_by_week[response["week"]][response["team"].get("team").team_id] = response["result"]
        # else:

        logger.debug("Getting Yahoo matchups by week data.")
        # TODO: figure out how to write to json files (json.dump) in a thread-safe manner
        # YAHOO API QUERY: run yahoo queries to retrieve matchups by week for the entire season
        self.matchups_by_week = {}
        for wk in range(self.start_week, self.num_regular_season_weeks + 1):
            self.matchups_by_week[wk] = self.yahoo_data.retrieve(
                "week_" + str(wk) + "-matchups_by_week",
                self.yahoo_query.get_league_matchups_by_week,
                params={"chosen_week": str(wk)},
                new_data_dir=self.data_dir / str(self.season) / str(self.league_id) / f"week_{str(wk)}"
            )

            if int(wk) <= int(self.week_for_report):
                scores = []
                matchup: Matchup
                for matchup in self.matchups_by_week[wk]:
                    for team in matchup.teams:
                        team_score = team.points
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    self.median_score_by_week[str(wk)] = weekly_median
                else:
                    self.median_score_by_week[str(wk)] = 0

        logger.debug("Getting Yahoo rosters by week data.")
        # YAHOO API QUERY: run yahoo queries to retrieve team rosters by week for the season up to the current week
        self.rosters_by_week = {}
        for wk in range(self.start_week, int(self.week_for_report) + 1):
            self.rosters_by_week[str(wk)] = {
                str(team.team_id):
                    self.yahoo_data.retrieve(
                        str(team.team_id) + "-" +
                        str(team.name.decode("utf-8")).replace(" ", "_") + "-roster",
                        self.yahoo_query.get_team_roster_player_info_by_week,
                        params={"team_id": str(team.team_id), "chosen_week": str(wk)},
                        new_data_dir=(
                                self.data_dir / str(self.season) / str(self.league_id) / f"week_{str(wk)}" / "rosters"
                        )
                    ) for team in self.league_info.standings.teams
            }

        # TODO: too many request to Yahoo, triggers 999 rate limiting error
        # self.player_stats_by_week = defaultdict(lambda: defaultdict(Player))
        # self.player_season_stats = {}
        # for wk in range(self.start_week, int(self.week_for_report) + 1):
        #     for roster in self.rosters_by_week[str(wk)].values():
        #         for player in roster:
        #             y_player: Player = player.get("player")
        #             player_id = str(y_player.player_id)
        #             player_key = str(y_player.player_key)
        #
        #             for week in range(1, int(self.week_for_report) + 1):
        #                 if player_id not in self.player_stats_by_week[str(week)].keys():
        #                     self.player_stats_by_week[str(week)][player_id] = self.get_player_data(
        #                         player_key=player_key, week=str(week))
        #
        #             if player_id not in self.player_season_stats.keys():
        #                 self.player_season_stats[player_id] = self.get_player_data(player_key=player_key)

    def get_player_data(self, player_key, week=None):
        # YAHOO API QUERY: run query to retrieve stats for specific player for chosen week if supplied, else for season
        params = {"player_key": player_key}
        if week:
            params["chosen_week"] = week

            return self.yahoo_data.retrieve(
                player_key,
                self.yahoo_query.get_player_stats_by_week,
                params=params,
                new_data_dir=Path(self.data_dir) / str(self.season) / self.league_id / f"week_{week}" / "players",
                data_type_class=Player
            )
        else:
            return self.yahoo_data.retrieve(
                player_key,
                self.yahoo_query.get_player_stats_for_season,
                params=params,
                new_data_dir=Path(self.data_dir) / str(self.season) / self.league_id / "players",
                data_type_class=Player
            )

    # noinspection PyTypeChecker
    def map_data_to_base(self, base_league_class):
        logger.debug("Mapping Yahoo data to base objects.")

        league: BaseLeague = base_league_class(
            self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data, self.dev_offline
        )

        league.name = self.league_info.name.decode()
        league.week = int(self.current_week)
        league.start_week = int(self.start_week)
        league.season = self.season
        league.num_teams = int(self.league_info.num_teams)
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.num_divisions = self.num_divisions
        league.divisions = self.divisions
        if league.num_divisions > 0:
            league.has_divisions = True
        league.has_median_matchup = self.has_median_matchup
        league.median_score = 0
        league.is_faab = True if int(self.league_info.settings.uses_faab) == 1 else False
        if league.is_faab:
            league.faab_budget = self.config.getint("Settings", "initial_faab_budget", fallback=100)
        league.url = self.league_info.url

        league.player_data_by_week_function = self.get_player_data
        league.player_data_by_week_key = "player_points_value"

        league.bench_positions = ["BN", "IR"]

        flex_mapping = {
            "W/R": {
                "flex_label": "FLEX_RB_WR",
                "flex_positions_attribute": "flex_positions_rb_wr",
                "flex_positions": ["RB", "WR"]
            },
            "W/T": {
                "flex_label": "FLEX_TE_WR",
                "flex_positions_attribute": "flex_positions_te_wr",
                "flex_positions": ["TE", "WR"]
            },
            "W/R/T": {
                "flex_label": "FLEX",
                "flex_positions_attribute": "flex_positions_rb_te_wr",
                "flex_positions": ["RB", "TE", "WR"]
            },
            "Q/W/R/T": {
                "flex_label": "SUPERFLEX",
                "flex_positions_attribute": "flex_positions_qb_rb_te_wr",
                "flex_positions": ["QB", "RB", "TE", "WR"]
            },
            "DB": {
                "flex_label": "FLEX_DB",
                "flex_positions_attribute": "flex_positions_db",
                "flex_positions": ["CB", "S"]
            },
            "DL": {
                "flex_label": "FLEX_DL",
                "flex_positions_attribute": "flex_positions_dl",
                "flex_positions": ["DE", "DT"]
            },
            "D": {
                "flex_label": "FLEX_IDP",
                "flex_positions_attribute": "flex_positions_individual_defensive_player",
                "flex_positions": ["CB", "DB", "DE", "DL", "DT", "LB", "S"]
            }
        }

        for position in self.roster_positions:
            pos_name = position.position
            pos_count = position.count

            if pos_name in flex_mapping.keys():
                league.__setattr__(
                    flex_mapping[pos_name].get("flex_positions_attribute"),
                    flex_mapping[pos_name].get("flex_positions")
                )
                pos_name = flex_mapping[pos_name].get("flex_label")

            pos_counter = deepcopy(pos_count)
            while pos_counter > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_counter -= 1

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = pos_count

        league_median_records_by_team = {}
        matchups: List[Matchup]
        for week, matchups in self.matchups_by_week.items():
            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []
            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = int(matchup.week)
                base_matchup.complete = True if matchup.status == "postevent" else False
                base_matchup.tied = bool(matchup.is_tied)

                team: Team
                for team in matchup.teams:
                    base_team = BaseTeam()

                    opposite_key = 1 if matchup.teams.index(team) == 0 else 0
                    team_division = team.division_id
                    opponent_division = matchup.teams[opposite_key].division_id
                    if team_division and opponent_division and team_division == opponent_division:
                        base_matchup.division_matchup = True

                    base_team.week = matchup.week
                    base_team.name = team.name.decode()
                    base_team.num_moves = team.number_of_moves
                    base_team.num_trades = team.number_of_trades

                    if isinstance(team.managers, list):
                        team_managers = team.managers
                    else:
                        team_managers = [team.managers]

                    manager: Manager
                    for manager in team_managers:
                        base_manager = BaseManager()

                        base_manager.manager_id = str(manager.manager_id)
                        base_manager.email = manager.email
                        base_manager.name = manager.nickname

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name_str for manager in base_team.managers])

                    base_team.team_id = str(team.team_id)
                    base_team.points = team.points
                    base_team.projected_points = team.projected_points
                    base_team.waiver_priority = team.waiver_priority
                    league.has_waiver_priorities = base_team.waiver_priority > 0
                    if league.is_faab:
                        base_team.faab = team.faab_balance if team.faab_balance else 0
                    base_team.url = team.url

                    team_standings_info = Team({})
                    for ranked_team in self.league_info.standings.teams:
                        if ranked_team.team_id == int(base_team.team_id):
                            team_standings_info = ranked_team

                    if team_standings_info.streak_type == "win":
                        streak_type = "W"
                    elif team_standings_info.streak_type == "loss":
                        streak_type = "L"
                    else:
                        streak_type = "T"

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(team_standings_info.wins) if team_standings_info.wins else 0,
                        losses=int(team_standings_info.losses) if team_standings_info.losses else 0,
                        ties=int(team_standings_info.ties) if team_standings_info.ties else 0,
                        percentage=float(team_standings_info.percentage) if team_standings_info.percentage else 0.0,
                        points_for=float(team_standings_info.points_for) if team_standings_info.points_for else 0.0,
                        points_against=float(team_standings_info.points_against) if team_standings_info.points_against
                        else 0.0,
                        streak_type=streak_type,
                        streak_len=int(team_standings_info.streak_length) if team_standings_info.streak_type else 0,
                        team_id=team.team_id,
                        team_name=team.name,
                        rank=int(team_standings_info.rank) if team_standings_info.rank else 0,
                        division=base_team.division,
                        division_wins=int(team_standings_info.team_standings.divisional_outcome_totals.wins) if
                        team_standings_info.team_standings.divisional_outcome_totals.wins else 0,
                        division_losses=int(team_standings_info.team_standings.divisional_outcome_totals.losses) if
                        team_standings_info.team_standings.divisional_outcome_totals.losses else 0,
                        division_ties=int(team_standings_info.team_standings.divisional_outcome_totals.ties) if
                        team_standings_info.team_standings.divisional_outcome_totals.ties else 0,
                        division_percentage=round(float(
                            team_standings_info.team_standings.divisional_outcome_totals.wins / (
                                    team_standings_info.team_standings.divisional_outcome_totals.wins +
                                    team_standings_info.team_standings.divisional_outcome_totals.ties +
                                    team_standings_info.team_standings.divisional_outcome_totals.losses)), 3)
                        if (team_standings_info.team_standings.divisional_outcome_totals.wins +
                            team_standings_info.team_standings.divisional_outcome_totals.ties +
                            team_standings_info.team_standings.divisional_outcome_totals.losses) > 0 else 0
                    )
                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if base_matchup.division_matchup:
                        base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = self.median_score_by_week.get(str(week))

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
                    league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # no winner/loser if matchup is tied
                    if not base_matchup.tied:
                        if team.team_key == matchup.winner_team_key:
                            base_matchup.winner = base_team
                        else:
                            base_matchup.loser = base_team

                # add matchup to league matchups by week
                league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            roster: List[Player]
            for team_id, roster in rosters.items():
                league_team: BaseTeam = league.teams_by_week.get(str(week)).get(str(team_id))
                for player in roster:
                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = player.player_key
                    base_player.bye_week = player.bye if player.bye else 0
                    base_player.display_position = player.display_position
                    base_player.nfl_team_id = player.editorial_team_key
                    base_player.nfl_team_abbr = player.editorial_team_abbr
                    base_player.nfl_team_name = player.editorial_team_full_name
                    base_player.first_name = player.first_name
                    base_player.last_name = player.last_name
                    base_player.full_name = player.full_name
                    if base_player.display_position != "DEF":
                        base_player.headshot_url = "https:" + player.headshot_url.split(":")[-1]
                    else:
                        # use ESPN D/ST team logo (higher resolution)
                        base_player.headshot_url = (
                            f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{base_player.nfl_team_abbr}.png"
                        )
                        # base_player.headshot_url = y_player_for_week.headshot_url
                    base_player.owner_team_id = player.ownership.owner_team_key
                    base_player.owner_team_name = player.ownership.owner_team_name
                    base_player.percent_owned = player.percent_owned_value if player.percent_owned_value else 0
                    base_player.points = player.player_points_value if player.player_points_value else 0
                    base_player.position_type = player.position_type
                    if player.primary_position in flex_mapping.keys():
                        base_player.primary_position = flex_mapping[player.primary_position].get("flex_label")
                    else:
                        base_player.primary_position = player.primary_position

                    if player.selected_position_value in flex_mapping.keys():
                        base_player.selected_position = flex_mapping[player.selected_position_value].get("flex_label")
                    else:
                        base_player.selected_position = player.selected_position_value
                    base_player.selected_position_is_flex = bool(player.selected_position.is_flex)

                    base_player.status = player.status

                    eligible_positions = player.eligible_positions
                    for position in eligible_positions:
                        if position in flex_mapping.keys():
                            position = flex_mapping[position].get("flex_label")
                        for flex_label, flex_positions in league.get_flex_positions_dict().items():
                            if position in flex_positions:
                                base_player.eligible_positions.append(flex_label)
                        base_player.eligible_positions.append(position)

                    for stat in player.stats:
                        base_stat = BaseStat()

                        base_stat.stat_id = stat.stat_id
                        base_stat.name = stat.name
                        base_stat.value = stat.value

                        base_player.stats.append(base_stat)

                    # add player to team roster
                    league_team.roster.append(base_player)

                    # add player to league players by week
                    league.players_by_week[str(week)][base_player.player_id] = base_player

        league.current_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.current_record.rank)

        league.current_median_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(),
            key=lambda x: (
                x.current_median_record.get_wins(),
                -x.current_median_record.get_losses(),
                x.current_median_record.get_ties(),
                x.current_median_record.get_points_for()
            ),
            reverse=True
        )

        return league
