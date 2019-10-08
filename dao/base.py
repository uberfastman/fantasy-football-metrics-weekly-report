__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os
from collections import defaultdict

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.playoff_probabilities import PlayoffProbabilities
from report.utils import user_week_input_validation

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class League(object):

    def __init__(self,
                 config,
                 league_id,
                 data_dir,
                 week_for_report,
                 auth_dir=None,
                 save_data=True,
                 dev_offline=False):

        # attributes set during instantiation
        self.config = config
        self.league_id = league_id
        self.data_dir = data_dir
        self.week_for_report = user_week_input_validation(self.config, week_for_report, self.current_week)
        self.auth_dir = auth_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        # attributes mapped directly from platform API data
        self.name = None
        self.roster_positions = []
        self.bench_positions = []
        self.current_week = None
        self.season = None
        self.num_teams = 0
        self.num_playoff_slots = 0
        self.num_regular_season_weeks = 0
        self.url = None

        # attributes calculated externally from platform API data
        self.roster_position_counts = defaultdict(int)
        self.active_positions = []
        self.flex_positions = []


        self.teams = []
        self.matchups = []
        self.standings = Standings()  # type: Standings


        self.fetch_player_function = None
        self.fetch_player_params = {}

    def get_player_data(self, player_id):
        return self.fetch_player_function(player_id, **self.fetch_player_params)

    def get_standings(self, weekly_matchups):
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

        matchup_list = []
        for matchup in weekly_matchups:

            if matchup.status == "COMPLETE":
                winning_team = matchup.winner_team_key
                is_tied = 1 if matchup.tied else 0
            elif matchup.status == "INCOMPLETE":
                winning_team = ""
                is_tied = 1
            else:
                winning_team = ""
                is_tied = 0

            teams = {}
            for team in matchup.teams:
                teams[team.name] = {
                    "result": "T" if is_tied else "W" if team.team_key == winning_team else "L",
                    "score": team.team_points.total
                }

            matchup_list.append(teams)
        return matchup_list

    def get_roster_slots(self):
        return {
            "position_counts": self.roster_position_counts,
            "positions_active": self.active_positions,
            "positions_flex": self.flex_positions,
            "positions_bench": self.bench_positions
        }

    def get_playoff_probs(self, save_data=False, playoff_prob_sims=None, dev_offline=False, recalculate=True):
        # TODO: UPDATE USAGE OF recalculate PARAM (could use self.dev_offline)
        return PlayoffProbabilities(
            int(playoff_prob_sims) if playoff_prob_sims is not None else self.config.getint("Configuration",
                                                                                            "num_playoff_simulations"),
            self.num_regular_season_weeks,
            self.num_playoff_slots,
            data_dir=os.path.join(self.data_dir, str(self.season), self.league_id),
            save_data=save_data,
            recalculate=recalculate,
            dev_offline=dev_offline
        )

    def get_bad_boy_stats(self, save_data=False, dev_offline=False, refresh=False):
        return BadBoyStats(
            os.path.join(self.data_dir, str(self.season), self.league_id),
            save_data=save_data,
            dev_offline=dev_offline,
            refresh=refresh
        )

    def get_beef_stats(self, save_data=False, dev_offline=False, refresh=False):

        return BeefStats(
            os.path.join(self.data_dir, str(self.season), self.league_id),
            save_data=save_data,
            dev_offline=dev_offline,
            refresh=refresh
        )


class Standings(object):

    def __init__(self):
        pass


class Matchup(object):

    def __init__(self):
        self.status = "INCOMPLETE"  # options: INCOMPLETE, COMPLETE
        self.teams = []  # type: list
        self.tied = False  # type: bool
        self.week = 0  # type: int
        self.winner = Team()  # type: Team
        self.loser = Team()  # type: Team

    def __setattr__(self, name, value):
        if name == "status" and value not in ["INCOMPLETE", "COMPLETE"]:
            raise ValueError("MATCHUP STATUS CAN ONLY BE \"INCOMPLETE\" OR \"COMPLETE\"!")
        super().__setattr__(name, value)


class Team(object):

    def __init__(self):
        self.managers = []
        self.matchups = []
        self.name = None
        self.num_moves = 0
        self.num_trades = 0
        self.roster = []
        self.team_id = None
        self.points = 0
        self.projected_points = 0
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.streak_type = None
        self.streak_len = 0
        self.streak_str = None
        self.points_against = 0
        self.points_for = 0
        self.percentage = 0
        self.rank = 0
        self.week_for_report = None
        self.waiver_priority = 0
        self.url = None


class Manager(object):

    def __init__(self):
        pass


class Player(object):

    def __init__(self):
        pass
