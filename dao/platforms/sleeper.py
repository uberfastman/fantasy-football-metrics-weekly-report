__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import datetime
import json
import logging
import os
import sys
from collections import defaultdict, Counter
from copy import deepcopy
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path
from statistics import median

import requests
from requests.exceptions import HTTPError

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from report.logger import get_logger

logger = get_logger(__name__, propagate=False)

# Suppress Sleeper API debug logging
logger.setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class LeagueData(object):

    def __init__(self,
                 week_for_report,
                 league_id,
                 season,
                 start_week,
                 config,
                 data_dir,
                 week_validation_function,
                 get_current_nfl_week_function,
                 save_data=True,
                 dev_offline=False):

        logger.debug("Initializing Sleeper league.")

        self.league_id = league_id
        self.season = season
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        self.offensive_positions = ["QB", "RB", "WR", "TE", "K", "FLEX", "REC_FLEX", "WRRB_FLEX", "SUPER_FLEX"]
        self.defensive_positions = ["DEF"]

        # create full directory path if any directories in it do not already exist
        if not Path(self.data_dir).exists():
            os.makedirs(self.data_dir)

        self.base_url = "https://api.sleeper.app/v1/"
        self.base_stat_url = "https://api.sleeper.app/"

        self.league_info = self.query(
            self.base_url + "league/" + str(self.league_id),
            Path(self.data_dir) / str(self.season) / str(self.league_id),
            f"{self.league_id}-league_info.json"
        )

        self.league_settings = self.league_info.get("settings")
        self.league_scoring = self.league_info.get("scoring_settings")

        # TODO: figure out how to get league starting week
        self.start_week = start_week or 1

        self.current_week = get_current_nfl_week_function(self.config, self.dev_offline)

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week, self.season)

        self.num_playoff_slots = self.league_settings.get("playoff_teams")
        self.num_regular_season_weeks = (int(self.league_settings.get("playoff_week_start")) - 1) \
            if self.league_settings.get("playoff_week_start") > 0 \
            else self.config.get("Settings", "num_regular_season_weeks")
        self.roster_positions = dict(Counter(self.league_info.get("roster_positions")))
        self.has_median_matchup = bool(self.league_settings.get("league_average_match"))
        self.median_score_by_week = {}

        self.player_data = self.query(
            self.base_url + "players/nfl",
            Path(self.data_dir) / str(self.season) / str(self.league_id),
            str(self.league_id) + "-player_data.json",
            check_for_saved_data=True,
            refresh_days_delay=7
        )

        self.player_stats_data_by_week = {}
        self.player_projected_stats_data_by_week = {}
        for week_for_player_stats in range(1, int(self.num_regular_season_weeks) + 1):
            if int(week_for_player_stats) <= int(self.week_for_report):
                self.player_stats_data_by_week[str(week_for_player_stats)] = {
                    player["player_id"]: player["stats"] for player in self.query(
                        self.base_stat_url + "stats/nfl/" + str(season) + "/" + str(week_for_player_stats) +
                        "?season_type=regular",
                        Path(self.data_dir) / str(self.season) / str(self.league_id) / f"week_{week_for_player_stats}",
                        f"week_{week_for_player_stats}-player_stats_by_week.json",
                        check_for_saved_data=True,
                        refresh_days_delay=1
                    )
                }

            self.player_projected_stats_data_by_week[str(week_for_player_stats)] = {
                player["player_id"]: player["stats"] for player in self.query(
                    self.base_stat_url + "projections/nfl/" + str(season) + "/" + str(week_for_player_stats) +
                    "?season_type=regular",
                    Path(self.data_dir) / str(self.season) / str(self.league_id) / f"week_{week_for_player_stats}",
                    f"week_{week_for_player_stats}-player_projected_stats_by_week.json",
                    check_for_saved_data=True,
                    refresh_days_delay=1
                )
            }

        self.player_season_stats = {
            player["player_id"]: player["stats"] for player in self.query(
                self.base_stat_url + "stats/nfl/" + str(self.season) + "?season_type=regular",
                Path(self.data_dir) / str(self.season) / str(self.league_id),
                f"{league_id}-player_season_stats.json",
                check_for_saved_data=True,
                refresh_days_delay=1
            )
        }

        self.player_season_projected_stats = {
            player["player_id"]: player["stats"] for player in self.query(
                self.base_stat_url + "projections/nfl/" + str(self.season) + "?season_type=regular",
                Path(self.data_dir) / str(self.season) / str(self.league_id),
                f"{league_id}-player_season_projected_stats.json",
                check_for_saved_data=True,
                refresh_days_delay=1
            )
        }

        # with open(Path(
        #         self.data_dir) / str(self.season) / str(self.league_id) / "player_stats_by_week.json"), "w") as out:
        #     json.dump(self.player_stats_data_by_week, out, ensure_ascii=False, indent=2)

        self.league_managers = {
            manager.get("user_id"): manager for manager in self.query(
                self.base_url + "league/" + self.league_id + "/users",
                Path(self.data_dir) / str(self.season) / str(self.league_id),
                f"{league_id}-league_managers.json"
            )
        }

        self.standings = sorted(
            self.query(
                self.base_url + "league/" + league_id + "/rosters",
                Path(self.data_dir) / str(self.season) / str(self.league_id),
                f"{self.league_id}-league_standings.json"
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
            team["owner"] = self.league_managers.get(team.get("owner_id"))
            team["co_owners"] = [self.league_managers.get(co_owner) for co_owner in team.get("co_owners")] if team.get(
                "co_owners") else []

        self.matchups_by_week = {}
        for week_for_matchups in range(1, int(self.num_regular_season_weeks) + 1):
            self.matchups_by_week[str(week_for_matchups)] = [
                self.map_player_data_to_matchup(list(group), week_for_matchups) for key, group in groupby(
                    sorted(
                        self.query(
                            self.base_url + "league/" + league_id + "/matchups/" + str(week_for_matchups),
                            Path(self.data_dir) / str(self.season) / str(self.league_id) / f"week_{week_for_matchups}",
                            f"week_{week_for_matchups}-matchups_by_week.json"
                        ),
                        key=lambda x: x["matchup_id"]
                    ),
                    key=lambda x: x["matchup_id"]
                )
            ]

            if int(week_for_matchups) <= int(self.week_for_report):
                scores = []
                for matchup in self.matchups_by_week[str(week_for_matchups)]:
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
                    self.median_score_by_week[str(week_for_matchups)] = weekly_median
                else:
                    self.median_score_by_week[str(week_for_matchups)] = 0

        self.rosters_by_week = {}
        for week_for_rosters in range(1, int(self.week_for_report) + 1):
            team_rosters = {}
            for matchup in self.matchups_by_week[str(week_for_rosters)]:
                for team in matchup:
                    team_rosters[team["roster_id"]] = team["roster"]

            self.rosters_by_week[str(week_for_rosters)] = team_rosters

        self.league_transactions_by_week = {}
        for week_for_transactions in range(1, int(self.week_for_report) + 1):
            self.league_transactions_by_week[str(week_for_transactions)] = defaultdict(lambda: defaultdict(list))
            weekly_transactions = self.query(
                self.base_url + "league/" + league_id + "/transactions/" + str(week_for_transactions),
                Path(self.data_dir) / str(self.season) / str(self.league_id) / f"week_{week_for_transactions}",
                f"week_{week_for_transactions}-transactions_by_week.json"
            )

            for transaction in weekly_transactions:
                if transaction.get("status") == "complete":
                    transaction_type = transaction.get("type")
                    if transaction_type in ["waiver", "free_agent", "trade"]:
                        for team_roster_id in transaction.get("consenter_ids"):
                            if transaction_type == "waiver":
                                self.league_transactions_by_week[str(week_for_transactions)][str(team_roster_id)][
                                    "moves"].append(transaction)
                            elif transaction_type == "free_agent":
                                self.league_transactions_by_week[str(week_for_transactions)][str(team_roster_id)][
                                    "moves"].append(transaction)
                            elif transaction_type == "trade":
                                self.league_transactions_by_week[str(week_for_transactions)][str(team_roster_id)][
                                    "trades"].append(transaction)

    def query(self, url, file_dir, filename, check_for_saved_data=False, refresh_days_delay=1):

        file_path = Path(file_dir) / filename

        run_query = True
        if check_for_saved_data:
            if not Path(file_path).exists():
                logger.debug(f"File {filename} does not exist... attempting data retrieval.")
            else:
                file_modified_timestamp = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                if file_modified_timestamp < (datetime.today() - timedelta(days=refresh_days_delay)):
                    if not self.dev_offline:
                        logger.debug(
                            f"Data in {filename} over {refresh_days_delay} day{'s' if refresh_days_delay > 1 else ''} "
                            f"old... refreshing."
                        )
                    else:
                        logger.debug(
                            f"Data in {filename} over {refresh_days_delay} day{'s' if refresh_days_delay > 1 else ''} "
                            f"old but dev_offline=True... skipping refresh."
                        )
                else:
                    logger.debug(f"Data in {filename} still recent... skipping refresh.")
                    run_query = False
                    with open(file_path, "r") as saved_data:
                        response_json = json.load(saved_data)

        if not self.dev_offline:
            if run_query:
                logger.debug(f"Retrieving Sleeper data from endpoint: {url}")
                response = requests.get(url)

                try:
                    response.raise_for_status()
                except HTTPError as e:
                    # log error and terminate query if status code is not 200
                    logger.error(f"REQUEST FAILED WITH STATUS CODE: {response.status_code} - {e}")
                    sys.exit("...run aborted.")

                response_json = response.json()
                logger.debug(f"Response (JSON): {response_json}")
        else:
            try:
                logger.debug(f"Loading saved Sleeper data for endpoint: {url}")
                with open(file_path, "r", encoding="utf-8") as data_in:
                    response_json = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    f"FILE {file_path} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!"
                )
                sys.exit("...run aborted.")

        if self.save_data or check_for_saved_data:
            if run_query:
                logger.debug(f"Saving Sleeper data retrieved from endpoint: {url}")
                if not Path(file_dir).exists():
                    os.makedirs(file_dir)

                with open(file_path, "w", encoding="utf-8") as data_out:
                    json.dump(response_json, data_out, ensure_ascii=False, indent=2)

        return response_json

    def fetch_player_data(self, player_id, week, starter=False):
        # handle the move of the Raiders from Oakland (OAK) to Las Vegas (LV) between the 2019 and 2020 seasons
        if player_id == "OAK":
            player_id = "LV"
        player = deepcopy(self.player_data.get(str(player_id)))
        if int(week) <= int(self.week_for_report):
            player["stats"] = deepcopy(self.player_stats_data_by_week.get(str(week)).get(str(player_id)))
            player["projected"] = deepcopy(self.player_projected_stats_data_by_week[str(week)].get(str(player_id)))
            player["starter"] = starter
        return player

    def map_player_data_to_matchup(self, matchup, week):
        for team in matchup:
            for ranked_team in self.standings:
                if ranked_team.get("roster_id") == team.get("roster_id"):
                    team["info"] = {
                        k: v for k, v in ranked_team.items() if k not in ["taxi", "starters", "reserve", "players"]
                    }

            if team["starters"] and team["players"]:
                team["roster"] = [
                    self.fetch_player_data(player_id, week, True) if player_id in team["starters"] else
                    self.fetch_player_data(player_id, week) for player_id in team["players"]
                ]
            elif not team["starters"] and team["players"]:
                team["roster"] = [
                    self.fetch_player_data(player_id, week) for player_id in team["players"]
                ]
            else:
                team["roster"] = []

        return matchup

    def get_player_points(self, stats, projected_stats):
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

    def map_data_to_base(self, base_league_class):
        logger.debug("Mapping Sleeper data to base objects.")

        league: BaseLeague = base_league_class(
            self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data, self.dev_offline
        )

        league.name = self.league_info.get("name")
        league.week = int(self.current_week)
        league.start_week = int(self.start_week)
        league.season = self.league_info.get("season")
        league.num_teams = int(self.league_settings.get("num_teams"))
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.num_divisions = int(self.league_settings.get("divisions", 0))
        # TODO: missing division names
        league.divisions = None
        if league.num_divisions > 0:
            league.has_divisions = True
        league.has_median_matchup = self.has_median_matchup
        league.median_score = 0
        league.faab_budget = int(self.league_settings.get("waiver_budget"))
        if league.faab_budget > 0:
            league.is_faab = True
        # league.url = self.base_url + "league/" + str(self.league_id)
        league.url = "https://sleeper.app/leagues/" + str(self.league_id)

        # TODO: hook up to collected player stats by week
        league.player_data_by_week_function = None
        league.player_data_by_week_key = None

        league.bench_positions = ["BN", "IR"]

        flex_mapping = {
            "WRRB_FLEX": {
                "flex_label": "FLEX_RB_WR",
                "flex_positions_attribute": "flex_positions_rb_wr",
                "flex_positions": ["RB", "WR"]
            },
            "REC_FLEX": {
                "flex_label": "FLEX_TE_WR",
                "flex_positions_attribute": "flex_positions_te_wr",
                "flex_positions": ["TE", "WR"]
            },
            "FLEX": {
                "flex_label": "FLEX_RB_TE_WR",
                "flex_positions_attribute": "flex_positions_rb_te_wr",
                "flex_positions": ["RB", "TE", "WR"]
            },
            "SUPER_FLEX": {
                "flex_label": "FLEX_QB_RB_TE_WR",
                "flex_positions_attribute": "flex_positions_qb_rb_te_wr",
                "flex_positions": ["QB", "RB", "TE", "WR"]
            },
            "IDP_FLEX": {
                "flex_label": "FLEX_IDP",
                "flex_positions_attribute": "flex_positions_idp",
                "flex_positions": ["DB", "DL", "LB"]
            }
        }

        for position, count in self.roster_positions.items():
            pos_name = position
            pos_count = count

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
        for week, matchups in self.matchups_by_week.items():
            matchups_week = str(week)
            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []

            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = int(matchups_week)
                # TODO: because Sleeper doesn't tell current week of selected season, check current vs. previous season
                #  and use month to determine if it's first or second year within same season and mark matchups from
                #  previous years complete by default for the sake of this functionality working
                # base_matchup.complete = True if int(week) <= int(self.current_week) else False
                current_date = datetime.today()
                if current_date.month < 9 and int(league.season) < (current_date.year - 1):
                    base_matchup.complete = True
                elif int(league.season) < current_date.year:
                    base_matchup.complete = True
                else:
                    base_matchup.complete = True if int(week) <= int(self.current_week) else False
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
                    if league.has_divisions:
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
                    base_team.manager_str = team_info.get("owner").get("display_name") if team_info.get("owner") else \
                        "N/A"
                    base_team.points = round(float(team.get("points")), 2) if team.get("points") else 0
                    base_team.num_moves = sum(len(self.league_transactions_by_week.get(str(week), {}).get(
                        str(base_team.team_id), {}).get("moves", [])) for week in range(1, int(week) + 1))
                    base_team.num_trades = sum(len(self.league_transactions_by_week.get(str(week), {}).get(
                        str(base_team.team_id), {}).get("trades", [])) for week in range(1, int(week) + 1))

                    base_team.waiver_priority = team_settings.get("waiver_position")
                    league.has_waiver_priorities = base_team.waiver_priority > 0
                    base_team.faab = league.faab_budget - int(team_settings.get("waiver_budget_used", 0))
                    base_team.url = None

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(team_settings.get("wins")),
                        losses=int(team_settings.get("losses")),
                        ties=int(team_settings.get("ties")),
                        percentage=(
                            round(float(int(team_settings.get("wins")) / (
                                int(team_settings.get("wins")) + int(team_settings.get("losses")) +
                                int(team_settings.get("ties"))
                            )), 3)
                            if int(team_settings.get("wins")) +
                            int(team_settings.get("losses")) +
                            int(team_settings.get("ties")) > 0 else 0.0
                        ),
                        points_for=float(str(team_settings.get("fpts")) + "." + (
                            str(team_settings.get("fpts_decimal")) if team_settings.get("fpts_decimal") else "0")),
                        points_against=float(
                            (str(team_settings.get("fpts_against")) if
                             team_settings.get("fpts_against") else "0") + "." +
                            (str(team_settings.get("fpts_against_decimal")) if
                             team_settings.get("fpts_against_decimal") else "0")
                        ),
                        streak_type=None,
                        streak_len=0,
                        team_id=base_team.team_id,
                        team_name=base_team.name,
                        rank=team_rank
                    )
                    if league.has_divisions:
                        base_team.current_record.division = base_team.division

                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if league.has_divisions:
                        if base_matchup.division_matchup:
                            base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = self.median_score_by_week.get(matchups_week)

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
                league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            team_count = 1
            for team_id, roster in rosters.items():
                league_team: BaseTeam = league.teams_by_week.get(str(week)).get(str(team_id))

                team_filled_positions = [
                    position if position not in flex_mapping.keys()
                    else flex_mapping[position].get("flex_label")
                    for position in self.league_info.get("roster_positions")
                ]

                for player in roster:
                    if player:
                        base_player = BasePlayer()

                        base_player.week_for_report = int(week)
                        base_player.player_id = player.get("player_id")
                        # TODO: use week WITHOUT projections (Ex.: 11: null) to determine player bye week
                        base_player.bye_week = None
                        base_player.display_position = player.get("position")
                        base_player.nfl_team_id = None
                        base_player.nfl_team_abbr = player.get("team")
                        # TODO: no full team name for player
                        base_player.nfl_team_name = player.get("team")
                        if base_player.display_position == "DEF":
                            base_player.first_name = player.get("first_name") + " " + player.get("last_name")
                            base_player.full_name = base_player.first_name
                            base_player.nfl_team_name = base_player.first_name
                            base_player.headshot_url = "https://sleepercdn.com/images/team_logos/nfl/" + \
                                                       str(base_player.player_id).lower() + ".png"
                        else:
                            base_player.first_name = player.get("first_name")
                            base_player.last_name = player.get("last_name")
                            base_player.full_name = player.get("full_name")
                            base_player.headshot_url = "https://sleepercdn.com/content/nfl/players/thumb/" + \
                                                       str(base_player.player_id) + ".jpg"
                        base_player.owner_team_id = None
                        base_player.owner_team_id = None
                        base_player.percent_owned = None

                        player_stats = player.get("stats")
                        base_player.points, base_player.projected_points = self.get_player_points(
                            stats=player_stats,
                            projected_stats=player.get("projected")
                        )

                        base_player.season_points, base_player.season_projected_points = self.get_player_points(
                            stats=self.player_season_stats[str(base_player.player_id)]
                            if str(base_player.player_id) in self.player_season_stats.keys() else [],
                            projected_stats=self.player_season_projected_stats[str(base_player.player_id)]
                            if str(base_player.player_id) in self.player_season_projected_stats.keys() else []
                        )

                        base_player.position_type = "O" if base_player.display_position in self.offensive_positions \
                            else "D"
                        base_player.primary_position = player.get("position")

                        eligible_positions = player.get("fantasy_positions")
                        if len(eligible_positions) > 1:
                            player["multiple_non_flex_positions"] = True
                        for position in eligible_positions:
                            if position in flex_mapping.keys():
                                position = flex_mapping[position].get("flex_label")
                            for flex_label, flex_positions in league.get_flex_positions_dict().items():
                                if position in flex_positions:
                                    base_player.eligible_positions.append(flex_label)
                            base_player.eligible_positions.append(position)

                        if player["starter"]:

                            if not player.get("roster_assignation_delayed", False) and player.get(
                                    "multiple_non_flex_positions", False):
                                player["roster_assignation_delayed"] = True
                                roster.append(player)
                                continue

                            available_primary_slots = list(
                                set(base_player.eligible_positions)
                                .intersection(set(team_filled_positions))
                                .difference(set([item.get("flex_label") for item in flex_mapping.values()]))
                            )

                            available_wrrb_flex_slots = list(
                                set(base_player.eligible_positions)
                                .intersection(set(league.flex_positions_rb_wr))
                            )

                            available_rec_flex_slots = list(
                                set(base_player.eligible_positions)
                                .intersection(set(league.flex_positions_te_wr))
                            )

                            available_flex_slots = list(
                                set(base_player.eligible_positions)
                                .intersection(set(league.flex_positions_rb_te_wr))
                            )

                            available_super_flex_slots = list(
                                set(base_player.eligible_positions)
                                .intersection(set(league.flex_positions_qb_rb_te_wr))
                            )

                            available_idp_flex_slots = list(
                                set(base_player.eligible_positions)
                                .intersection(set(league.flex_positions_idp))
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

                            elif len(available_flex_slots) > 0 and "FLEX_RB_TE_WR" in team_filled_positions:
                                base_player.selected_position = "FLEX_RB_TE_WR"
                                base_player.selected_position_is_flex = True
                                team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                            elif len(available_super_flex_slots) > 0 and "FLEX_QB_RB_TE_WR" in team_filled_positions:
                                base_player.selected_position = "FLEX_QB_RB_TE_WR"
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
                        league.players_by_week[str(week)][base_player.player_id] = base_player

                team_count += 1

        league.current_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.current_record.rank
        )

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
