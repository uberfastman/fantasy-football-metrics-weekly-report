__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import copy

from dao.base import BaseLeague, BaseTeam, BasePlayer
from report.logger import get_logger

logger = get_logger(__name__, propagate=False)


class PointsByPosition(object):
    def __init__(self, league: BaseLeague, week_for_report):
        logger.debug("Initializing points by position.")

        self.week_for_report = week_for_report
        self.roster_slot_counts = league.roster_position_counts
        self.bench_positions = league.bench_positions
        self.flex_positions_dict = league.get_flex_positions_dict()
        self.flex_types = list(self.flex_positions_dict.keys())
        # self.flex_types.remove("FLEX_IDP")  # comment/uncomment line to remove/add FLEX_IDP to team points by position

    @staticmethod
    def calculate_points_by_position_season_averages(season_average_points_by_position_dict):
        logger.debug("Calculating points by position season averages.")

        for team in list(season_average_points_by_position_dict.keys()):
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

    def _get_points_for_position(self, players, position):
        total_points_by_position = 0
        player: BasePlayer
        for player in players:
            if position == player.primary_position and player.selected_position not in self.bench_positions:
                total_points_by_position += float(player.points)

        return total_points_by_position

    def _execute_points_by_position(self, team_name, roster):
        logger.debug(f"Calculating points by position for team \"{team_name}\".")

        player_points_by_position = []
        starting_players = [p for p in roster if p.selected_position not in self.bench_positions]
        for slot in list(self.roster_slot_counts.keys()):
            if slot not in self.bench_positions and slot not in self.flex_types:
                player_points_by_position.append([slot, self._get_points_for_position(starting_players, slot)])

        player_points_by_position = sorted(player_points_by_position, key=lambda x: x[0])
        return player_points_by_position

    def get_weekly_points_by_position(self, teams_results):
        logger.debug("Retrieving weekly points by position.")

        weekly_points_by_position_data = []
        team_result: BaseTeam
        for team_result in teams_results.values():
            team_roster_slot_counts = copy.deepcopy(self.roster_slot_counts)
            for slot in list(team_roster_slot_counts.keys()):
                if slot in self.flex_types and self.roster_slot_counts.get(slot) != 0:
                    active_roster_slots = list({k: v for k, v in self.roster_slot_counts.items() if v != 0}.keys())

                    if not set(self.flex_positions_dict.get(slot)).intersection(set(active_roster_slots)):
                        self.flex_types.remove(slot)
                    else:
                        for flex_slot in self.flex_positions_dict.get(slot):
                            if flex_slot not in team_roster_slot_counts:
                                self.roster_slot_counts[flex_slot] = 1

                if self.roster_slot_counts.get(slot) == 0:
                    del self.roster_slot_counts[slot]

            player_points_by_position = self._execute_points_by_position(team_result.name, team_result.roster)
            weekly_points_by_position_data.append([team_result.team_id, player_points_by_position])

        return weekly_points_by_position_data
