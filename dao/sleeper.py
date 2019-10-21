__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import datetime
import json
import logging
import os
import re
from datetime import datetime, timedelta
import sys
from pprint import pprint
from collections import defaultdict, Counter
from copy import deepcopy

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from sleeper_wrapper import League

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseManager, BasePlayer, BaseStat

logger = logging.getLogger(__name__)

# Suppress Fleaflicker API debug logging
logger.setLevel(level=logging.INFO)


class LeagueData(object):

    def __init__(self,
                 week_for_report,
                 league_id,
                 season,
                 config,
                 base_dir,
                 data_dir,
                 week_validation_function,
                 save_data=True,
                 dev_offline=False):

        self.league_id = league_id
        self.season = season
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        self.offensive_positions = ["QB", "RB", "WR", "TE", "K", "FLEX", "SUPER_FLEX"]
        self.defensive_positions = ["DEF"]

        # create full directory path if any directories in it do not already exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.base_url = "https://api.sleeper.app/v1/"

        self.league_info = self.query(
            self.base_url + "league/" + str(self.league_id),
            os.path.join(self.data_dir, str(self.season), str(self.league_id)),
            str(self.league_id) + "-league_info.json"
        )

        self.league_settings = self.league_info.get("settings")

        self.current_season = self.league_info.get("season")
        # TODO: current week
        self.current_week = 6

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week)

        self.num_playoff_slots = self.league_settings.get("playoff_teams")
        self.num_regular_season_weeks = int(self.league_settings.get("playoff_week_start")) - 1
        self.roster_positions = dict(Counter(self.league_info.get("roster_positions")))

        self.player_data = self.query(
            self.base_url + "players/nfl",
            os.path.join(self.data_dir, str(self.season), str(self.league_id)),
            str(self.league_id) + "-player_data.json",
            check_for_saved_data=True,
            refresh_days_delay=7
        )

        self.player_stats_data_by_week = {}
        self.player_projected_stats_data_by_week = {}
        for wk in range(1, int(self.num_regular_season_weeks) + 1):
            if int(wk) <= int(self.week_for_report):
                self.player_stats_data_by_week[str(wk)] = self.query(
                    self.base_url + "stats/nfl/regular/" + str(season) + "/" + str(wk),
                    os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk)),
                    "week_" + str(wk) + "-player_stats_by_week.json",
                    check_for_saved_data=True,
                    refresh_days_delay=1
                )

            self.player_projected_stats_data_by_week[str(wk)] = self.query(
                self.base_url + "projections/nfl/regular/" + str(season) + "/" + str(wk),
                os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk)),
                "week_" + str(wk) + "-player_projected_stats_by_week.json",
                check_for_saved_data=True,
                refresh_days_delay=1
            )

        self.league_managers = {
            manager.get("user_id"): manager for manager in self.query(
                self.base_url + "league/" + self.league_id + "/users",
                os.path.join(self.data_dir, str(self.season), str(self.league_id)),
                str(self.league_id) + "-league_managers.json"
            )
        }

        self.current_rosters = sorted(
            self.query(
                self.base_url + "league/" + league_id + "/rosters",
                os.path.join(self.data_dir, str(self.season), str(self.league_id)),
                str(self.league_id) + "-league_rosters.json"
            ),
            key=lambda x: (
                x.get("settings").get("wins"),
                -x.get("settings").get("losses"),
                x.get("settings").get("ties"),
                float(str(x.get("settings").get("fpts")) + "." + str(x.get("settings").get("fpts_decimal")))
            ),
            reverse=True
        )

        for team in self.current_rosters:
            team["taxi"] = [
                self.fetch_player_data(player_id, self.current_week) for player_id in team.get("taxi")
            ] if team.get("taxi") else []

            team["starters"] = [
                self.fetch_player_data(player_id, self.current_week) for player_id in team.get("starters")
            ] if team.get("starters") else []

            team["reserve"] = [
                self.fetch_player_data(player_id, self.current_week) for player_id in team.get("reserve")
            ] if team.get("reserve") else []

            team["players"] = [
                self.fetch_player_data(player_id, self.current_week) for player_id in team.get("players")
            ] if team.get("players") else []

            team["owner"] = self.league_managers.get(team.get("owner_id"))
            team["co_owners"] = [self.league_managers.get(co_owner) for co_owner in team.get("co_owners")] if team.get(
                "co_owners") else []

        # # TODO: remove
        # with open(os.path.join(self.data_dir, str(self.season), str(self.league_id), "current_rosters.json"), "w") as out:
        #     json.dump(self.current_rosters, out, ensure_ascii=False, indent=2)

        self.matchups_by_week = {}
        for wk in range(1, int(self.num_regular_season_weeks) + 1):
            self.matchups_by_week[str(wk)] = self.query(
                self.base_url + "league/" + league_id + "/matchups/" + str(wk),
                os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk)),
                "week_" + str(wk) + "-matchups_by_week.json"
            )

        self.rosters_by_week = {}
        for wk, matchups in self.matchups_by_week.items():
            self.rosters_by_week[str(wk)] = {}
            matchup_pairs = defaultdict(lambda: defaultdict(list))
            for matchup_team in matchups:
                matchup_team["starters"] = [
                    self.fetch_player_data(player_id, wk) for player_id in matchup_team.get("starters")
                ] if matchup_team.get("starters") else []

                matchup_team["players"] = [
                    self.fetch_player_data(player_id, wk) for player_id in matchup_team.get("players")
                ] if matchup_team.get("players") else []

                if int(wk) <= int(self.week_for_report):
                    self.rosters_by_week[str(wk)][str(matchup_team.get("roster_id"))] = {
                        "starters": matchup_team.get("starters"),
                        "players": matchup_team.get("players")
                    }

                    for team in self.current_rosters:
                        if team.get("roster_id") == matchup_team.get("roster_id"):
                            self.rosters_by_week[str(wk)][str(matchup_team.get("roster_id"))]["info"] = team

                matchup_pairs[matchup_team.get("matchup_id")]["teams"].append(matchup_team)

            for matchup_pair in matchup_pairs.values():
                matchup_pair_roster_ids = [matchup_pair["teams"][0].get("roster_id"),
                                           matchup_pair["teams"][1].get("roster_id")]
                matchup_pair["roster_ids"] = matchup_pair_roster_ids

            self.matchups_by_week[wk] = matchup_pairs

        # # TODO: remove
        # with open(os.path.join(self.data_dir, str(self.season), str(self.league_id), "matchups_by_week.json"), "w") as out:
        #     json.dump(self.matchups_by_week, out, ensure_ascii=False, indent=2)
        with open(os.path.join(self.data_dir, str(self.season), str(self.league_id), "rosters_by_week.json"), "w") as out:
            json.dump(self.rosters_by_week[str(week_for_report)], out, ensure_ascii=False, indent=2)

        self.league_transactions_by_week = {}
        for wk in range(1, int(self.week_for_report) + 1):
            self.league_transactions_by_week[str(wk)] = defaultdict(lambda: defaultdict(list))
            weekly_transactions = self.query(
                self.base_url + "league/" + league_id + "/transactions/" + str(wk),
                os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk)),
                "week_" + str(wk) + "-transactions_by_week.json"
            )

            for transaction in weekly_transactions:
                if transaction.get("status") == "complete":
                    transaction_type = transaction.get("type")
                    if transaction_type in ["waiver", "free_agent", "trade"]:
                        for team_roster_id in transaction.get("consenter_ids"):
                            if transaction_type == "waiver":
                                self.league_transactions_by_week[str(wk)][str(team_roster_id)]["moves"].append(transaction)
                            elif transaction_type == "free_agent":
                                self.league_transactions_by_week[str(wk)][str(team_roster_id)]["moves"].append(transaction)
                            elif transaction_type == "trade":
                                self.league_transactions_by_week[str(wk)][str(team_roster_id)]["trades"].append(transaction)

        # # TODO: remove
        # with open(os.path.join(self.data_dir, str(self.season), str(self.league_id), "transactions_by_week.json"), "w") as out:
        #     json.dump(self.league_transactions_by_week, out, ensure_ascii=False, indent=2)

    def query(self, url, file_dir, filename, check_for_saved_data=False, refresh_days_delay=1):

        file_path = os.path.join(file_dir, filename)

        run_query = True
        if check_for_saved_data:
            if not os.path.exists(file_path):
                logger.info("File {} does not exist... attempting data retrieval.".format(filename))
            else:
                file_modified_timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_modified_timestamp < (datetime.today() - timedelta(days=refresh_days_delay)):
                    logger.info("Data in {} over {} day{} old... refreshing.".format(
                        filename, refresh_days_delay, "s" if refresh_days_delay > 1 else ""))
                else:
                    logger.debug("Data in {} still recent... skipping refresh.".format(filename))
                    run_query = False
                    with open(file_path, "r") as saved_data:
                        response_json = json.load(saved_data)

        if not self.dev_offline:
            if run_query:
                response = requests.get(url)

                try:
                    response.raise_for_status()
                except HTTPError as e:
                    # log error and terminate query if status code is not 200
                    logger.error("REQUEST FAILED WITH STATUS CODE: {} - {}".format(response.status_code, e))
                    sys.exit()

                response_json = response.json()
                logger.debug("Response (JSON): {}".format(response_json))
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    response_json = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    "FILE {} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit()

        if self.save_data or check_for_saved_data:
            if run_query:
                if not os.path.exists(file_dir):
                    os.makedirs(file_dir)

                with open(file_path, "w", encoding="utf-8") as data_out:
                    json.dump(response_json, data_out, ensure_ascii=False, indent=2)

        return response_json

    def fetch_player_data(self, player_id, week):
        player = self.player_data.get(str(player_id))
        if int(week) <= int(self.week_for_report):
            player["stats"] = self.player_stats_data_by_week.get(str(week)).get(str(player_id))
            player["projected"] = self.player_projected_stats_data_by_week[str(week)].get(str(player_id))
        return player

    def map_data_to_base(self, base_league_class):
        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague

        league.name = self.league_info.get("name")
        league.week = int(self.current_week)
        league.season = self.league_info.get("season")
        league.num_teams = self.league_settings.get("num_teams")
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.faab_budget = int(self.league_settings.get("waiver_budget"))
        if league.faab_budget > 0:
            league.is_faab = True
        league.url = self.base_url + "league/" + str(self.league_id)

        # TODO: hook up to collected player stats by week
        league.player_data_by_week_function = None
        league.player_data_by_week_key = None

        league.bench_positions = [
            str(bench_position) for bench_position in self.config.get("Configuration", "bench_positions").split(",")]

        for position, count in self.roster_positions.items():
            pos_name = position
            pos_count = count

            pos_counter = deepcopy(pos_count)
            while pos_counter > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_counter -= 1

            # if pos_name == "FLEX":
            #     league.flex_positions = ["WR", "RB"]
            # TODO: how to tell the difference when player starting positions are not specified?
            if pos_name == "FLEX":
                flex_positions = ["WR", "RB", "TE"]
                if len(flex_positions) > len(league.flex_positions):
                    league.flex_positions = flex_positions
            elif pos_name == "SUPER_FLEX":
                flex_positions = ["QB", "WR", "RB", "TE"]
                if len(flex_positions) > len(league.flex_positions):
                    league.flex_positions = flex_positions

            # if pos_name != "D/ST" and "/" in pos_name:
            #     pos_name = "FLEX"

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = pos_count

        for week, weekly_matchups in self.matchups_by_week.items():
            if int(week) <= int(self.week_for_report):
                matchups_week = str(week)
                league.teams_by_week[str(week)] = {}
                league.matchups_by_week[str(week)] = []

                for matchup_id, matchup in weekly_matchups.items():
                    base_matchup = BaseMatchup()

                    matchup_teams = matchup.get("teams")

                    base_matchup.week = int(matchups_week)
                    base_matchup.complete = True if int(week) <= int(self.current_week) else False
                    base_matchup.tied = True if float(matchup_teams[0].get("points")) == float(
                        matchup_teams[1].get("points")) else False

                    for team in matchup_teams:
                        base_team = BaseTeam()

                        team_info = self.rosters_by_week[str(week)][str(team.get("roster_id"))].get("info")

                        base_team.week = int(matchups_week)
                        base_team.name = team_info.get("owner").get("metadata").get("team_name") if team_info.get(
                            "owner").get("metadata").get("team_name") else team_info.get("owner").get("display_name")

                        for manager in [team_info.get("owner")] + team_info.get("co_owners"):
                            base_manager = BaseManager()

                            base_manager.manager_id = manager.get("user_id")
                            base_manager.email = None
                            base_manager.name = manager.get("display_name")

                            base_team.managers.append(base_manager)

                        base_team.manager_str = ", ".join([manager.name for manager in base_team.managers])

                        # TODO: change team_key to team_id universally
                        base_team.team_id = team.get("roster_id")
                        base_team.team_key = team.get("roster_id")
                        base_team.points = round(float(team.get("points")), 2)
                        # TODO: sum projected points from players
                        base_team.projected_points = None

                        base_team.num_moves = len(self.league_transactions_by_week.get(str(week), {}).get(
                            str(base_team.team_id), {}).get("moves", []))
                        base_team.num_trades = len(self.league_transactions_by_week.get(str(week), {}).get(
                            str(base_team.team_id), {}).get("trades", []))

                        team_settings = team_info.get("settings")

                        base_team.waiver_priority = team_settings.get("waiver_position")
                        base_team.faab = league.faab_budget - int(team_settings.get("waiver_budget_used"))
                        base_team.url = None

                        base_team.wins = int(team_settings.get("wins"))
                        base_team.losses = int(team_settings.get("losses"))
                        base_team.ties = int(team_settings.get("ties"))
                        base_team.percentage = round(float(base_team.wins / (base_team.wins + base_team.losses + base_team.ties)), 3)

                        # TODO: must build streaks from custom standings week by week
                        base_team.streak_str = "N/A"
                        # if team > 0:
                        #     base_team.streak_type = "W"
                        # elif team < 0:
                        #     base_team.streak_type = "L"
                        # else:
                        #     base_team.streak_type = "T"
                        # base_team.streak_len = None
                        # base_team.streak_str = None
                        base_team.points_for = float(str(team_settings.get("fpts")) + "." + str(team_settings.get("fpts_decimal")))
                        base_team.points_against = float(str(team_settings.get("fpts_against")) + "." + str(team_settings.get("fpts_against_decimal")))

                        for roster in self.current_rosters:
                            if int(roster.get("roster_id")) == int(base_team.team_id):
                                base_team.rank = int(self.current_rosters.index(roster) + 1)

                        # add team to matchup teams
                        base_matchup.teams.append(base_team)

                        # add team to league teams by week
                        league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                        if not base_matchup.tied:
                            if float(matchup_teams[0].get("points")) > float(matchup_teams[1].get("points")):
                                if int(matchup_teams[0].get("roster_id")) == int(base_team.team_id):
                                    base_matchup.winner = base_team
                                else:
                                    base_matchup.loser = base_team
                        else:
                            # TODO: how to set winner/loser with ties?
                            pass

                    # add matchup to league matchups by week
                    league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                league_team = league.teams_by_week.get(str(week)).get(str(team_id))  # type: BaseTeam

                starters = roster.get("starters")

                team_filled_positions = deepcopy(self.league_info.get("roster_positions"))  # type: list
                if self.league_settings.get("reserve_slots"):
                    team_filled_positions.extend(["BN"] * self.league_settings.get("reserve_slots"))
                if self.league_settings.get("taxi_slots"):
                    team_filled_positions.extend(["BN"] * self.league_settings.get("taxi_slots"))
                for player in roster.get("players"):
                    if player:
                        base_player = BasePlayer()

                        base_player.week_for_report = int(week)
                        base_player.player_id = player.get("player_id")
                        # TODO: missing bye
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
                        else:
                            base_player.first_name = player.get("first_name")
                            base_player.last_name = player.get("last_name")
                            base_player.full_name = player.get("full_name")
                        base_player.headshot_url = None
                        base_player.owner_team_id = None
                        base_player.owner_team_id = None
                        base_player.percent_owned = None

                        reception_scoring_value = self.league_info.get("scoring_settings").get("rec")
                        player_stats = player.get("stats")
                        player_projected_stats = player.get("projected")
                        if player_stats:
                            if reception_scoring_value == 1.0:
                                base_player.points = player_stats.get("pts_ppr", 0)
                                base_player.projected_points = player_projected_stats.get("pts_ppr", 0)
                            elif reception_scoring_value == 0.5:
                                base_player.points = player_stats.get("pts_half_ppr", 0)
                                base_player.projected_points = player_projected_stats.get("pts_half_ppr", 0)
                            else:
                                base_player.points = player_stats.get("pts_std", 0)
                                base_player.projected_points = player_projected_stats.get("pts_std", 0)
                        else:
                            base_player.points = 0
                            base_player.projected_points = 0

                        base_player.position_type = "O" if base_player.display_position in self.offensive_positions else "D"
                        base_player.primary_position = player.get("position")

                        if player in starters:
                            if base_player.primary_position in team_filled_positions:
                                base_player.selected_position = base_player.primary_position
                                base_player.selected_position_is_flex = False
                                team_filled_positions.pop(team_filled_positions.index(base_player.primary_position))
                            elif base_player.primary_position in league.flex_positions:
                                base_player.selected_position = "FLEX"
                                base_player.selected_position_is_flex = True
                                try:
                                    team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))
                                except ValueError:
                                    base_player.selected_position = "SUPER_FLEX"
                                    team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))
                        else:
                            base_player.selected_position = "BN"
                            base_player.selected_position_is_flex = False
                            team_filled_positions.pop(team_filled_positions.index(base_player.selected_position))

                        base_player.status = player.get("status")

                        base_player.eligible_positions = player.get("fantasy_positions")

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

        league.current_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.rank)

        return league
