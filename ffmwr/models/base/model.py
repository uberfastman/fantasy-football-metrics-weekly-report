from __future__ import annotations

__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ffmwr.calculate.playoff_probabilities import PlayoffProbabilities
from ffmwr.features.bad_boy import BadBoyFeature
from ffmwr.features.beef import BeefFeature
from ffmwr.features.high_roller import HighRollerFeature
from ffmwr.utilities.settings import AppSettings
from ffmwr.utilities.utils import FFMWRPythonObjectJson, generate_normalized_player_key


class BaseLeague(FFMWRPythonObjectJson):
    def __init__(
        self,
        settings: AppSettings,
        platform: str,
        league_id: str,
        season: int,
        week_for_report: int,
        root_dir: Path,
        data_dir: Path,
        save_data: bool = True,
        offline: bool = False,
    ):
        super().__init__()

        # attributes set during instantiation
        self.settings: AppSettings = settings
        self.platform: str = platform
        self.league_id: str = league_id
        self.season: int = season
        self.week_for_report: int = week_for_report
        self.root_dir: Path = root_dir
        self.data_dir: Path = data_dir / f"{self.season}" / self.platform / self.league_id
        self.league_data_file_path: Path = self.data_dir / f"week_{self.week_for_report}" / f"{self.league_id}.json"
        self.save_data: bool = save_data
        self.offline: bool = offline

        # attributes mapped directly from platform API data
        self.name: Optional[str] = None
        self.week: int = 0
        self.start_week: int = 1
        self.num_teams: int = 0
        self.num_playoff_slots: int = 0
        self.num_regular_season_weeks: int = 0
        self.has_divisions: bool = False
        self.num_divisions: int = 0
        self.divisions: Dict[str, str] = {}
        self.has_median_matchup: bool = False
        self.median_score: float = 0.0
        self.has_waiver_priorities: bool = False
        self.is_faab: bool = False
        self.faab_budget: int = 0
        self.url: Optional[str] = None

        # attributes calculated externally from platform API data
        self.roster_positions: List[str] = []
        self.roster_position_counts: Dict[str, int] = defaultdict(int)
        self.roster_active_slots: List[str] = []
        self.flex_positions_rb_wr: List[str] = []
        self.flex_positions_te_wr: List[str] = []
        self.flex_positions_rb_te_wr: List[str] = []
        self.flex_positions_qb_rb_te_wr: List[str] = []
        self.flex_positions_dl: List[str] = []  # DE, DT
        self.flex_positions_db: List[str] = []  # CB, S
        self.flex_positions_idp: List[str] = []
        self.offensive_positions: List[str] = []
        self.defensive_positions: List[str] = []
        self.bench_positions: List[str] = []

        self.matchups_by_week: Dict[str, List[BaseMatchup]] = {}
        self.teams_by_week: Dict[str, Dict[str, BaseTeam]] = {}
        self.players_by_week: Dict[str, Dict[str, BasePlayer]] = {}
        self.records_by_week: Dict[str, Dict] = {}

        self.standings: List[BaseTeam] = []
        self.current_standings: List[BaseTeam] = []
        self.median_standings: List[BaseTeam] = []
        self.current_median_standings: List[BaseTeam] = []

        # TODO: find better pattern for player points retrieval instead of passing around a class method object
        # self.player_data_by_week_function: Optional[Callable] = None
        # self.player_data_by_week_key: Optional[str] = None

    # TODO: find better pattern for player points retrieval instead of passing around a class method object
    # def get_player_data_by_week(self, player_id: str, week: int = None) -> Any:
    #     return getattr(self.player_data_by_week_function(player_id, week), self.player_data_by_week_key)

    def get_custom_weekly_matchups(self, week_for_report: int) -> List[Dict[str, Dict[str, Any]]]:
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
                    "division": True
                    if ((team.division or team.division == 0) and team.division == opponent.division)
                    else False,
                }

            matchup_list.append(teams)
        return matchup_list

    def get_flex_positions_dict(self) -> Dict[str, List[str]]:
        return {
            "FLEX_RB_WR": self.flex_positions_rb_wr,
            "FLEX_TE_WR": self.flex_positions_te_wr,
            "FLEX": self.flex_positions_rb_te_wr,
            "SUPERFLEX": self.flex_positions_qb_rb_te_wr,
            "FLEX_DL": self.flex_positions_dl,
            "FLEX_DB": self.flex_positions_db,
            "FLEX_IDP": self.flex_positions_idp,
        }

    def get_playoff_probs(
        self, playoff_prob_sims: int = None, save_data: bool = False, offline: bool = False, recalculate: bool = True
    ) -> PlayoffProbabilities:
        # TODO: UPDATE USAGE OF recalculate PARAM (could use self.offline)
        return PlayoffProbabilities(
            self.settings,
            playoff_prob_sims,
            self.num_regular_season_weeks,
            self.num_playoff_slots,
            data_dir=self.data_dir,
            num_divisions=self.num_divisions,
            save_data=save_data,
            recalculate=recalculate,
            offline=offline,
        )

    def get_bad_boy_stats(self, refresh: bool = False, save_data: bool = False, offline: bool = False) -> BadBoyFeature:
        return BadBoyFeature(
            self.week_for_report, self.root_dir, self.data_dir, refresh=refresh, save_data=save_data, offline=offline
        )

    def get_beef_stats(self, refresh: bool = False, save_data: bool = False, offline: bool = False) -> BeefFeature:
        return BeefFeature(self.week_for_report, self.data_dir, refresh=refresh, save_data=save_data, offline=offline)

    def get_high_roller_stats(
        self, refresh: bool = False, save_data: bool = False, offline: bool = False
    ) -> HighRollerFeature:
        return HighRollerFeature(
            self.season, self.week_for_report, self.data_dir, refresh=refresh, save_data=save_data, offline=offline
        )


