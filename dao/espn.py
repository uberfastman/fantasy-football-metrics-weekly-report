__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import json
import logging
import os
import sys
from copy import deepcopy
from typing import List

import requests
from ff_espn_api import League, Settings, Team
from ff_espn_api.box_player import BoxPlayer
from ff_espn_api.box_score import BoxScore
from ff_espn_api.constant import POSITION_MAP
from ff_espn_api.league import checkRequestStatus

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseManager, BasePlayer, BaseStat

logger = logging.getLogger(__name__)

# Suppress ESPN API debug logging
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

        self.offensive_positions = ["QB", "RB", "WR", "TE", "K", "RB/WR", "RB/WR/TE", "QB/RB/WR/TE"]
        self.defensive_positions = ["D/ST"]

        espn_auth_file = os.path.join(base_dir, config.get("ESPN", "espn_auth_dir"), "private.json")
        with open(espn_auth_file, "r") as auth:
            espn_auth_json = json.load(auth)

        self.league = LeagueWrapper(
            league_id=self.league_id,
            year=int(self.season),
            espn_s2=espn_auth_json.get("espn_s2"),
            swid=espn_auth_json.get("swid")
        )  # type: LeagueWrapper

        self.league_settings = self.league.settings
        self.league_settings_json = self.league.settings_json
        self.league_standings = self.league.standings()

        self.season = self.league.year
        self.current_week = self.league.current_week
        self.num_playoff_slots = int(self.league_settings.playoff_team_count)
        self.num_regular_season_weeks = int(self.league.settings.reg_season_count)

        # use hijacked raw json since roster settings are not exposed in the API wrapper
        self.roster_positions = {
            POSITION_MAP[int(pos_id)]: pos_count for pos_id, pos_count in
            self.league_settings_json.get("rosterSettings").get("lineupSlotCounts").items()
            if pos_count > 0
        }

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week)

        self.matchups_by_week = {}
        self.matchups_json_by_week = {}
        for week_for_matchups in range(1, self.num_regular_season_weeks + 1):
            self.matchups_by_week[str(week_for_matchups)] = self.league.box_scores(int(week_for_matchups))
            self.matchups_json_by_week[str(week_for_matchups)] = self.league.box_data_json

        self.rosters_by_week = {}
        self.rosters_json_by_week = {}
        for week_for_rosters in range(1, int(self.week_for_report) + 1):
            team_rosters = {}
            for matchup in self.matchups_by_week[str(week_for_rosters)]:
                team_rosters[matchup.home_team.team_id] = matchup.home_lineup
                team_rosters[matchup.away_team.team_id] = matchup.away_lineup
            self.rosters_by_week[str(week_for_rosters)] = team_rosters

            team_rosters_json = {}
            for matchup in self.matchups_json_by_week[str(week_for_rosters)]:
                team_rosters_json[matchup["home"]["teamId"]] = matchup[
                    "home"]["rosterForCurrentScoringPeriod"]["entries"]
                team_rosters_json[matchup["away"]["teamId"]] = matchup[
                    "away"]["rosterForCurrentScoringPeriod"]["entries"]
            self.rosters_json_by_week[str(week_for_rosters)] = team_rosters_json

        self.teams_json = self.league.teams_json

    def save_and_load_data(self, file_dir, filename, data=None):
        file_path = os.path.join(file_dir, filename)

        if self.dev_offline:
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    data = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    "FILE {} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit()

        if self.save_data:
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                json.dump(data, data_out, ensure_ascii=False, indent=2)

        return data

    def map_data_to_base(self, base_league_class):
        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague

        league.name = self.league_settings.name
        league.week = int(self.current_week)
        league.season = self.season
        league.num_teams = int(self.league_settings.team_count)
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)

        # use hijacked raw json since acquisition settings are not exposed in the API wrapper
        league.faab_budget = int(self.league_settings_json.get("acquisitionSettings", {}).get("acquisitionBudget", 0))
        if league.faab_budget > 0:
            league.is_faab = True
        league.url = self.league.ENDPOINT

        # TODO: set up with ESPN player endpoint
        # league.player_data_by_week_function = self.league.player_map
        # league.player_data_by_week_key = "player_points_value"

        league.bench_positions = [
            str(bench_position) for bench_position in self.config.get("Configuration", "bench_positions").split(",")
        ]
        league.bench_positions = [
            "BE" if bench_position == "BN" else bench_position for bench_position in league.bench_positions
        ]

        for position, count in self.roster_positions.items():
            pos_name = deepcopy(position)
            pos_counter = deepcopy(int(count))
            while pos_counter > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_counter -= 1

            if pos_name == "RB/WR":
                league.flex_positions = ["RB", "WR"]
            if pos_name == "RB/WR/TE":
                league.flex_positions = ["RB", "WR", "TE"]
            if pos_name == "QB/RB/WR/TE":
                league.flex_positions = ["QB", "RB", "Wr", "TE"]

            if "/" in pos_name and pos_name != "D/ST":
                pos_name = "FLEX"

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = int(count)

        for week, matchups in self.matchups_by_week.items():
            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []
            for matchup in matchups:  # type: BoxScore
                base_matchup = BaseMatchup()

                base_matchup.week = int(week)
                base_matchup.complete = True if int(week) != int(self.current_week) else False
                base_matchup.tied = True if (matchup.home_score == matchup.away_score) else False

                for team in [matchup.home_team, matchup.away_team]:  # type: Team
                    team_json = self.teams_json[str(team.team_id)]

                    base_team = BaseTeam()

                    base_team.week = int(week)
                    base_team.name = team.team_name
                    base_team.num_moves = team_json["transactionCounter"].get("acquisitions", 0)
                    base_team.num_trades = team_json["transactionCounter"].get("trades", 0)

                    if isinstance(team.owner, list):
                        team_managers = team.owner
                    else:
                        team_managers = [team.owner]

                    for manager in team_managers:
                        base_manager = BaseManager()

                        base_manager.manager_id = None
                        base_manager.email = None
                        base_manager.name = manager

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name for manager in base_team.managers])

                    base_team.team_id = str(team.team_id)

                    team_is_home = False
                    if team.team_id == matchup.home_team.team_id:
                        team_is_home = True
                        base_team.points = float(matchup.home_score)
                    else:
                        base_team.points = float(matchup.away_score)

                    base_team.projected_points = None
                    base_team.waiver_priority = team_json["waiverRank"]
                    if league.is_faab:
                        base_team.faab = int(league.faab_budget) - int(
                            team_json["transactionCounter"].get("acquisitionBudgetSpent", 0))
                    base_team.url = "https://fantasy.espn.com/football/team?leagueId=48153503&teamId={}".format(
                        base_team.team_id)

                    # add team to matchup teams
                    base_matchup.teams.append(base_team)

                    # add team to league teams by week
                    league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # TODO: how to set winner/loser with ties?
                    if team_is_home:
                        if matchup.home_score > matchup.away_score:
                            base_matchup.winner = base_team
                        elif matchup.home_score < matchup.away_score:
                            base_matchup.loser = base_team
                        else:
                            pass
                    else:
                        if matchup.home_score > matchup.away_score:
                            base_matchup.loser = base_team
                        elif matchup.home_score < matchup.away_score:
                            base_matchup.winner = base_team
                        else:
                            pass

                # add matchup to league matchups by week
                league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                league_team = league.teams_by_week.get(str(week)).get(str(team_id))  # type: BaseTeam
                league_team_json = self.rosters_json_by_week[str(week)][int(team_id)]
                for player in roster:  # type: BoxPlayer

                    player_json = {}
                    for league_player_json in league_team_json:
                        if player.playerId == league_player_json["playerId"]:
                            player_json = league_player_json["playerPoolEntry"]["player"]

                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = str(player.playerId)
                    # TODO: missing bye
                    base_player.bye_week = None
                    base_player.display_position = player.position
                    base_player.nfl_team_id = player_json["proTeamId"]
                    base_player.nfl_team_abbr = player.proTeam
                    base_player.nfl_team_name = player.proTeam

                    if base_player.display_position == "D/ST":
                        base_player.first_name = player_json["firstName"]
                        base_player.full_name = base_player.first_name
                        base_player.nfl_team_name = base_player.first_name
                        base_player.headshot_url = \
                            "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{}.png".format(
                                base_player.nfl_team_abbr)
                    else:
                        base_player.first_name = player_json["firstName"]
                        base_player.last_name = player_json["lastName"]
                        base_player.full_name = player.name
                        base_player.headshot_url = "https://a.espncdn.com/i/headshots/nfl/players/full/{}.png".format(
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
                    base_player.selected_position = player.slot_position
                    base_player.selected_position_is_flex = True if "/" in player.slot_position and \
                                                                    player.slot_position != "D/ST" else False
                    base_player.status = player_json.get("injuryStatus")

                    for position in player.eligibleSlots:
                        base_player.eligible_positions.append(position)

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

        for ranked_team in self.league_standings:

            team = league.teams_by_week.get(str(self.week_for_report)).get(str(ranked_team.team_id))  # type: BaseTeam

            team_json = self.teams_json[str(team.team_id)]

            team.wins = int(ranked_team.wins)
            team.losses = int(ranked_team.losses)
            team.ties = team_json["record"]["overall"].get("ties", 0)
            team.percentage = round(float(team_json["record"]["overall"].get("percentage", 0)), 3)
            if ranked_team.streak_type == "WIN":
                team.streak_type = "W"
            elif ranked_team.streak_type == "LOSS":
                team.streak_type = "L"
            else:
                team.streak_type = "T"

            team.streak_len = int(ranked_team.streak_length)
            team.streak_str = str(team.streak_type) + "-" + str(ranked_team.streak_length)
            team.points_against = float(ranked_team.points_against)
            team.points_for = float(ranked_team.points_for)
            team.rank = int(ranked_team.standing)

        league.current_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.rank)

        return league


