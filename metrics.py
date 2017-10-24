from collections import defaultdict, Counter


class Points(object):

    def __init__(self):
        pass


class CoachingEfficiency(object):
    # prohibited statuses to check team coaching efficiency eligibility
    prohibited_status_list = ["PUP-P", "SUSP", "O", "IR"]

    def __init__(self, roster_settings):
        self.roster_slots = roster_settings["slots"]

        self.flex_positions = {
            "FLEX": roster_settings["flex_positions"],
            "D": ["D", "DB", "DL", "LB", "DT", "DE", "S", "CB"]
        }

    def get_eligible_positions(self, player):
        eligible = []

        for position in self.roster_slots:
            if position in player["eligible_positions"]:
                # special case, because all defensive players get D as an eligible position
                # whereas for offense, there is no special eligible position for FLEX
                if position != "D":
                    eligible.append(position)

                # assign all flex positions the player is eligible for
                for flex_position, base_positions in self.flex_positions.items():
                    if position in base_positions:
                        eligible.append(flex_position)

        return eligible

    def get_optimal_players(self, eligible_players, position):
        player_list = eligible_players[position]

        num_slots = self.roster_slots[position]

        return sorted(player_list, key=lambda x: x["fantasy_points"], reverse=True)[:num_slots]

    def get_optimal_flex(self, eligible_positions, optimal):

        # method to turn player dict into a tuple for use in sets/comparison
        # should just have a class, but w/e
        def create_tuple(player_info):
            return (
                player_info["name"],
                player_info["fantasy_points"]
            )

        for flex_position, base_positions in self.flex_positions.items():
            candidates = set([create_tuple(player) for player in eligible_positions[flex_position]])

            optimal_allocated = set()
            # go through positions that makeup the flex position
            # and add each player from the optimal list to an allocated set
            for base_position in base_positions:
                for player in optimal.get(base_position, []):
                    optimal_allocated.add(create_tuple(player))

            # extract already allocated players from candidates
            available = candidates - optimal_allocated

            num_slots = self.roster_slots[flex_position]

            # convert back to list, sort, take as many as there are slots available
            optimal_flex = sorted(list(available), key=lambda x: x[1], reverse=True)[:num_slots]

            # grab the player dict that matches and return those
            # so that the data types we deal with are all similar
            for player in eligible_positions[flex_position]:
                for optimal_flex_player in optimal_flex:
                    if create_tuple(player) == optimal_flex_player:
                        yield player

    def is_player_eligible(self, player, week):
        return player["status"] in self.prohibited_status_list or player["bye_week"] == week

    def execute_coaching_efficiency(self, team_name, team_info, week, league_roster_active_slots, disqualification_eligible=False):

        players = team_info["players"]

        eligible_positions = defaultdict(list)

        for player in players:
            for position in self.get_eligible_positions(player):
                eligible_positions[position].append(player)

        # debug stuff
        # import json
        # for position, players in eligible_positions.items():
        #     print("{0}: {1}".format(position, [p["name"] for p in players]))

        optimal_players = []
        optimal = {}

        for position in self.roster_slots:
            if position in self.flex_positions.keys():
                # handle flex positions later...
                continue
            optimal_position = self.get_optimal_players(eligible_positions, position)
            optimal_players.append(optimal_position)
            optimal[position] = optimal_position

        # now that we have optimal by position, figure out flex positions
        optimal_flexes = list(self.get_optimal_flex(eligible_positions, optimal))

        optimal_players.append(optimal_flexes)

        optimal_lineup = [item for sublist in optimal_players for item in sublist]

        # calculate optimal score
        optimal_score = sum([x["fantasy_points"] for x in optimal_lineup])

        # print("optimal lineup for " + team_name)
        # for player in optimal_lineup:
        #     print(player)

        # calculate coaching efficiency
        actual_weekly_score = team_info["weekly_score"]

        coaching_efficiency = (actual_weekly_score / optimal_score) * 100

        # apply coaching efficiency eligibility requirements for League of Emperors
        if disqualification_eligible:

            bench_players = [p for p in players if p["selected_position"] == "BN"]
            ineligible_efficiency_player_count = len([p for p in bench_players if self.is_player_eligible(p, week)])
            positions_filled_active = team_info["positions_filled_active"]

            if Counter(league_roster_active_slots) == Counter(positions_filled_active):
                if ineligible_efficiency_player_count <= 4:
                    efficiency_disqualification = False
                else:
                    print("ROSTER INVALID! There are %d inactive players on the bench of %s in week %s!" % (
                        ineligible_efficiency_player_count, team_name, week))
                    efficiency_disqualification = True

            else:
                print(
                    "ROSTER INVALID! There is not a full squad of active players starting on %s in week %s!" % (
                        team_name,
                        week))
                efficiency_disqualification = True

            if efficiency_disqualification:
                coaching_efficiency = 0.0

        return coaching_efficiency


