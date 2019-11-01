__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import json
import os
from collections import defaultdict

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.playoff_probabilities import PlayoffProbabilities


def complex_json_handler(obj):
    """Custom handler to allow custom objects to be serialized into json.

    :param obj: custom object to be serialized into json
    :return: serializable version of the custom object
    """
    if hasattr(obj, "serialized"):
        return obj.serialized()
    else:
        try:
            return str(obj, "utf-8")
        except TypeError:
            raise TypeError("Object of type %s with value of %s is not JSON serializable" % (type(obj), repr(obj)))


class FantasyFootballReportObject(object):
    """Base Fantasy Football Report object.
    """

    def __init__(self):
        """Instantiate a Yahoo fantasy football object.
        """

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return self.to_json()

    def subclass_dict(self):
        """Derive snake case dict keys from custom object type camel case class names.

        :return: dict with snake case strings of all subclasses of YahooFantasyObject as keys and subclasses as values
        """
        return {cls.__name__: cls for cls in self.__class__.__mro__[-2].__subclasses__()}

    def clean_data_dict(self):
        """Recursive method to un-type custom class type objects for serialization.

        :return: dictionary that extracts serializable data from custom objects
        """
        clean_dict = {}
        for k, v in self.__dict__.items():
            clean_dict[k] = v.clean_data_dict() if type(v) in self.subclass_dict().values() else v
        return clean_dict

    def serialized(self):
        """Pack up all object content into nested dictionaries for json serialization.

        :return: serializable dictionary
        """
        serializable_dict = dict()
        for a, v in self.clean_data_dict().items():
            if hasattr(v, "serialized"):
                serializable_dict[a] = v.serialized()
            else:
                serializable_dict[a] = v
        return serializable_dict

    def to_json(self):
        """Serialize the class object to json.

        :return: json string derived from the serializable version of the class object
        """
        return json.dumps(self.serialized(), indent=2, default=complex_json_handler, ensure_ascii=False)


