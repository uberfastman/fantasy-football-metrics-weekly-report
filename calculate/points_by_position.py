from calculate.coaching_efficiency import CoachingEfficiency


class PointsByPosition(object):
    def __init__(self, roster_settings, chosen_week):

        self.chosen_week = chosen_week
        self.roster_slots = roster_settings.get("slots")
        self.flex_positions = {
            "FLEX": roster_settings["flex_positions"],
            "D": ["D", "DB", "DL", "LB", "DT", "DE", "S", "CB"]
        }
        self.coaching_efficiency_dq_dict = {}

    @staticmethod
    def get_starting_players(players):
        return [p for p in players if p["selected_position"] != "BN"]

    @staticmethod
    def get_points_for_position(players, position):
        total_points_by_position = 0
        for player in players:
            player_positions = player["eligible_positions"]
            if not isinstance(player_positions, list):
                player_positions = [player_positions]
            if position in player_positions and player["selected_position"] != "BN":
                total_points_by_position += float(player["fantasy_points"])

        return total_points_by_position

    @staticmethod
    def calculate_points_by_position_season_averages(season_average_points_by_position_dict, report_info_dict):

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

        report_info_dict["season_average_points_by_position"] = season_average_points_by_position_dict

    def execute_points_by_position(self, team_info):

        players = team_info["players"]

        player_points_by_position = []
        starting_players = self.get_starting_players(players)
        for slot in list(self.roster_slots.keys()):
            if slot != "BN" and slot != "FLEX":
                player_points_by_position.append([slot, self.get_points_for_position(starting_players, slot)])

        player_points_by_position = sorted(player_points_by_position, key=lambda x: x[0])
        return player_points_by_position

    def get_weekly_points_by_position(self, dq_ce_bool, config, week, roster, active_slots, team_results_dict):

        coaching_efficiency = CoachingEfficiency(roster)
        weekly_points_by_position_data = []

        for team_name in team_results_dict:
            team_info = team_results_dict[team_name]
            team_info["coaching_efficiency"] = coaching_efficiency.execute_coaching_efficiency(
                team_name, team_info, int(week), active_slots, disqualification_eligible=dq_ce_bool)
            for slot in list(roster["slots"].keys()):
                if roster["slots"].get(slot) == 0:
                    del roster["slots"][slot]
            player_points_by_position = self.execute_points_by_position(team_info)
            weekly_points_by_position_data.append([team_name, player_points_by_position])

        self.coaching_efficiency_dq_dict = coaching_efficiency.coaching_efficiency_dq_dict

        # Option to disqualify chosen team(s) for current week of coaching efficiency
        if week == self.chosen_week:
            disqualified_teams = config.get("Fantasy_Football_Report_Settings",
                                            "coaching_efficiency_disqualified_teams")
            if disqualified_teams:
                for team in disqualified_teams.split(","):
                    print("{} has been manually disqualified from coaching efficiency eligibility!".format(team))
                    team_results_dict.get(team)["coaching_efficiency"] = 0.0

        return weekly_points_by_position_data
