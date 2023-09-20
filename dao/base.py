__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
from collections import defaultdict
from pathlib import Path

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.covid_risk import CovidRisk
from calculate.playoff_probabilities import PlayoffProbabilities


# noinspection GrazieInspection
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
            raise TypeError(f"Object of type {type(obj)} with value of {repr(obj)} is not JSON serializable")


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
        self.start_week = 1
        self.season = None
        self.num_teams = 0
        self.num_playoff_slots = 0
        self.num_regular_season_weeks = 0
        self.has_divisions = False
        self.num_divisions = 0
        self.divisions = None
        self.has_median_matchup = False
        self.median_score = 0
        self.has_waiver_priorities = False
        self.is_faab = False
        self.faab_budget = 0
        self.url = None

        # attributes calculated externally from platform API data
        self.bench_positions = []
        self.roster_positions = []
        self.roster_position_counts = defaultdict(int)
        self.active_positions = []
        self.flex_positions_rb_wr = []
        self.flex_positions_te_wr = []
        self.flex_positions_rb_te_wr = []
        self.flex_positions_qb_rb_te_wr = []
        self.flex_positions_individual_offensive_player = []
        self.flex_positions_dl = []  # DE, DT
        self.flex_positions_db = []  # CB, S
        self.flex_positions_individual_defensive_player = []

        self.matchups_by_week = {}
        self.teams_by_week = {}
        self.players_by_week = {}
        self.records_by_week = {}

        self.standings = []
        self.current_standings = []
        self.median_standings = []
        self.current_median_standings = []

        self.player_data_by_week_function = None
        self.player_data_by_week_key = None

    def get_player_data_by_week(self, player_id, week=None):
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
                    'points_against': 50,
                    'division': True
                },
                'team2.team_id': {
                    'result': 'L',
                    'points_for': 50
                    'points_against': 100,
                    'division': True
                }
            },
            {
                'team3.team_id': {
                    'result': 'T',
                    'points_for': 75
                    'points_against': 75,
                    'division': False
                },
                'team4.team_id': {
                    'result': 'T',
                    'points_for': 75
                    'points_against': 75,
                    'division': False
                }
            }
        ]
        """

        matchup_list = []
        matchup: BaseMatchup
        for matchup in self.matchups_by_week.get(str(week_for_report)):
            if matchup.complete:
                if matchup.teams[0].points == matchup.teams[1].points:
                    is_tied = matchup.tied
                else:
                    is_tied = False

                if not is_tied:
                    winning_team = matchup.winner.team_id
                else:
                    winning_team = ""
            else:
                is_tied = True
                winning_team = ""

            teams = {}
            team: BaseTeam
            for team in matchup.teams:
                if matchup.teams.index(team) == 0:
                    opponent: BaseTeam = matchup.teams[1]
                else:
                    opponent: BaseTeam = matchup.teams[0]
                teams[str(team.team_id)] = {
                    "result": "T" if is_tied else "W" if team.team_id == winning_team else "L",
                    "points_for": team.points,
                    "points_against": opponent.points,
                    "division": True if (
                            (team.division or team.division == 0) and team.division == opponent.division) else False
                }

            matchup_list.append(teams)
        return matchup_list

    def get_flex_positions_dict(self):
        return {
            "FLEX_RB_WR": self.flex_positions_rb_wr,
            "FLEX_TE_WR": self.flex_positions_te_wr,
            "FLEX": self.flex_positions_rb_te_wr,
            "SUPERFLEX": self.flex_positions_qb_rb_te_wr,
            "FLEX_IOP": self.flex_positions_individual_offensive_player,
            "FLEX_DL": self.flex_positions_dl,
            "FLEX_DB": self.flex_positions_db,
            "FLEX_IDP": self.flex_positions_individual_defensive_player
        }

    def get_playoff_probs(self, save_data=False, playoff_prob_sims=None, dev_offline=False, recalculate=True):
        # TODO: UPDATE USAGE OF recalculate PARAM (could use self.dev_offline)
        return PlayoffProbabilities(
            self.config,
            playoff_prob_sims,
            self.num_regular_season_weeks,
            self.num_playoff_slots,
            data_dir=Path(self.data_dir) / str(self.season) / self.league_id,
            num_divisions=self.num_divisions,
            save_data=save_data,
            recalculate=recalculate,
            dev_offline=dev_offline
        )

    def get_bad_boy_stats(self, save_data=False, dev_offline=False, refresh=False):
        return BadBoyStats(
            Path(self.data_dir) / str(self.season) / self.league_id,
            save_data=save_data,
            dev_offline=dev_offline,
            refresh=refresh
        )

    def get_beef_stats(self, save_data=False, dev_offline=False, refresh=False):
        return BeefStats(
            Path(self.data_dir) / str(self.season) / self.league_id,
            save_data=save_data,
            dev_offline=dev_offline,
            refresh=refresh
        )

    def get_covid_risk(self, save_data=False, dev_offline=False, refresh=False):
        return CovidRisk(
            self.config,
            Path(self.data_dir) / str(self.season) / self.league_id,
            season=self.season,
            week=self.week_for_report,
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
        self.division_matchup = False
        self.teams = []
        self.winner: BaseTeam = BaseTeam()
        self.loser: BaseTeam = BaseTeam()

    def __setattr__(self, key, value):
        if key == "complete" and not isinstance(value, bool):
            raise ValueError("Matchup completion status can only be \"True\" or \"False\"!")
        if key == "tied" and value:
            self.winner = None
            self.loser = None
        super().__setattr__(key, value)


class BaseTeam(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.week = None
        self.name = None
        self.num_moves = 0
        self.num_trades = 0
        self.managers = []
        self.team_id = None
        self.division = None
        self.points = 0
        self.projected_points = 0
        self.home_field_advantage = 0
        self.waiver_priority = 0
        self.faab = 0
        self.url = None
        self.roster = []

        # custom report attributes
        self.manager_str = None
        self.bench_points = 0
        self.streak_str = None
        self.division_streak_str = None
        self.bad_boy_points = 0
        self.worst_offense = None
        self.num_offenders = 0
        self.worst_offense_score = 0
        self.total_weight = 0
        self.tabbu = 0
        self.total_covid_risk = 0
        self.positions_filled_active = []
        self.coaching_efficiency = 0
        self.luck = 0
        self.optimal_points = 0
        self.weekly_overall_record = BaseRecord()
        self.record = BaseRecord()
        self.current_record = BaseRecord()
        self.median_record = BaseRecord()
        self.current_median_record = BaseRecord()
        self._combined_record = BaseRecord()

    # def __setattr__(self, key, value):
    #     if key == "manager_str":
    #         value_tokens = str(value).split()
    #         self.name_str = value_tokens[0]
    #         for token in value_tokens[1:]:
    #             self.name_str += " " + token[0] + "."
    #         value = self.name_str
    #     super().__setattr__(key, value)

    def get_combined_record(self):
        self._combined_record = BaseRecord(
            team_id=self.team_id,
            team_name=self.name,
            wins=self.record.get_wins() + self.current_median_record.get_wins(),
            losses=self.record.get_losses() + self.current_median_record.get_losses(),
            ties=self.record.get_ties() + self.current_median_record.get_ties()
        )

        return self._combined_record


# noinspection DuplicatedCode
class BaseRecord(FantasyFootballReportObject):

    # noinspection GrazieInspection
    def __init__(self, week=0, wins=0, ties=0, losses=0, percentage=0, points_for=0, points_against=0,
                 streak_type=None, streak_len=0, team_id=None, team_name=None, rank=None, division=None,
                 division_wins=0, division_ties=0, division_losses=0, division_percentage=0, division_points_for=0,
                 division_points_against=0, division_streak_type=None, division_streak_len=None, division_rank=None,
                 division_opponents_dict=None):
        """Custom team record object.

        :param week: week if record_type is "weekly"
        """
        super().__init__()

        self.team_id = team_id
        self.team_name = team_name

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
        self.rank = rank
        self._percentage = percentage if percentage else self._calculate_percentage(
            self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)

        self.division = division
        self._division_wins = division_wins
        self._division_ties = division_ties
        self._division_losses = division_losses
        self._division_points_for = division_points_for
        self._division_points_against = division_points_against
        self._division_streak_type = division_streak_type
        self._division_streak_len = division_streak_len
        self.division_rank = division_rank
        self._division_percentage = division_percentage if division_percentage else self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses)
        self._division_record_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for)
        self._division_opponents_dict = division_opponents_dict

    def __setattr__(self, key, value):
        if key == "week":
            if self._record_type == "overall":
                raise ValueError(
                    "BaseRecord.week attribute cannot be assigned when BaseRecord.record_type = \"overall\".")

        self.__dict__[key] = value

    @staticmethod
    def _calculate_percentage(wins, ties, losses):
        num_matchups = wins + ties + losses
        if num_matchups > 0:
            percentage = round(float(wins / num_matchups), 3)
        else:
            percentage = round(0, 3)
        return percentage

    def _format_record(self, wins, ties, losses, points_for=None):
        if points_for:
            return self._format_record_with_points_for(wins, ties, losses, points_for)
        else:
            return self._format_record_without_points_for(wins, ties, losses)

    @staticmethod
    def _format_record_with_points_for(wins, ties, losses, points_for):
        if ties > 0:
            record_str = f"{wins}-{losses}-{ties} ({round(points_for, 2)})"
        else:
            record_str = f"{wins}-{losses} ({round(points_for, 2)})"
        return record_str

    @staticmethod
    def _format_record_without_points_for(wins, ties, losses):
        if ties > 0:
            record_str = f"{wins}-{losses}-{ties}"
        else:
            record_str = f"{wins}-{losses}"
        return record_str

    def _update_streak(self, streak_type):
        if self._streak_type == streak_type:
            self._streak_len += 1
        else:
            self._streak_type = streak_type
            self._streak_len = 1

    def get_wins(self):
        return self._wins

    def add_win(self, wins=1):
        self._wins += wins
        self._percentage = self._calculate_percentage(self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)
        self._update_streak("W")

    def get_losses(self):
        return self._losses

    def add_loss(self, losses=1):
        self._losses += losses
        self._percentage = self._calculate_percentage(self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)
        self._update_streak("L")

    def get_ties(self):
        return self._ties

    def add_tie(self, ties=1):
        self._ties += ties
        self._percentage = self._calculate_percentage(self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)
        self._update_streak("T")

    def get_points_for(self):
        return self._points_for

    def add_points_for(self, points):
        self._points_for += points
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)

    def get_points_against(self):
        return self._points_against

    def add_points_against(self, points):
        self._points_against += points

    def get_percentage(self):
        return f"{self._percentage:.3f}"

    def get_record_str(self):
        return self._record_str

    def get_record_and_pf_str(self):
        return self._record_and_pf_str

    def get_streak_type(self):
        return self._streak_type

    def get_streak_length(self):
        return self._streak_len

    def get_streak_str(self):
        return f"{self._streak_type}-{self._streak_len}"

    def _update_division_streak(self, streak_type):
        if self._division_streak_type == streak_type:
            self._division_streak_len += 1
        else:
            self._division_streak_type = streak_type
            self._division_streak_len = 1

    def get_division_wins(self):
        return self._division_wins

    def add_division_win(self):
        self._division_wins += 1
        self._division_percentage = self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses)
        self._record_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses)
        self._record_and_pf_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for)
        self._update_division_streak("W")

    def get_division_losses(self):
        return self._division_losses

    def add_division_loss(self):
        self._division_losses += 1
        self._division_percentage = self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses)
        self._record_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses)
        self._record_and_pf_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for)
        self._update_division_streak("L")

    def get_division_ties(self):
        return self._division_ties

    def add_division_tie(self):
        self._division_ties += 1
        self._division_percentage = self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses)
        self._record_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses)
        self._record_and_pf_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for)
        self._update_division_streak("T")

    def get_division_points_for(self):
        return self._division_points_for

    def add_division_points_for(self, points):
        self._division_points_for += points
        self._division_record_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for)

    def get_division_points_against(self):
        return self._division_points_against

    def add_division_points_against(self, points):
        self._division_points_against += points

    def get_division_percentage(self):
        return f"{self._division_percentage:.3f}"

    def get_division_record_str(self):
        return self._division_record_str

    def get_division_streak_type(self):
        return self._division_streak_type

    def get_division_streak_length(self):
        return self._division_streak_len

    def get_division_streak_str(self):
        return f"{self._division_streak_type}-{self._division_streak_len}"


class BaseManager(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.manager_id = None
        self.email = None
        self.name = None
        self.name_str = None

    def __setattr__(self, key, value):
        if key == "name":
            value_tokens = str(value).split()
            self.name_str = value_tokens[0]
            for token in value_tokens[1:]:
                self.name_str += " " + token[0] + "."
            value = self.name_str
        super().__setattr__(key, value)


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
        self.season_projected_points = 0
        self.season_average_points = 0
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
        self.covid_risk = 0


class BaseStat(FantasyFootballReportObject):

    def __init__(self):
        super().__init__()

        self.stat_id = None
        self.name = None
        self.value = None
