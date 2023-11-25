__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import copy
from typing import Dict, List, Any

from dao.base import BaseLeague, BaseTeam, BasePlayer
from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class PointsByPosition(object):
    def __init__(self, league: BaseLeague, week_for_report: int):
        logger.debug("Initializing points by position.")

        self.week_for_report: int = week_for_report
        self.roster_slot_counts: Dict[str, int] = {k: v for k, v in league.roster_position_counts.items() if v != 0}
        self.bench_positions: List[str] = league.bench_positions
        self.flex_positions_dict: Dict[str, List[str]] = league.get_flex_positions_dict()
        self.flex_types: List[str] = list(self.flex_positions_dict.keys())

    @staticmethod
    def calculate_points_by_position_season_averages(
            season_average_points_by_position_dict: Dict[str, List[List[float]]]) -> Dict[str, List[List[float]]]:
        logger.debug("Calculating points by position season averages.")

        for team in season_average_points_by_position_dict:
            points_by_position = season_average_points_by_position_dict.get(team)
            season_average_points_by_position = {}
            for week in points_by_position:
                for position in week:
                    position_points = season_average_points_by_position.get(position[0])
                    if position_points:
                        season_average_points_by_position[position[0]] = position_points + position[1]
                    else:
                        season_average_points_by_position[position[0]] = position[1]
            season_average_points_by_position_list = []
            for position in list(season_average_points_by_position.keys()):
                season_average_points_by_position_list.append(
                    [position, season_average_points_by_position.get(position) / len(points_by_position)])
            season_average_points_by_position_list = sorted(season_average_points_by_position_list, key=lambda x: x[0])
            season_average_points_by_position_dict[team] = season_average_points_by_position_list

        return season_average_points_by_position_dict

    def _get_points_for_position(self, players: List[BasePlayer], position: str) -> float:
        total_points_by_position = 0
        player: BasePlayer
        for player in players:
            if ((position == player.primary_position
                 or (player.primary_position in self.flex_positions_dict.get(position, [])))
                    and player.selected_position not in self.bench_positions):
                total_points_by_position += float(player.points)

        return total_points_by_position

    def _execute_points_by_position(self, team_name: str, roster: List[BasePlayer]) -> List[List[Any]]:
        logger.debug(f"Calculating points by position for team \"{team_name}\".")

        player_points_by_position = []
        starting_players = [p for p in roster if p.selected_position not in self.bench_positions]
        for slot in list(self.roster_slot_counts.keys()):
            if slot not in self.bench_positions and slot not in self.flex_types:
                player_points_by_position.append([slot, self._get_points_for_position(starting_players, slot)])

        player_points_by_position = sorted(player_points_by_position, key=lambda x: x[0])
        return player_points_by_position

    def get_weekly_points_by_position(self, teams_results: Dict[str, BaseTeam]) -> List[List[Any]]:
        logger.debug("Retrieving weekly points by position.")

        team_roster_slot_counts = copy.deepcopy(self.roster_slot_counts)
        team_roster_slots = list(team_roster_slot_counts.keys())

        weekly_points_by_position_data = []
        team_result: BaseTeam
        for team_result in teams_results.values():
            for slot in list(team_roster_slot_counts.keys()):
                if slot in self.flex_types:
                    if not set(self.flex_positions_dict.get(slot)).intersection(set(team_roster_slots)):
                        self.flex_types.remove(slot)
                    else:
                        for flex_slot in self.flex_positions_dict.get(slot):
                            if flex_slot not in team_roster_slot_counts:
                                self.roster_slot_counts[flex_slot] = 1

            player_points_by_position = self._execute_points_by_position(team_result.name, team_result.roster)
            weekly_points_by_position_data.append([team_result.team_id, player_points_by_position])

        return weekly_points_by_position_data
