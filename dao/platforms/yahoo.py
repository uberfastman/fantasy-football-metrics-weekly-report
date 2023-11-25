__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import logging
from pathlib import Path
# from collections import defaultdict
# from concurrent.futures import ThreadPoolExecutor
from statistics import median
from typing import Union, List, Callable

from yfpy.data import Data
from yfpy.models import League, Manager, Matchup, Team, Player, RosterPosition
from yfpy.query import YahooFantasySportsQuery

from dao.base import BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from dao.platforms.base.base import BaseLeagueData
from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)

# Suppress YFPY debug logging
logging.getLogger("yfpy.query").setLevel(level=logging.INFO)
logging.getLogger("yfpy.data").setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class LeagueData(BaseLeagueData):

    def __init__(self, base_dir: Path, data_dir: Path, game_id: Union[str, int],
                 league_id: str, season: int, start_week: int, week_for_report: int,
                 get_current_nfl_week_function: Callable, week_validation_function: Callable, save_data: bool = True,
                 offline: bool = False):
        super().__init__(
            "Yahoo",
            None,
            base_dir,
            data_dir,
            league_id,
            season,
            start_week,
            week_for_report,
            get_current_nfl_week_function,
            week_validation_function,
            save_data,
            offline
        )

        self.game_id = game_id or settings.platform_settings.yahoo_game_id

        self.yahoo_data = Data(self.league.data_dir, save_data=self.league.save_data, dev_offline=self.league.offline)

        yahoo_auth_dir = Path(self.base_dir) / settings.platform_settings.yahoo_auth_dir_local_path
        self.yahoo_query = YahooFantasySportsQuery(
            yahoo_auth_dir, self.league.league_id, game_code=self.game_id, game_id=self.game_id,
            offline=self.league.offline, browser_callback=False
        )

    def get_player_data(self, player_key: str, week: int = None):
        # YAHOO API QUERY: run query to retrieve stats for specific player for chosen week if supplied, else for season
        params = {"player_key": player_key}
        if week:
            params["chosen_week"] = week

            return self.yahoo_data.retrieve(
                player_key,
                self.yahoo_query.get_player_stats_by_week,
                params=params,
                new_data_dir=(
                        Path(self.league.data_dir) / str(self.league.season) / self.league.league_id / f"week_{week}"
                        / "players"
                ),
                data_type_class=Player
            )
        else:
            return self.yahoo_data.retrieve(
                player_key,
                self.yahoo_query.get_player_stats_for_season,
                params=params,
                new_data_dir=Path(self.league.data_dir) / str(self.league.season) / self.league.league_id / "players",
                data_type_class=Player
            )

    # noinspection PyTypeChecker
    def map_data_to_base(self):
        logger.debug(f"Retrieving {self.platform_display} league data and mapping it to base objects.")

        # YAHOO API QUERY: run query to retrieve all league information, including current standings
        league_info: League = self.yahoo_data.retrieve(
            f"{self.league.league_id}-league_info",
            self.yahoo_query.get_league_info,
            data_type_class=League,
            new_data_dir=(self.league.data_dir / str(self.league.season) / self.league.league_id)
        )

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

        self.league.name = league_info.name.decode()
        self.league.season = league_info.season  # this gets set already in BaseLeague by the run parameters
        self.league.week = int(league_info.current_week) or self.current_week
        self.league.start_week = int(self.start_week or league_info.start_week)
        self.league.num_regular_season_weeks = int(league_info.settings.playoff_start_week) - 1
        self.league.num_teams = int(league_info.num_teams)
        self.league.num_playoff_slots = int(league_info.settings.num_playoff_teams)
        self.league.num_divisions = len(league_info.settings.divisions)
        self.league.divisions = {
            str(division.division_id): division.name for division in league_info.settings.divisions
        }
        self.league.has_divisions = self.league.num_divisions > 0
        self.league.has_median_matchup = bool(league_info.settings.uses_median_score)
        self.league.median_score = 0
        self.league.is_faab = bool(league_info.settings.uses_faab)
        if self.league.is_faab:
            self.league.faab_budget = settings.platform_settings.yahoo_initial_faab_budget or 100
        self.league.url = league_info.url

        self.league.player_data_by_week_function = self.get_player_data
        self.league.player_data_by_week_key = "player_points_value"

        position: RosterPosition
        for position in league_info.settings.roster_positions:
            pos_attributes = self.position_mapping.get(position.position)
            pos_name = pos_attributes.get("base")
            pos_count = position.count

            if pos_attributes.get("is_flex"):
                self.league.__setattr__(
                    pos_attributes.get("league_positions_attribute"),
                    pos_attributes.get("positions")
                )

            self.league.roster_positions.append(pos_name)
            self.league.roster_position_counts[pos_name] = pos_count
            self.league.roster_active_slots.extend(
                [pos_name] * pos_count
                if pos_name not in self.league.bench_positions
                else []
            )

        logger.debug("Getting Yahoo matchups by week data.")
        # TODO: figure out how to write to json files (json.dump) in a thread-safe manner
        # YAHOO API QUERY: run yahoo queries to retrieve matchups by week for the entire season
        matchups_by_week = {}
        median_score_by_week = {}
        for wk in range(self.start_week, self.league.num_regular_season_weeks + 1):
            matchups_by_week[str(wk)] = self.yahoo_data.retrieve(
                f"week_{wk}-matchups_by_week",
                self.yahoo_query.get_league_matchups_by_week,
                params={"chosen_week": str(wk)},
                new_data_dir=(
                        self.league.data_dir / str(self.league.season) / self.league.league_id / f"week_{str(wk)}"
                )
            )

            if wk <= self.league.week_for_report:
                scores = []
                matchup: Matchup
                for matchup in matchups_by_week[str(wk)]:
                    for team in matchup.teams:
                        team_score = team.points
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    median_score_by_week[str(wk)] = weekly_median
                else:
                    median_score_by_week[str(wk)] = 0

        league_median_records_by_team = {}
        matchups: List[Matchup]
        for week, matchups in matchups_by_week.items():
            self.league.teams_by_week[str(week)] = {}
            self.league.matchups_by_week[str(week)] = []
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
                    self.league.has_waiver_priorities = base_team.waiver_priority > 0
                    if self.league.is_faab:
                        base_team.faab = team.faab_balance if team.faab_balance else 0
                    base_team.url = team.url

                    team_standings_info = Team({})
                    for ranked_team in league_info.standings.teams:
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
                    week_median = median_score_by_week.get(str(week))

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
                    self.league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # no winner/loser if matchup is tied
                    if not base_matchup.tied:
                        if team.team_key == matchup.winner_team_key:
                            base_matchup.winner = base_team
                        else:
                            base_matchup.loser = base_team

                # add matchup to league matchups by week
                self.league.matchups_by_week[str(week)].append(base_matchup)

        logger.debug("Getting Yahoo rosters by week data.")
        # YAHOO API QUERY: run yahoo queries to retrieve team rosters by week for the season up to the current week
        rosters_by_week = {}
        for wk in range(self.start_week, self.league.week_for_report + 1):
            rosters_by_week[str(wk)] = {
                str(team.team_id):
                    self.yahoo_data.retrieve(
                        f"{team.team_id}-{str(team.name.decode('utf-8')).replace(' ', '_')}-roster",
                        self.yahoo_query.get_team_roster_player_info_by_week,
                        params={"team_id": str(team.team_id), "chosen_week": str(wk)},
                        new_data_dir=(
                                self.league.data_dir / str(
                            self.league.season) / self.league.league_id / f"week_{str(wk)}"
                                / "rosters"
                        )
                    ) for team in league_info.standings.teams
            }

        for week, rosters in rosters_by_week.items():
            self.league.players_by_week[str(week)] = {}
            roster: List[Player]
            for team_id, roster in rosters.items():
                league_team: BaseTeam = self.league.teams_by_week.get(str(week)).get(str(team_id))
                for player in roster:
                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = player.player_key
                    base_player.bye_week = player.bye if player.bye else 0
                    base_player.display_position = (
                        ", ".join([self.get_mapped_position(pos.strip()) for pos in player.display_position.split(",")])
                        if "," in player.display_position
                        else self.get_mapped_position(player.display_position)
                    )
                    base_player.nfl_team_id = player.editorial_team_key
                    base_player.nfl_team_abbr = player.editorial_team_abbr
                    base_player.nfl_team_name = player.editorial_team_full_name
                    base_player.first_name = player.first_name
                    base_player.last_name = player.last_name
                    base_player.full_name = player.full_name
                    if base_player.display_position != "D/ST":
                        base_player.headshot_url = f"https:{player.headshot_url.split(':')[-1]}"
                    else:
                        # use ESPN D/ST team logo (higher resolution)
                        base_player.headshot_url = (
                            f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{base_player.nfl_team_abbr}.png"
                        )
                        # base_player.headshot_url = player.headshot_url
                    base_player.owner_team_id = player.ownership.owner_team_key
                    base_player.owner_team_name = player.ownership.owner_team_name
                    base_player.percent_owned = player.percent_owned_value if player.percent_owned_value else 0
                    base_player.points = player.player_points_value if player.player_points_value else 0
                    base_player.position_type = player.position_type
                    base_player.primary_position = self.get_mapped_position(player.primary_position)
                    base_player.selected_position = self.get_mapped_position(player.selected_position_value)
                    base_player.selected_position_is_flex = bool(player.selected_position.is_flex)

                    base_player.status = player.status

                    eligible_positions = player.eligible_positions
                    for position in eligible_positions:

                        base_position = self.get_mapped_position(position)
                        base_player.eligible_positions.add(base_position)
                        for flex_position, positions in self.league.get_flex_positions_dict().items():
                            if base_position in positions:
                                base_player.eligible_positions.add(flex_position)

                    for stat in player.stats:
                        base_stat = BaseStat()

                        base_stat.stat_id = stat.stat_id
                        base_stat.name = stat.name
                        base_stat.value = stat.value

                        base_player.stats.append(base_stat)

                    # add player to team roster
                    league_team.roster.append(base_player)

                    # add player to league players by week
                    self.league.players_by_week[str(week)][base_player.player_id] = base_player

        self.league.current_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: x.current_record.rank
        )

        self.league.current_median_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: (
                x.current_median_record.get_wins(),
                -x.current_median_record.get_losses(),
                x.current_median_record.get_ties(),
                x.current_median_record.get_points_for()
            ),
            reverse=True
        )

        return self.league
