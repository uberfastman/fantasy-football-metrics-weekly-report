# written by Wren J.R.
# contributors: Kevin N., Joe M.

import math
from collections import defaultdict, Counter


class CoachingEfficiency(object):
    # prohibited statuses to check team coaching efficiency eligibility
    prohibited_status_list = ["PUP-P", "SUSP", "O", "IR", "INACTIVE"]

    def __init__(self, roster_settings):
        self.roster_slots = roster_settings["slots"]

        self.flex_positions = {
            "FLEX": roster_settings["flex_positions"]
        }

        flex_def_positions = ["DB", "DL", "LB", "DT", "DE", "S", "CB"]

        self.has_flex_def = False
        for rs in self.roster_slots:
            if rs in flex_def_positions:
                self.has_flex_def = True
                break

        if self.has_flex_def:
            self.flex_positions['D'] = flex_def_positions

        self.coaching_efficiency_dq_dict = {}

    def get_eligible_positions(self, player):
        eligible = []

        for position in self.roster_slots:
            eligible_positions = player["eligible_positions"]
            if not isinstance(eligible_positions, list):
                eligible_positions = [eligible_positions]
            if position in eligible_positions:
                # special case, because all defensive players get D as an eligible position
                # whereas for offense, there is no special eligible position for FLEX
                if not self.has_flex_def or position != 'D':
                    eligible.append(position)

                # assign all flex positions the player is eligible for
                for flex_position, base_positions in list(self.flex_positions.items()):
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

        for flex_position, base_positions in list(self.flex_positions.items()):
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

    def execute_coaching_efficiency(self, team_name, team_info, week, league_roster_active_slots,
                                    disqualification_eligible=False):

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
            if position in list(self.flex_positions.keys()):
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

        # calculate coaching efficiency
        actual_weekly_score = team_info["score"]

        coaching_efficiency = (actual_weekly_score / optimal_score) * 100

        # apply coaching efficiency eligibility requirements if coaching efficiency disqualification bool (dq_ce_bool)
        # is set to True
        if disqualification_eligible:

            bench_players = [p for p in players if p["selected_position"] == "BN"]
            ineligible_efficiency_player_count = len([p for p in bench_players if self.is_player_eligible(p, week)])
            positions_filled_active = team_info["positions_filled_active"]

            if Counter(league_roster_active_slots) == Counter(positions_filled_active):
                # divide bench slots by 2 and DQ team if number of ineligible players exceeds the ceiling of that value
                if ineligible_efficiency_player_count <= math.ceil(self.roster_slots.get("BN") / 2.0):
                    efficiency_disqualification = False
                else:
                    efficiency_disqualification = True
                    self.coaching_efficiency_dq_dict[team_name] = ineligible_efficiency_player_count

            else:
                efficiency_disqualification = True
                self.coaching_efficiency_dq_dict[team_name] = -1

            if efficiency_disqualification:
                coaching_efficiency = 0.0

        return coaching_efficiency