class BaseMatchup(FFMWRPythonObjectJson):
    def __init__(self):
        super().__init__()

        self.week: int = 0
        self.complete: bool = False
        self.tied: bool = False
        self.division_matchup: bool = False
        self.teams: List[BaseTeam] = []
        self.winner: BaseTeam = BaseTeam()
        self.loser: BaseTeam = BaseTeam()

    def __setattr__(self, key: str, value: Any):
        if key == "complete" and not isinstance(value, bool):
            raise ValueError('Matchup completion status can only be "True" or "False"!')
        if key == "tied" and value:
            self.winner = None
            self.loser = None
        super().__setattr__(key, value)


class BaseTeam(FFMWRPythonObjectJson):
    def __init__(self):
        super().__init__()

        self.week: int = 0
        self.name: Optional[str] = None
        self.num_moves: int = 0
        self.num_trades: int = 0
        self.managers: List[BaseManager] = []
        self.team_id: Optional[str] = None
        self.division: Optional[str] = None
        self.points: float = 0
        self.projected_points: float = 0
        self.home_field_advantage_points: float = 0
        self.waiver_priority: int = 0
        self.faab: int = 0
        self.url: Optional[str] = None
        self.roster: List[BasePlayer] = []

        # - - - - - - - - - - - -
        # custom report attributes
        # v v v v v v v v v v v v

        self.manager_str: Optional[str] = None
        self.bench_points: float = 0
        self.streak_str: Optional[str] = None
        self.division_streak_str: Optional[str] = None

        self.bad_boy_points: int = 0
        self.worst_offense: Optional[str] = None
        self.worst_offense_score: int = 0
        self.num_offenders: int = 0

        self.total_weight: float = 0.0
        self.tabbu: float = 0.0

        self.fines_count: int = 0
        self.fines_total: float = 0.0
        self.worst_violation: Optional[str] = None
        self.worst_violation_fine: float = 0.0
        self.num_violators: int = 0

        self.positions_filled_active: List[str] = []
        self.coaching_efficiency: Union[float, str] = 0.0
        self.luck: float = 0
        self.optimal_points: float = 0
        self.weekly_overall_record: BaseRecord = BaseRecord()
        self.record: BaseRecord = BaseRecord()
        self.current_record: BaseRecord = BaseRecord()
        self.median_record: BaseRecord = BaseRecord()
        self.current_median_record: BaseRecord = BaseRecord()
        self._combined_record: BaseRecord = BaseRecord()

    def get_combined_record(self) -> BaseRecord:
        self._combined_record = BaseRecord(
            team_id=self.team_id,
            team_name=self.name,
            wins=self.record.get_wins() + self.current_median_record.get_wins(),
            losses=self.record.get_losses() + self.current_median_record.get_losses(),
            ties=self.record.get_ties() + self.current_median_record.get_ties(),
        )

        return self._combined_record


