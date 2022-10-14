__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
import os
import re
import sys
import time
from copy import deepcopy
from pathlib import Path
from statistics import median
from typing import List

import colorama
import requests
from colorama import Fore, Style
from ff_espn_api import League, Settings, Team
from ff_espn_api.box_player import BoxPlayer
from ff_espn_api.box_score import BoxScore
from ff_espn_api.constant import POSITION_MAP
from ff_espn_api.league import checkRequestStatus

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from report.logger import get_logger

colorama.init()

logger = get_logger(__name__, propagate=False)

# Suppress ESPN API requests debug logging
logging.getLogger("urllib3.connectionpool").setLevel(level=logging.WARNING)
# Suppress gitpython debug logging
logging.getLogger("git.cmd").setLevel(level=logging.WARNING)
logging.getLogger("git.cmd.cmd.execute").setLevel(level=logging.WARNING)


# noinspection DuplicatedCode
class LeagueData(object):

    def __init__(self,
                 week_for_report,
                 league_id,
                 season,
                 start_week,
                 config,
                 base_dir,
                 data_dir,
                 week_validation_function,
                 save_data=True,
                 dev_offline=False):

        logger.debug("Initializing ESPN league.")

        self.league_id = league_id
        self.season = season
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        self.offensive_positions = ["QB", "RB", "WR", "TE", "K", "RB/WR", "WR/TE", "RB/WR/TE", "QB/RB/WR/TE", "OP"]
        self.defensive_positions = ["D/ST"]

        espn_auth_json = None
        espn_auth_file = Path(base_dir) / config.get("ESPN", "espn_auth_dir") / "private.json"
        if Path(espn_auth_file).is_file():
            with open(espn_auth_file, "r") as auth:
                espn_auth_json = json.load(auth)
        else:
            no_auth_msg = (
                f"{Fore.YELLOW}No \"private.json\" file found for ESPN. If generating the report for a PUBLIC league\n"
                f"then ignore this message and CONTINUE running the app. However, if generating the report\n"
                f"for a PRIVATE league then please follow the instructions in the README.md for obtaining\n"
                f"ESPN credentials. Press \"y\" to CONTINUE or \"n\" to ABORT. "
                f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
            )
            self.check_auth(no_auth_msg)

        if self.dev_offline:
            self.league = self.save_and_load_data(
                Path(self.data_dir) / str(self.season) / str(self.league_id),
                f"{self.league_id}-league_info.json"
            )
        else:
            # TODO: GET SAVE/LOAD WORKING FOR ESPN!
            # self.league = self.save_and_load_data(
            #     Path(self.data_dir) / str(self.season) / str(self.league_id),
            #     str(self.league_id) + "-league_info.json",
            #     data=LeagueWrapper(
            #         league_id=self.league_id,
            #         year=int(self.season),
            #         espn_s2=espn_auth_json.get("espn_s2"),
            #         swid=espn_auth_json.get("swid")
            #     )  # type: LeagueWrapper
            # )
            logger.debug("Retrieving ESPN league data.")
            self.league = LeagueWrapper(
                league_id=self.league_id,
                year=int(self.season),
                espn_s2=espn_auth_json.get("espn_s2") if espn_auth_json else None,
                swid=espn_auth_json.get("swid") if espn_auth_json else None
            )  # type: LeagueWrapper

        self.league_settings = self.league.settings
        self.league_settings_json = self.league.settings_json
        self.league_standings = self.league.standings()

        self.season = self.league.year
        # TODO: figure out how to get league starting week
        self.start_week = start_week or 1
        self.current_week = self.league.current_week
        self.num_playoff_slots = int(self.league_settings.playoff_team_count)
        self.num_regular_season_weeks = int(self.league.settings.reg_season_count)
        self.divisions = {
            str(division.get("id")): division.get("name")
            for division in self.league_settings_json.get("scheduleSettings").get("divisions")
        }
        self.num_divisions = len(self.divisions) if len(self.divisions) > 1 else 0
        # only ESPN (out of the supported Yahoo, Sleeper, Fleaflicker, and ESPN platforms) offers home field advantage
        if self.league_settings_json.get("scoringSettings").get("homeTeamBonus"):
            self.home_field_advantage = self.league.settings_json.get("scoringSettings").get("homeTeamBonus")
        else:
            self.home_field_advantage = 0

        # use hijacked raw json since roster settings are not exposed in the API wrapper
        self.roster_positions = {
            POSITION_MAP[int(pos_id)]: pos_count for pos_id, pos_count in
            self.league_settings_json.get("rosterSettings").get("lineupSlotCounts").items()
            if pos_count > 0
        }
        # TODO: ESPN does not currently offer a built-in median game
        self.has_median_matchup = False
        self.median_score_by_week = {}

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week, self.season)

        logger.debug("Getting ESPN matchups by week data.")
        self.matchups_by_week = {}
        self.matchups_json_by_week = {}
        for week_for_matchups in range(1, self.num_regular_season_weeks + 1):
            self.matchups_by_week[str(week_for_matchups)] = self.league.box_scores(int(week_for_matchups))
            self.matchups_json_by_week[str(week_for_matchups)] = self.league.box_data_json

            if int(week_for_matchups) <= int(self.week_for_report):
                scores = []
                for matchup in self.matchups_by_week[str(week_for_matchups)]:  # type: BoxScore
                    for team in [matchup.home_team, matchup.away_team]:  # type: Team
                        team_score = team.scores[week_for_matchups - 1]
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    self.median_score_by_week[str(week_for_matchups)] = weekly_median
                else:
                    self.median_score_by_week[str(week_for_matchups)] = 0

        logger.debug("Getting ESPN rosters by week data.")
        self.rosters_by_week = {}
        self.rosters_json_by_week = {}
        for week_for_rosters in range(1, int(self.week_for_report) + 1):
            team_rosters = {}
            for matchup in self.matchups_by_week[str(week_for_rosters)]:
                team_rosters[matchup.home_team.team_id] = matchup.home_lineup
                team_rosters[matchup.away_team.team_id] = matchup.away_lineup
            self.rosters_by_week[str(week_for_rosters)] = team_rosters

            team_rosters_json = {}
            for matchup_json in self.matchups_json_by_week[str(week_for_rosters)]:
                team_rosters_json[matchup_json["home"]["teamId"]] = matchup_json[
                    "home"]["rosterForCurrentScoringPeriod"]["entries"]
                team_rosters_json[matchup_json["away"]["teamId"]] = matchup_json[
                    "away"]["rosterForCurrentScoringPeriod"]["entries"]
            self.rosters_json_by_week[str(week_for_rosters)] = team_rosters_json

        self.teams_json = self.league.teams_json

    def check_auth(self, msg):
        logger.debug(msg)
        time.sleep(0.25)
        use_credentials = input("\n{0}".format(msg))
        if use_credentials.lower() == "y":
            logger.info("\"{0}y{1}\" -> Continuing...".format(Fore.GREEN, Style.RESET_ALL))
        elif use_credentials.lower() == "n":
            logger.info("\"{0}n{1}\" -> Aborting...".format(Fore.RED, Style.RESET_ALL))
            sys.exit(0)
        else:
            incorrect_key_msg = (
                f"{Fore.YELLOW}Please type \"{Fore.GREEN}y{Fore.YELLOW}\" to CONTINUE or \"{Fore.RED}n{Fore.YELLOW}\" "
                f"to ABORT and press {Fore.GREEN}<ENTER>{Fore.YELLOW}. "
                f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
            )
            logger.debug(incorrect_key_msg)
            self.check_auth(incorrect_key_msg)

    def save_and_load_data(self, file_dir, filename, data=None):
        file_path = Path(file_dir) / filename

        if self.dev_offline:
            logger.debug("Loading saved ESPN league data.")
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    data = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    "FILE {0} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit("...run aborted.")

        if self.save_data:
            logger.debug("Saving ESPN league data.")
            if not Path(file_dir).exists():
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                json.dump(data, data_out, ensure_ascii=False, indent=2)

        return data

    def map_data_to_base(self, base_league_class):
        logger.debug("Mapping ESPN data to base objects.")

        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague

        league.name = self.league_settings.name
        league.week = int(self.current_week)
        league.start_week = int(self.start_week)
        league.season = self.season
        league.num_teams = int(self.league_settings.team_count)
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.num_divisions = self.num_divisions
        if league.num_divisions > 0:
            league.has_divisions = True
        league.has_median_matchup = self.has_median_matchup
        league.median_score = 0
        # use hijacked raw json since acquisition settings are not exposed in the API wrapper
        league.is_faab = bool(self.league_settings_json.get("acquisitionSettings").get("isUsingAcquisitionBudget"))
        if league.is_faab:
            league.faab_budget = int(self.league_settings_json.get("acquisitionSettings").get("acquisitionBudget", 0))
        # league.url = self.league.ENDPOINT
        league.url = "https://fantasy.espn.com/football/league?leagueId={0}".format(self.league_id)

        # TODO: set up with ESPN player endpoint
        # league.player_data_by_week_function = self.league.player_map
        # league.player_data_by_week_key = "player_points_value"

        league.bench_positions = ["BN", "IR"]  # ESPN uses "BE" for the bench slot, but this app adjusts it to "BN"

        for position, count in self.roster_positions.items():
            pos_name = deepcopy(position)

            if pos_name == "BE":
                pos_name = "BN"

            if pos_name == "RB/WR":
                league.flex_positions_rb_wr = ["RB", "WR"]
                pos_name = "FLEX_RB_WR"
            if pos_name == "WR/TE":
                league.flex_positions_te_wr = ["TE", "WR"]
                pos_name = "FLEX_TE_WR"
            if pos_name == "RB/WR/TE":
                league.flex_positions_rb_te_wr = ["RB", "TE", "WR"]
                pos_name = "FLEX_RB_TE_WR"
            if pos_name == "QB/RB/WR/TE":
                league.flex_positions_qb_rb_te_wr = ["QB", "RB", "TE", "WR"]
                pos_name = "FLEX_OFFENSIVE_PLAYER"
            if pos_name == "OP":
                league.flex_positions_offensive_player = ["QB", "RB", "WR", "TE"]
                pos_name = "FLEX_OFFENSIVE_PLAYER"
            if pos_name == "DP":
                league.flex_positions_idp = ["CB", "DB", "DE", "DL", "DT", "EDR", "LB", "S"]
                pos_name = "FLEX_IDP"

            pos_counter = deepcopy(int(count))
            while pos_counter > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_counter -= 1

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = int(count)

        league_median_records_by_team = {}
        for week, matchups in self.matchups_by_week.items():
            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []
            for matchup in matchups:  # type: BoxScore
                base_matchup = BaseMatchup()

                base_matchup.week = int(week)
                base_matchup.complete = True if int(week) != int(self.current_week) else False
                base_matchup.tied = True if (matchup.home_score == matchup.away_score) else False

                matchup_teams = {
                    "home": matchup.home_team,
                    "away": matchup.away_team
                }
                for key, matchup_team in matchup_teams.items():
                    team_json = self.teams_json[str(matchup_team.team_id)]
                    base_team = BaseTeam()

                    opposite_key = "away" if key == "home" else "home"
                    team_division = matchup_team.division_id if self.num_divisions > 0 else None
                    opponent_division = matchup_teams[opposite_key].division_id if self.num_divisions > 0 else None
                    if team_division and opponent_division and team_division == opponent_division:
                        base_matchup.division_matchup = True

                    base_team.week = int(week)
                    base_team.name = matchup_team.team_name
                    base_team.num_moves = team_json["transactionCounter"].get("acquisitions", 0)
                    base_team.num_trades = team_json["transactionCounter"].get("trades", 0)

                    if isinstance(matchup_team.owner, list):
                        team_managers = matchup_team.owner
                    else:
                        team_managers = [matchup_team.owner]

                    for manager in team_managers:
                        base_manager = BaseManager()

                        base_manager.manager_id = None
                        base_manager.email = None
                        base_manager.name = re.sub(r"\W+", " ", manager)

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name_str for manager in base_team.managers])
                    base_team.team_id = str(matchup_team.team_id)

                    team_is_home = False
                    if int(base_team.team_id) == int(matchup.home_team.team_id):
                        team_is_home = True
                        base_team.home_field_advantage = self.home_field_advantage
                        base_team.points = float(matchup.home_score + base_team.home_field_advantage)
                    else:
                        base_team.points = float(matchup.away_score)

                    base_team.projected_points = None
                    base_team.waiver_priority = team_json["waiverRank"]
                    league.has_waiver_priorities = base_team.waiver_priority > 0
                    if league.is_faab:
                        base_team.faab = int(league.faab_budget) - int(
                            team_json["transactionCounter"].get("acquisitionBudgetSpent", 0))
                    base_team.url = "https://fantasy.espn.com/football/team?leagueId=48153503&teamId={0}".format(
                        base_team.team_id)

                    if matchup_team.streak_type == "WIN":
                        streak_type = "W"
                    elif matchup_team.streak_type == "LOSS":
                        streak_type = "L"
                    else:
                        streak_type = "T"

                    if team_json["record"]["division"].get("streakType") == "WIN":
                        division_streak_type = "W"
                    elif team_json["record"]["division"].get("streakType") == "LOSS":
                        division_streak_type = "L"
                    else:
                        division_streak_type = "T"

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(matchup_team.wins),
                        losses=int(matchup_team.losses),
                        ties=int(team_json["record"]["overall"].get("ties", 0)),
                        percentage=round(float(team_json["record"]["overall"].get("percentage", 0)), 3),
                        points_for=float(matchup_team.points_for),
                        points_against=float(matchup_team.points_against),
                        streak_type=streak_type,
                        streak_len=int(matchup_team.streak_length),
                        team_id=matchup_team.team_id,
                        team_name=matchup_team.team_name,
                        rank=int(matchup_team.standing),
                        division=base_team.division,
                        division_wins=int(team_json["record"]["division"].get("wins", 0)),
                        division_losses=int(team_json["record"]["division"].get("losses", 0)),
                        division_ties=int(team_json["record"]["division"].get("ties", 0)),
                        division_percentage=round(float(team_json["record"]["division"].get("percentage", 0)), 3),
                        division_streak_type=division_streak_type,
                        division_streak_len=int(team_json["record"]["division"].get("streakLength", 0))
                    )
                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if base_matchup.division_matchup:
                        base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = self.median_score_by_week.get(str(week))

                    median_record = league_median_records_by_team.get(str(base_team.team_id))  # type: BaseRecord
                    if not median_record:
                        median_record = BaseRecord(
                            team_id=base_team.team_id,
                            team_name=base_team.name,
                            points_for=(base_team.points - week_median),
                            points_against=week_median
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
                    if team_is_home:
                        if (matchup.home_score + self.home_field_advantage) > matchup.away_score:
                            base_matchup.winner = base_team
                        elif (matchup.home_score + self.home_field_advantage) < matchup.away_score:
                            base_matchup.loser = base_team
                    else:
                        if (matchup.home_score + self.home_field_advantage) > matchup.away_score:
                            base_matchup.loser = base_team
                        elif (matchup.home_score + self.home_field_advantage) < matchup.away_score:
                            base_matchup.winner = base_team

                # add matchup to league matchups by week
                league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                team_json = self.rosters_json_by_week[str(week)][int(team_id)]
                league_team = league.teams_by_week.get(str(week)).get(str(team_id))  # type: BaseTeam

                for player in roster:  # type: BoxPlayer

                    player_json = {}
                    for league_player_json in team_json:
                        if player.playerId == league_player_json["playerId"]:
                            player_json = league_player_json["playerPoolEntry"]["player"]

                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = str(player.playerId)
                    # TODO: missing bye
                    base_player.bye_week = None
                    base_player.display_position = player.position
                    base_player.nfl_team_id = player_json["proTeamId"]
                    # TODO: change back once ESPN fixes their API to not use "WSH"" instead of "WAS" for the
                    #  Washington Football Team
                    # base_player.nfl_team_abbr = player.proTeam
                    base_player.nfl_team_abbr = player.proTeam if player.proTeam != "WSH" else "WAS"
                    base_player.nfl_team_name = player.proTeam

                    if base_player.display_position == "D/ST":
                        # TODO: change back once ESPN fixes their API to not use "WSH"" instead of "WAS" for the
                        #  Washington Football Team
                        # base_player.first_name = player_json["firstName"]
                        base_player.first_name = player_json["firstName"] if player_json["firstName"] != "Washington" \
                            else "Football Team"
                        base_player.full_name = base_player.first_name
                        base_player.nfl_team_name = base_player.first_name
                        base_player.headshot_url = \
                            "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{0}.png".format(
                                base_player.nfl_team_abbr)
                    else:
                        base_player.first_name = player_json["firstName"]
                        base_player.last_name = player_json["lastName"]
                        base_player.full_name = player.name
                        base_player.headshot_url = "https://a.espncdn.com/i/headshots/nfl/players/full/{0}.png".format(
                            player.playerId)
                    base_player.owner_team_id = None
                    base_player.owner_team_name = league_team.manager_str
                    # TODO: missing percent owned
                    base_player.percent_owned = None
                    base_player.points = float(player.points)
                    base_player.projected_points = float(player.projected_points)

                    base_player.position_type = "O" if base_player.display_position in self.offensive_positions \
                        else "D"
                    base_player.primary_position = player.position

                    eligible_positions = player.eligibleSlots
                    for position in eligible_positions:
                        if position == "BE":
                            position = "BN"
                        elif position == "RB/WR":
                            position = "FLEX_RB_WR"
                        elif position == "WR/TE":
                            position = "FLEX_TE_WR"
                        elif position == "RB/WR/TE":
                            position = "FLEX_RB_TE_WR"
                        elif position == "QB/RB/WR/TE":
                            position = "FLEX_QB_RB_TE_WR"
                        elif position == "OP":
                            position = "FLEX_OFFENSIVE_PLAYER"
                        elif position == "DP":
                            position = "FLEX_IDP"

                        base_player.eligible_positions.append(position)

                    if player.slot_position == "BE":
                        base_player.selected_position = "BN"
                    elif player.slot_position == "RB/WR":
                        base_player.selected_position = "FLEX_RB_WR"
                    elif player.slot_position == "WR/TE":
                        base_player.selected_position = "FLEX_TE_WR"
                    elif player.slot_position == "RB/WR/TE":
                        base_player.selected_position = "FLEX_RB_TE_WR"
                    elif player.slot_position == "QB/RB/WR/TE":
                        base_player.selected_position = "FLEX_QB_RB_TE_WR"
                    elif player.slot_position == "OP":
                        base_player.selected_position = "FLEX_OFFENSIVE_PLAYER"
                    elif player.slot_position == "DP":
                        base_player.selected_position = "FLEX_IDP"
                    else:
                        base_player.selected_position = player.slot_position
                    base_player.selected_position_is_flex = True if "/" in player.slot_position and \
                                                                    player.slot_position != "D/ST" else False

                    base_player.status = player_json.get("injuryStatus")

                    if player_json["stats"]:
                        for stat_id, stat_value in player_json["stats"][0]["stats"].items():
                            base_stat = BaseStat()

                            base_stat.stat_id = stat_id
                            base_stat.name = None
                            base_stat.value = stat_value

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


# noinspection DuplicatedCode
class LeagueWrapper(League):

    def __init__(self, league_id: int, year: int, espn_s2=None, swid=None):
        super().__init__(league_id, year, espn_s2, swid)

    def _fetch_teams(self):
        """Fetch teams in league"""
        params = {
            "view": "mTeam"
        }
        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(
            "ESPN API Request: url: {0} params: {1} \nESPN API Response: {2}\n".format(self.ENDPOINT, params, r.json()))
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        teams = data["teams"]
        members = data["members"]

        params = {
            "view": "mMatchup",
        }
        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(
            "ESPN API Request: url: {0} params: {1} \nESPN API Response: {2}\n".format(self.ENDPOINT, params, r.json()))
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        schedule = data["schedule"]

        params = {
            "view": "mRoster",
        }
        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(
            "ESPN API Request: url: {0} params: {1} \nESPN API Response: {2}\n".format(self.ENDPOINT, params, r.json()))
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        team_roster = {}
        for team in data["teams"]:
            team_roster[team["id"]] = team["roster"]

        self.teams_json = {}
        for team in teams:
            self.teams_json[str(team["id"])] = team
            managers = None

            owners = team["owners"]
            if len(owners) > 1:
                managers = []

            for member in members:
                # For league that is not full the team will not have an owner field
                if "owners" not in team or not team["owners"]:
                    break
                elif member["id"] in owners:
                    if len(owners) > 1:
                        managers.append(member)
                    else:
                        managers = [member]
                        break
            roster = team_roster[team["id"]]

            team = Team(team, roster, None, schedule)
            team.owner = sorted(["%s %s" % (owner["firstName"], owner["lastName"]) for owner in managers])

            self.teams.append(team)

        # replace opponentIds in schedule with team instances
        for team in self.teams:
            for week, matchup in enumerate(team.schedule):
                for opponent in self.teams:
                    if matchup == opponent.team_id:
                        team.schedule[week] = opponent

        # calculate margin of victory
        for team in self.teams:
            for week, opponent in enumerate(team.schedule):
                mov = team.scores[week] - opponent.scores[week]
                team.mov.append(mov)

        # sort by team ID
        self.teams = sorted(self.teams, key=lambda x: x.team_id, reverse=False)

    def _fetch_settings(self):
        params = {
            "view": "mSettings",
        }

        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(
            "ESPN API Request: url: {0} params: {1} \nESPN API Response: {2}\n".format(self.ENDPOINT, params, r.json()))
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        self.settings_json = data["settings"]
        self.settings = Settings(self.settings_json)

    # noinspection PyAttributeOutsideInit
    def box_scores(self, week: int = None) -> List[BoxScore]:
        """Returns list of box score for a given week\n
        Should only be used with most recent season"""
        if self.year < 2019:
            raise Exception("Can't use box score before 2019")
        if not week or week > self.current_week:
            week = self.current_week

        params = {
            "view": "mMatchupScore",
            "scoringPeriodId": week,
        }

        filters = {"schedule": {"filterMatchupPeriodIds": {"value": [week]}}}
        headers = {"x-fantasy-filter": json.dumps(filters)}

        r = requests.get(self.ENDPOINT + "?view=mMatchup", params=params, cookies=self.cookies, headers=headers)
        self.status = r.status_code
        self.logger.debug(
            "ESPN API Request: url: {0}?view=mMatchup params: {1} headers: {2} \nESPN API Response: {3}\n".format(
                self.ENDPOINT, params, headers, r.json()))
        checkRequestStatus(self.status)

        data = r.json()

        schedule = data["schedule"]
        pro_schedule = self._get_nfl_schedule(week)
        positional_rankings = self._get_positional_ratings(week)
        self.box_data_json = [matchup for matchup in schedule]
        box_data = [BoxScore(matchup, pro_schedule, positional_rankings, week) for matchup in schedule]

        for team in self.teams:
            for matchup in box_data:
                if matchup.home_team == team.team_id:
                    matchup.home_team = team
                elif matchup.away_team == team.team_id:
                    matchup.away_team = team
        return box_data
