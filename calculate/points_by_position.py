__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import copy
import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class PointsByPosition(object):
    def __init__(self, roster_settings, week_for_report):

        self.week_for_report = week_for_report
        self.roster_slot_counts = roster_settings.get("position_counts")
        self.flex_positions = {
            "FLEX": roster_settings["positions_flex"],
            "D": ["D", "DB", "DL", "LB", "DT", "DE", "S", "CB"]
        }
        self.bench_positions = roster_settings.get("positions_bench")

    def get_starting_players(self, players):
        return [p for p in players if p.selected_position.position not in self.bench_positions]

    def get_points_for_position(self, players, position):
        total_points_by_position = 0
        for player in players:
            player_positions = player.eligible_positions

            if isinstance(player_positions, dict):
                player_positions = [player_positions.get("position")]
            else:
                player_positions = [player_position.get("position") for player_position in player_positions]

            if position in player_positions and player.selected_position.position not in self.bench_positions:
                total_points_by_position += float(player.player_points.total)

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

    def execute_points_by_position(self, players):

        player_points_by_position = []
        starting_players = self.get_starting_players(players)
        for slot in list(self.roster_slot_counts.keys()):
            if slot not in self.bench_positions and slot != "FLEX":
                player_points_by_position.append([slot, self.get_points_for_position(starting_players, slot)])

        player_points_by_position = sorted(player_points_by_position, key=lambda x: x[0])
        return player_points_by_position

    def get_weekly_points_by_position(self, teams_results):

        weekly_points_by_position_data = []
        for team_result in teams_results.values():
            team_roster_slot_counts = copy.deepcopy(self.roster_slot_counts)
            for slot in list(team_roster_slot_counts.keys()):
                if self.roster_slot_counts.get(slot) == 0:
                    del self.roster_slot_counts[slot]

            player_points_by_position = self.execute_points_by_position(team_result.players)
            weekly_points_by_position_data.append([team_result.team_key, player_points_by_position])

        return weekly_points_by_position_data