# noinspection DuplicatedCode
class BaseRecord(FFMWRPythonObjectJson):
    # noinspection GrazieInspection
    def __init__(
        self,
        week: int = 0,
        wins: int = 0,
        ties: int = 0,
        losses: int = 0,
        percentage: float = 0.0,
        points_for: float = 0.0,
        points_against: float = 0.0,
        streak_type: str = None,
        streak_len: int = 0,
        team_id: str = None,
        team_name: str = None,
        rank: int = None,
        division: str = None,
        division_wins: int = 0,
        division_ties: int = 0,
        division_losses: int = 0,
        division_percentage: float = 0.0,
        division_points_for: float = 0.0,
        division_points_against: float = 0.0,
        division_streak_type: str = None,
        division_streak_len: int = None,
        division_rank: int = None,
        division_opponents_dict: Dict = None,
    ):
        """Custom team record object.

        :param week: week if record_type is "weekly"
        """
        super().__init__()

        self.team_id: str = team_id
        self.team_name: str = team_name

        if week > 0:
            self._record_type: str = "weekly"
            self.week: int = week
        else:
            self._record_type: str = "overall"

        self._wins: int = wins
        self._ties: int = ties
        self._losses: int = losses
        self._points_for: float = points_for
        self._points_against: float = points_against
        self._streak_type: str = streak_type
        self._streak_len: int = streak_len
        self.rank: int = rank
        self._percentage: float = (
            percentage if percentage else self._calculate_percentage(self._wins, self._ties, self._losses)
        )
        self._record_str: str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str: str = self._format_record(self._wins, self._ties, self._losses, self._points_for)

        self.division: str = division
        self._division_wins: int = division_wins
        self._division_ties: int = division_ties
        self._division_losses: int = division_losses
        self._division_points_for: float = division_points_for
        self._division_points_against: float = division_points_against
        self._division_streak_type: str = division_streak_type
        self._division_streak_len: int = division_streak_len
        self.division_rank: int = division_rank
        self._division_percentage: float = (
            division_percentage
            if division_percentage
            else self._calculate_percentage(self._division_wins, self._division_ties, self._division_losses)
        )
        self._division_record_str: str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for
        )
        self._division_opponents_dict: Dict = division_opponents_dict

    def __setattr__(self, key: str, value: Any):
        if key == "week":
            if self._record_type == "overall":
                raise ValueError(
                    'BaseRecord.week attribute cannot be assigned when BaseRecord.record_type = "overall".'
                )

        self.__dict__[key] = value

    @staticmethod
    def _calculate_percentage(wins: int, ties: int, losses: int) -> float:
        num_matchups = wins + ties + losses
        if num_matchups > 0:
            percentage = round(float(wins / num_matchups), 3)
        else:
            percentage = round(0, 3)
        return percentage

    def _format_record(self, wins: int, ties: int, losses: int, points_for: float = None) -> str:
        if points_for is not None:
            return self._format_record_with_points_for(wins, ties, losses, points_for)
        else:
            return self._format_record_without_points_for(wins, ties, losses)

    @staticmethod
    def _format_record_with_points_for(wins: int, ties: int, losses: int, points_for: float) -> str:
        if ties > 0:
            record_str = f"{wins}-{losses}-{ties} ({round(points_for, 2)})"
        else:
            record_str = f"{wins}-{losses} ({round(points_for, 2)})"
        return record_str

    @staticmethod
    def _format_record_without_points_for(wins: int, ties: int, losses: int) -> str:
        if ties > 0:
            record_str = f"{wins}-{losses}-{ties}"
        else:
            record_str = f"{wins}-{losses}"
        return record_str

    def _update_streak(self, streak_type: str):
        if self._streak_type == streak_type:
            self._streak_len += 1
        else:
            self._streak_type = streak_type
            self._streak_len = 1

    def get_wins(self) -> int:
        return self._wins

    def add_win(self, wins: int = 1):
        self._wins += wins
        self._percentage = self._calculate_percentage(self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)
        self._update_streak("W")

    def get_losses(self) -> int:
        return self._losses

    def add_loss(self, losses: int = 1):
        self._losses += losses
        self._percentage = self._calculate_percentage(self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)
        self._update_streak("L")

    def get_ties(self) -> int:
        return self._ties

    def add_tie(self, ties: int = 1):
        self._ties += ties
        self._percentage = self._calculate_percentage(self._wins, self._ties, self._losses)
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)
        self._update_streak("T")

    def get_points_for(self) -> float:
        return self._points_for

    def add_points_for(self, points: float):
        self._points_for += points
        self._record_str = self._format_record(self._wins, self._ties, self._losses)
        self._record_and_pf_str = self._format_record(self._wins, self._ties, self._losses, self._points_for)

    def get_points_against(self) -> float:
        return self._points_against

    def add_points_against(self, points: float):
        self._points_against += points

    def get_percentage(self) -> str:
        return f"{self._percentage:.3f}"

    def get_record_str(self) -> str:
        return self._record_str

    def get_record_and_pf_str(self) -> str:
        return self._record_and_pf_str

    def get_streak_type(self) -> str:
        return self._streak_type

    def get_streak_length(self) -> int:
        return self._streak_len

    def get_streak_str(self) -> str:
        return f"{self._streak_type}-{self._streak_len}"

    def _update_division_streak(self, streak_type: str):
        if self._division_streak_type == streak_type:
            self._division_streak_len += 1
        else:
            self._division_streak_type = streak_type
            self._division_streak_len = 1

    def get_division_wins(self) -> int:
        return self._division_wins

    def add_division_win(self):
        self._division_wins += 1
        self._division_percentage = self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses
        )
        self._record_str = self._format_record(self._division_wins, self._division_ties, self._division_losses)
        self._record_and_pf_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for
        )
        self._update_division_streak("W")

    def get_division_losses(self) -> int:
        return self._division_losses

    def add_division_loss(self):
        self._division_losses += 1
        self._division_percentage = self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses
        )
        self._record_str = self._format_record(self._division_wins, self._division_ties, self._division_losses)
        self._record_and_pf_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for
        )
        self._update_division_streak("L")

    def get_division_ties(self) -> int:
        return self._division_ties

    def add_division_tie(self):
        self._division_ties += 1
        self._division_percentage = self._calculate_percentage(
            self._division_wins, self._division_ties, self._division_losses
        )
        self._record_str = self._format_record(self._division_wins, self._division_ties, self._division_losses)
        self._record_and_pf_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for
        )
        self._update_division_streak("T")

    def get_division_points_for(self) -> float:
        return self._division_points_for

    def add_division_points_for(self, points: float):
        self._division_points_for += points
        self._division_record_str = self._format_record(
            self._division_wins, self._division_ties, self._division_losses, self._division_points_for
        )

    def get_division_points_against(self) -> float:
        return self._division_points_against

    def add_division_points_against(self, points: float):
        self._division_points_against += points

    def get_division_percentage(self) -> str:
        return f"{self._division_percentage:.3f}"

    def get_division_record_str(self) -> str:
        return self._division_record_str

    def get_division_streak_type(self) -> str:
        return self._division_streak_type

    def get_division_streak_length(self) -> int:
        return self._division_streak_len

    def get_division_streak_str(self) -> str:
        return f"{self._division_streak_type}-{self._division_streak_len}"


