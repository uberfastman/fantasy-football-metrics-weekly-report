__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import copy

from dao.base import BaseTeam, BasePlayer
from report.logger import get_logger

logger = get_logger(__name__)


class PointsByPosition(object):
    def __init__(self, roster_settings, week_for_report):

        self.week_for_report = week_for_report
        self.roster_slot_counts = roster_settings.get("position_counts")
        self.flex_positions = {
            "FLEX": roster_settings["positions_flex"],
            "D": ["D", "DB", "DL", "LB", "DT", "DE", "S", "CB"]
        }
        self.bench_positions = roster_settings.get("positions_bench")

    def get_points_for_position(self, players, position):
        total_points_by_position = 0
        for player in players:  # type: BasePlayer
            if position in player.eligible_positions and player.selected_position not in self.bench_positions:
                total_points_by_position += float(player.points)

        return total_points_by_position

    @staticmethod
    def calculate_points_by_position_season_averages(season_average_points_by_position_dict):

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

    def execute_points_by_position(self, roster):

        player_points_by_position = []
        starting_players = [p for p in roster if p.selected_position not in self.bench_positions]
        for slot in list(self.roster_slot_counts.keys()):
            if slot not in self.bench_positions and slot not in ["FLEX", "SUPER_FLEX"]:
                player_points_by_position.append([slot, self.get_points_for_position(starting_players, slot)])

        player_points_by_position = sorted(player_points_by_position, key=lambda x: x[0])
        return player_points_by_position

    def get_weekly_points_by_position(self, teams_results):

        weekly_points_by_position_data = []
        for team_result in teams_results.values():  # type: BaseTeam
            team_roster_slot_counts = copy.deepcopy(self.roster_slot_counts)
            for slot in list(team_roster_slot_counts.keys()):
                if self.roster_slot_counts.get(slot) == 0:
                    del self.roster_slot_counts[slot]

            player_points_by_position = self.execute_points_by_position(team_result.roster)
            weekly_points_by_position_data.append([team_result.team_id, player_points_by_position])

        return weekly_points_by_position_data