class LeagueWrapper(League):

    def __init__(self, league_id: int, year: int, espn_s2=None, swid=None):
        super().__init__(league_id, year, espn_s2, swid)

    def _fetch_teams(self):
        """Fetch teams in league"""
        params = {
            'view': 'mTeam'
        }
        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(f'ESPN API Request: url: {self.ENDPOINT} params: {params} \nESPN API Response: {r.json()}\n')
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        teams = data['teams']
        members = data['members']

        params = {
            'view': 'mMatchup',
        }
        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(f'ESPN API Request: url: {self.ENDPOINT} params: {params} \nESPN API Response: {r.json()}\n')
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        schedule = data['schedule']

        params = {
            'view': 'mRoster',
        }
        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(f'ESPN API Request: url: {self.ENDPOINT} params: {params} \nESPN API Response: {r.json()}\n')
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        team_roster = {}
        for team in data['teams']:
            team_roster[team['id']] = team['roster']

        self.teams_json = {}
        for team in teams:
            self.teams_json[str(team["id"])] = team
            manager = None
            for member in members:
                # For league that is not full the team will not have a owner field
                if 'owners' not in team or not team['owners']:
                    break
                elif member['id'] == team['owners'][0]:
                    manager = member
                    break
            roster = team_roster[team['id']]
            self.teams.append(Team(team, roster, manager, schedule))

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
            'view': 'mSettings',
        }

        r = requests.get(self.ENDPOINT, params=params, cookies=self.cookies)
        self.status = r.status_code
        self.logger.debug(f'ESPN API Request: url: {self.ENDPOINT} params: {params} \nESPN API Response: {r.json()}\n')
        checkRequestStatus(self.status)

        data = r.json() if self.year > 2017 else r.json()[0]
        self.settings_json = data['settings']
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
            'view': 'mMatchupScore',
            'scoringPeriodId': week,
        }

        filters = {"schedule": {"filterMatchupPeriodIds": {"value": [week]}}}
        headers = {'x-fantasy-filter': json.dumps(filters)}

        r = requests.get(self.ENDPOINT + '?view=mMatchup', params=params, cookies=self.cookies, headers=headers)
        self.status = r.status_code
        self.logger.debug(
            f'ESPN API Request: url: {self.ENDPOINT}?view=mMatchup params: {params} headers: {headers} \n'
            f'ESPN API Response: {r.json()}\n')
        checkRequestStatus(self.status)

        data = r.json()

        schedule = data['schedule']
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