class BaseManager(FFMWRPythonObjectJson):
    def __init__(self):
        super().__init__()

        self.manager_id: Optional[str] = None
        self.email: Optional[str] = None
        self.name: Optional[str] = None
        self.name_str: Optional[str] = None
        self.nickname: Optional[str] = None

    def __setattr__(self, key: str, value: Any):
        if key == "name":
            value_tokens = str(value).split()
            self.name_str = value_tokens[0]
            for token in value_tokens[1:]:
                # skip turning additional tokens into initials if token is only an integer
                try:
                    token = int(token)
                except ValueError:
                    token = f" {token[0]}."
                self.name_str += f" {token}"
            value = self.name_str
        super().__setattr__(key, value)


class BasePlayer(FFMWRPythonObjectJson):
    def __init__(self):
        super().__init__()

        self.week_for_report: int = 0
        self.player_id: Optional[str] = None
        self.headshot_url: Optional[str] = None
        self.owner_team_id: Optional[str] = None
        self.owner_team_name: Optional[str] = None
        self.percent_owned: float = 0.0

        self.first_name: Optional[str] = None
        self.last_name: Optional[str] = None
        self.full_name: Optional[str] = None

        self.nfl_team_id: Optional[str] = None
        self.nfl_team_abbr: Optional[str] = None
        self.nfl_team_name: Optional[str] = None

        self.display_position: Optional[str] = None
        self.primary_position: Optional[str] = None
        self.eligible_positions: Set[str] = set()
        self.position_type: Optional[str] = None

        self.selected_position: Optional[str] = None
        self.selected_position_is_flex: bool = False

        self.bye_week: int = 0
        self.jersey_number: Optional[int] = None
        self.status: Optional[str] = None

        self.points: float = 0.0
        self.projected_points: float = 0.0
        self.season_points: float = 0.0
        self.season_projected_points: float = 0.0
        self.season_average_points: float = 0.0

        self.stats: List[BaseStat] = []

        # - - - - - - - - - - - -
        # custom report attributes
        # v v v v v v v v v v v v

        self.bad_boy_crime: Optional[str] = None
        self.bad_boy_points: int = 0
        self.bad_boy_num_offenders: int = 0

        self.beef_weight: int = 0
        self.beef_tabbu: float = 0.0

        self.high_roller_fines_count: int = 0
        self.high_roller_fines_total: float = 0.0
        self.high_roller_worst_violation: Optional[str] = None
        self.high_roller_worst_violation_fine: float = 0.0
        self.high_roller_num_violators: int = 0

    def get_normalized_player_key(self) -> str:
        return generate_normalized_player_key(self.full_name, self.nfl_team_abbr)


class BaseStat(FFMWRPythonObjectJson):
    def __init__(self):
        super().__init__()

        self.stat_id: Optional[str] = None
        self.name: Optional[str] = None
        self.abbreviation: Optional[str] = None
        self.value: float = 0.0