class BaseLeague(FantasyFootballReportObject):

    def __init__(self, week_for_report, league_id, config, data_dir, save_data=True, dev_offline=False):
        super().__init__()

        # attributes set during instantiation
        self.config = config
        self.league_id = league_id
        self.data_dir = data_dir
        self.week_for_report = week_for_report
        self.save_data = save_data
        self.dev_offline = dev_offline

        # attributes mapped directly from platform API data
        self.name = None
        self.week = None
        self.season = None
        self.num_teams = 0
        self.num_playoff_slots = 0
        self.num_regular_season_weeks = 0
        self.is_faab = False
        self.faab_budget = 0
        self.url = None

        # attributes calculated externally from platform API data
        self.bench_positions = []
        self.roster_positions = []
        self.roster_position_counts = defaultdict(int)
        self.active_positions = []
        self.flex_positions = []
        self.super_flex_positions = []

        self.matchups_by_week = {}
        self.teams_by_week = {}
        self.players_by_week = {}
        self.records_by_week = {}

        self.standings = []
        self.current_standings = []

        self.player_data_by_week_function = None
        self.player_data_by_week_key = None

    def get_player_data_by_week(self, player_id, week):
        return getattr(self.player_data_by_week_function(player_id, week), self.player_data_by_week_key)

    def get_custom_weekly_matchups(self, week_for_report):
        """
        get weekly matchup data
        result format is like:
        [
            {
                'team1.team_id': {
                    'result': 'W',
                    'points_for': 100
                    'points_against': 50
                },
                'team2.team_id': {
                    'result': 'L',
                    'points_for': 50
                    'points_against': 100
                }
            },
            {
                'team3.team_id': {
                    'result': 'T',
                    'points_for': 75
                    'points_against': 75
                },
                'team4.team_id': {
                    'result': 'T',
                    'points_for': 75
                    'points_against': 75
                }
            }
        ]
        """

        matchup_list = []
        for matchup in self.matchups_by_week.get(str(week_for_report)):  # type: BaseMatchup
            if matchup.complete:
                winning_team = matchup.winner.team_id
                is_tied = matchup.tied
            else:
                winning_team = ""
                is_tied = True

            teams = {}
            for team in matchup.teams:
                if matchup.teams.index(team) == 0:
                    opponent = matchup.teams[1]
                else:
                    opponent = matchup.teams[0]
                teams[str(team.team_id)] = {
                    "result": "T" if is_tied else "W" if team.team_id == winning_team else "L",
                    "points_for": team.points,
                    "points_against": opponent.points
                }

            matchup_list.append(teams)
        return matchup_list

    def get_roster_slots_by_type(self):
        return {
            "position_counts": self.roster_position_counts,
            "positions_active": self.active_positions,
            "positions_flex": self.flex_positions,
            "positions_super_flex": self.super_flex_positions,
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


class BaseMatchup(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.week = 0
        self.complete = False
        self.tied = False
        self.teams = []
        self.winner = BaseTeam()  # type: BaseTeam
        self.loser = BaseTeam()  # type: BaseTeam

    def __setattr__(self, name, value):
        if name == "complete" and not isinstance(value, bool):
            raise ValueError("Matchup completion status can only be \"True\" or \"False\"!")
        super().__setattr__(name, value)


class BaseTeam(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.week = None
        self.name = None
        self.num_moves = 0
        self.num_trades = 0
        self.managers = []
        self.team_id = None
        self.points = 0
        self.projected_points = 0
        self.waiver_priority = 0
        self.faab = 0
        self.url = None
        self.roster = []

        # custom report attributes
        self.manager_str = None
        self.bench_points = 0
        self.streak_str = None
        self.bad_boy_points = 0
        self.worst_offense = None
        self.num_offenders = 0
        self.worst_offense_score = 0
        self.total_weight = 0
        self.tabbu = 0
        self.positions_filled_active = []
        self.coaching_efficiency = 0
        self.luck = 0
        self.record = BaseRecord()
        self.current_record = BaseRecord()


class BaseRecord(FantasyFootballReportObject):

    def __init__(self, week=0, wins=0, ties=0, losses=0, percentage=None, points_for=0, points_against=0,
                 streak_type=None, streak_len=0, team_id=None, team_name=None, rank=None):
        """Custom team record object.

        :param week: week if record_type is "weekly"
        """
        super().__init__()

        if week > 0:
            self._record_type = "weekly"
            self.week = week
        else:
            self._record_type = "overall"

        self._wins = wins
        self._ties = ties
        self._losses = losses
        self._points_for = points_for
        self._points_against = points_against
        self._streak_type = streak_type
        self._streak_len = streak_len

        self.team_id = team_id
        self.team_name = team_name
        self.rank = rank

        self._percentage = percentage if percentage else self._calculate_percentage()
        self._record_str = self._format_record()

    def __setattr__(self, key, value):
        if key == "week":
            if self._record_type == "overall":
                raise ValueError(
                    "BaseRecord.week attribute cannot be assigned when BaseRecord.record_type = \"overall\".")

        self.__dict__[key] = value

    def _calculate_percentage(self):
        num_matchups = self._wins + self._ties + self._losses
        if num_matchups > 0:
            percentage = round(float(self._wins / num_matchups), 3)
        else:
            percentage = round(0, 3)
        return percentage

    def _format_record(self):
        if self._ties > 0:
            record_str = "{}-{}-{} ({})".format(self._wins, self._losses, self._ties, self._points_for)
        else:
            record_str = "{}-{} ({})".format(self._wins, self._losses, self._points_for)
        return record_str

    def _update_streak(self, streak_type):
        if self._streak_type == streak_type:
            self._streak_len += 1
        else:
            self._streak_type = streak_type
            self._streak_len = 1

    def get_wins(self):
        return self._wins

    def add_win(self):
        self._wins += 1
        self._percentage = self._calculate_percentage()
        self._record_str = self._format_record()
        self._update_streak("W")

    def get_losses(self):
        return self._losses

    def add_loss(self):
        self._losses += 1
        self._percentage = self._calculate_percentage()
        self._record_str = self._format_record()
        self._update_streak("L")

    def get_ties(self):
        return self._ties

    def add_tie(self):
        self._ties += 1
        self._percentage = self._calculate_percentage()
        self._record_str = self._format_record()
        self._update_streak("T")

    def get_points_for(self):
        return self._points_for

    def add_points_for(self, points):
        self._points_for += points
        self._record_str = self._format_record()

    def get_points_against(self):
        return self._points_against

    def add_points_against(self, points):
        self._points_against += points

    def get_percentage(self):
        return "%.3f" % self._percentage

    def get_record_str(self):
        return self._record_str

    def get_streak_type(self):
        return self._streak_type

    def get_streak_length(self):
        return self._streak_len

    def get_streak_str(self):
        return "{}-{}".format(self._streak_type, self._streak_len)


class BaseManager(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.manager_id = None
        self.email = None
        self.name = None


class BasePlayer(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.week_for_report = None
        self.player_id = None
        self.bye_week = 0
        self.display_position = None
        self.nfl_team_id = None
        self.nfl_team_abbr = None
        self.nfl_team_name = None
        self.first_name = None
        self.last_name = None
        self.full_name = None
        self.headshot_url = None
        self.owner_team_id = None
        self.owner_team_name = None
        self.percent_owned = 0
        self.points = 0
        self.projected_points = 0
        self.season_points = 0
        self.position_type = None
        self.primary_position = None
        self.selected_position = None
        self.selected_position_is_flex = False
        self.status = None
        self.eligible_positions = []
        self.stats = []

        # custom report attributes
        self.bad_boy_crime = None
        self.bad_boy_points = 0
        self.bad_boy_num_offenders = 0
        self.weight = 0
        self.tabbu = 0


class BaseStat(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.stat_id = None
        self.name = None
        self.value = None
