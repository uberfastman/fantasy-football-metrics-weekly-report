__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import collections
import logging
import os

from yffpy.data import Data
from yffpy.models import Game, League, Settings, Standings, Player
from yffpy.query import YahooFantasyFootballQuery

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.playoff_probabilities import PlayoffProbabilities
from report.utils import user_week_input_validation

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# Suppress YahooFantasyFootballQuery debug logging
logging.getLogger("yffpy.query").setLevel(level=logging.INFO)


class LeagueData(object):

    def __init__(self,
                 config,
                 yahoo_game_id,
                 yahoo_league_id,
                 yahoo_auth_dir,
                 data_dir,
                 week_for_report,
                 save_data=True,
                 dev_offline=False):

        self.config = config
        self.data_dir = data_dir
        self.league_id = yahoo_league_id
        self.yahoo_data = Data(self.data_dir, save_data=save_data, dev_offline=dev_offline)
        self.yahoo_query = YahooFantasyFootballQuery(yahoo_auth_dir, self.league_id, yahoo_game_id,
                                                     offline=dev_offline)

        if yahoo_game_id and yahoo_game_id != "nfl":
            yahoo_fantasy_game = self.yahoo_data.retrieve(str(yahoo_game_id) + "-game-metadata",
                                                          self.yahoo_query.get_game_metadata_by_game_id,
                                                          params={"game_id": yahoo_game_id},
                                                          data_type_class=Game)
        else:
            yahoo_fantasy_game = self.yahoo_data.retrieve("current-game-metadata",
                                                          self.yahoo_query.get_current_game_metadata,
                                                          data_type_class=Game)

        self.league_key = yahoo_fantasy_game.game_key + ".l." + self.league_id
        self.season = yahoo_fantasy_game.season

        # import sys
        # print(self.league_key)
        # sys.exit()

        league_metadata = self.yahoo_data.retrieve(str(self.league_id) + "-league-metadata",
                                                   self.yahoo_query.get_league_metadata,
                                                   data_type_class=League,
                                                   new_data_dir=os.path.join(self.data_dir,
                                                                             str(self.season),
                                                                             self.league_key))
        self.name = league_metadata.name
        self.season = league_metadata.season

        # import sys
        # print(self.name)
        # print(league_metadata)
        # sys.exit()

        league_settings = self.yahoo_data.retrieve(str(self.league_id) + "-league-settings",
                                                   self.yahoo_query.get_league_settings,
                                                   data_type_class=Settings,
                                                   new_data_dir=os.path.join(self.data_dir,
                                                                             str(self.season),
                                                                             self.league_key))

        # import sys
        # print(league_settings)
        # sys.exit()

        self.playoff_slots = league_settings.num_playoff_teams
        self.num_regular_season_weeks = int(league_settings.playoff_start_week) - 1
        self.roster_positions = league_settings.roster_positions
        self.roster_positions_by_type = self.get_roster_slots(self.roster_positions)

        # import sys
        # print(self.playoff_slots)
        # print(self.num_regular_season_weeks)
        # print(self.roster_positions)
        # sys.exit()

        self.standings = self.yahoo_data.retrieve(str(self.league_id) + "-league-standings",
                                                  self.yahoo_query.get_league_standings,
                                                  data_type_class=Standings,
                                                  new_data_dir=os.path.join(self.data_dir,
                                                                            str(self.season),
                                                                            self.league_key))

        # import sys
        # print(self.league_standings_data)
        # sys.exit()

        self.teams = self.yahoo_data.retrieve(str(self.league_id) + "-league-teams",
                                              self.yahoo_query.get_league_teams,
                                              new_data_dir=os.path.join(self.data_dir,
                                                                        str(self.season),
                                                                        self.league_key))

        # import sys
        # print(self.teams)
        # sys.exit()

        # validate user selection of week for which to generate report
        self.chosen_week_for_report = user_week_input_validation(self.config, week_for_report,
                                                                 league_metadata.current_week)

        # run yahoo queries requiring chosen week
        self.matchups_by_week = {}
        for wk in range(1, self.num_regular_season_weeks + 1):
            self.matchups_by_week[wk] = self.yahoo_data.retrieve("week_" + str(wk) + "-matchups_by_week",
                                                                 self.yahoo_query.get_league_matchups_by_week,
                                                                 params={"chosen_week": wk},
                                                                 new_data_dir=os.path.join(self.data_dir,
                                                                                           str(self.season),
                                                                                           self.league_key,
                                                                                           "week_" + str(wk)))

        # import sys
        # print(self.matchups_by_week)
        # sys.exit()

        self.rosters_by_week = {}
        for wk in range(1, int(self.chosen_week_for_report) + 1):
            self.rosters_by_week[str(wk)] = {
                str(team.get("team").team_id):
                    self.yahoo_data.retrieve(
                        str(team.get("team").team_id) + "-" +
                        str(team.get("team").name.decode("utf-8")).replace(" ", "_") + "-roster",
                        self.yahoo_query.get_team_roster_player_stats_by_week,
                        params={"team_id": str(team.get("team").team_id), "chosen_week": str(wk)},
                        new_data_dir=os.path.join(
                            self.data_dir, str(self.season), self.league_key, "week_" + str(wk), "rosters")
                    ) for team in self.teams
            }

        # import sys
        # print(self.rosters_by_week.keys())
        # sys.exit()

    def get_player_data(self, player_key, week):
        return self.yahoo_data.retrieve(
            player_key,
            self.yahoo_query.get_player_stats_by_week,
            params={"player_key": player_key, "chosen_week": str(week)},
            new_data_dir=os.path.join(self.data_dir, str(self.season), self.league_key, "week_" + str(week), "players"),
            data_type_class=Player
        )

    def get_custom_scoreboard(self, chosen_week):
        """
        get weekly matchup data

        result format is like:
        [
            {
                'team1': {
                    'result': 'W',
                    'score': 100
                },
                'team2': {
                    'result': 'L',
                    'score': 50
                }
            },
            {
                'team3': {
                    'result': 'T',
                    'score': 75
                },
                'team4': {
                    'result': 'T',
                    'score': 75
                }371.l.52364
            }
        ]
        """

        matchups = self.matchups_by_week.get(int(chosen_week))
        matchup_list = []
        for matchup in matchups:

            matchup = matchup.get("matchup")
            if matchup.status == "postevent":
                winning_team = matchup.winner_team_key
                is_tied = int(matchup.is_tied) if matchup.is_tied else 0
            elif matchup.status == "midevent":
                winning_team = ""
                is_tied = 1
            else:
                winning_team = ""
                is_tied = 0

            teams = {}
            for team in matchup.teams:
                team = team.get("team")
                teams[team.name] = {
                    "result": "T" if is_tied else "W" if team.team_key == winning_team else "L",
                    "score": team.team_points.total
                }

            matchup_list.append(teams)
        return matchup_list

    def get_teams_with_points(self, week_for_report):

        matchups = self.matchups_by_week.get(int(week_for_report))
        teams_with_points = []
        for matchup in matchups:
            for team in matchup.get("matchup").teams:
                teams_with_points.append(team.get("team"))

        return teams_with_points

    @staticmethod
    def get_roster_slots(roster_positions):

        position_counts = collections.defaultdict(int)
        positions_active = []
        positions_flex = []
        positions_bench = ["BN", "IR"]
        for roster_position in roster_positions:

            roster_position = roster_position.get("roster_position")

            position_name = roster_position.position
            position_count = int(roster_position.count)

            count = position_count
            while count > 0:
                if position_name not in positions_bench:
                    positions_active.append(position_name)
                count -= 1

            if position_name == "W/R":
                positions_flex = ["WR", "RB"]
            if position_name == "W/R/T":
                positions_flex = ["WR", "RB", "TE"]
            if position_name == "Q/W/R/T":
                positions_flex = ["QB", "WR", "RB", "TE"]

            if "/" in position_name:
                position_name = "FLEX"

            position_counts[position_name] += position_count

        roster_positions_by_type = {
            "position_counts": position_counts,
            "positions_active": positions_active,
            "positions_flex": positions_flex,
            "positions_bench": positions_bench
        }

        # import sys
        # print(self.roster_positions)
        # sys.exit()

        return roster_positions_by_type

    def get_playoff_probs(self, save_data=False, playoff_prob_sims=None, dev_offline=False, recalculate=True):
        # TODO: UPDATE USAGE OF recalculate PARAM (could use self.dev_offline)

        playoff_probs = PlayoffProbabilities(
            int(playoff_prob_sims) if playoff_prob_sims is not None else self.config.getint("Configuration",
                                                                                            "num_playoff_simulations"),
            self.num_regular_season_weeks,
            self.playoff_slots,
            data_dir=os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=save_data,
            recalculate=recalculate,
            dev_offline=dev_offline
        )

        # import sys
        # print(self.playoff_probs_data)
        # sys.exit()

        return playoff_probs

    def get_bad_boy_stats(self, save_data=False, dev_offline=False):
        bad_boy_stats = BadBoyStats(
            os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=save_data,
            dev_offline=dev_offline)

        # import sys
        # print(self.bad_boy_stats)
        # sys.exit()

        return bad_boy_stats

    def get_beef_stats(self, save_data=False, dev_offline=False):

        beef_stats = BeefStats(
            os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=save_data,
            dev_offline=dev_offline)

        # import sys
        # print(self.beef_rank)
        # sys.exit()

        return beef_stats