class Breakdown(object):

    def __init__(self):
        pass

    def execute_breakdown(self, teams, matchups):

        result = defaultdict(dict)

        for team_name, team in teams.items():
            record = {
                "W": 0, 
                "L": 0,
                "T": 0
            }

            for team_name2, team2 in teams.items():
                if team["team_id"] == team2["team_id"]:
                    continue
                score1 = team["weekly_score"]
                score2 = team2["weekly_score"]
                if score1 > score2:
                    record["W"] += 1
                elif score1 < score2:
                    record["L"] += 1
                else:
                    record["T"] += 1

            result[team_name]["breakdown"] = record

            # calc luck %
            # TODO: assuming no ties...  how are tiebreakers handled?
            luck = 0.0
            # number of teams excluding current team
            num_teams = float(len(teams.keys())) - 1 

            if record["W"] != 0 and record["L"] != 0:
                matchup_result = matchups[team_name]
                if matchup_result == "W" or matchup_result == "T":
                    luck = (record["L"] + record["T"]) / num_teams
                else:
                    luck = 0 - (record["W"] + record["T"]) / num_teams
                    
            result[team_name]["luck"] = luck

        return result                


class SeasonAverageCalculator(object):

    def __init__(self, team_names, report_info_dict):
        self.team_names = team_names
        self.report_info_dict = report_info_dict

    def get_average(self, data, key, with_percent_bool):

        season_average_list = []
        team_index = 0
        for team in data:
            team_name = self.team_names[team_index]
            season_average_value = "{0:.2f}".format(sum([float(week[1]) for week in team]) / float(len(team)))
            season_average_list.append([team_name, season_average_value])
            team_index += 1
        ordered_average_values = sorted(season_average_list, key=lambda x: float(x[1]), reverse=True)
        for team in ordered_average_values:
            ordered_average_values[ordered_average_values.index(team)] = [ordered_average_values.index(team), team[0], team[1]]

        ordered_season_average_list = []
        for ordered_team in self.report_info_dict.get(key):
            for team in ordered_average_values:
                if ordered_team[1] == team[1]:
                    if with_percent_bool:
                        ordered_team.append(str(team[2]) + "% (" + str(ordered_average_values.index(team) + 1) + ")")
                    else:
                        ordered_team.insert(-1, str(team[2]) + " (" + str(ordered_average_values.index(team) + 1) + ")")
                    ordered_season_average_list.append(ordered_team)
        return ordered_season_average_list


class PointsByPosition(object):

    def __init__(self, roster_settings):

        self.roster_slots = roster_settings.get("slots")
        self.flex_positions = {
            "FLEX": roster_settings["flex_positions"],
            "D": ["D", "DB", "DL", "LB", "DT", "DE", "S", "CB"]
        }

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

        for team in season_average_points_by_position_dict.keys():
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
            for position in season_average_points_by_position.keys():
                season_average_points_by_position_list.append(
                    [position, season_average_points_by_position.get(position) / len(points_by_position)])
            season_average_points_by_position_list = sorted(season_average_points_by_position_list, key=lambda x: x[0])
            season_average_points_by_position_dict[team] = season_average_points_by_position_list

        report_info_dict["season_average_team_points_by_position"] = season_average_points_by_position_dict

    def execute_points_by_position(self, team_info):

        players = team_info["players"]

        player_points_by_position = []
        starting_players = self.get_starting_players(players)
        for slot in self.roster_slots.keys():
            if slot != "BN" and slot != "FLEX":
                player_points_by_position.append([slot, self.get_points_for_position(starting_players, slot)])

        player_points_by_position = sorted(player_points_by_position, key=lambda x: x[0])
        return player_points_by_position
