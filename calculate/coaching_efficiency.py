__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

from math import comb, ceil, pow, sqrt

import sys
from typing import List, Dict
from collections import OrderedDict
from collections import defaultdict, Counter
from itertools import groupby
from pprint import pprint

from dao.base import BasePlayer
from report.logger import get_logger

logger = get_logger(__name__, propagate=False)


class CoachingEfficiency(object):

    def __init__(self, config, league):
        logger.debug("Initializing coaching efficiency.")

        self.config = config

        self.inactive_statuses = [
            str(status) for status in self.config.get("Configuration", "prohibited_statuses").split(",")]

        self.league = league
        self.roster_slot_counts = self.league.roster_position_counts
        self.roster_active_slots = self.league.active_positions
        self.roster_bench_slots = self.league.bench_positions
        self.flex_positions_dict = self.league.get_flex_positions_dict()
        self.standard_coaching_efficiency_dqs = {}

    def _get_eligible_positions(self, player):
        eligible = []
        for position in self.roster_slot_counts:
            eligible_positions = player.eligible_positions

            if position in self.roster_bench_slots:
                # do not tally eligible player for bench positions
                pass
            elif position in eligible_positions:
                eligible.append(position)

        return eligible

    def _get_ordered_flex_positions_dict(self) -> OrderedDict:
        ordered_flex_positions_dict = OrderedDict()
        for k, v in sorted(self.flex_positions_dict.items(), key=lambda item: len(item[1])):
            if len(v) > 0:
                ordered_flex_positions_dict[k] = v
        return ordered_flex_positions_dict

    @staticmethod
    def _get_optimal_players(eligible_players, position, position_count):
        player_list = eligible_players[position]
        return sorted(player_list, key=lambda x: x.points, reverse=True)[:position_count]

    def _get_optimal_flex(self, eligible_flex_players, optimal_position_lineup):

        optimal_flex_players = []
        allocated_flex_players = set()

        for flex_position, base_positions in self._get_ordered_flex_positions_dict().items():
            candidates = {player for player in eligible_flex_players[flex_position]}

            # subtract already allocated players from candidates
            available_flex_players = candidates - set(optimal_position_lineup) - allocated_flex_players

            num_slots = self.roster_slot_counts[flex_position]

            # convert back to list, sort, take as many as there are slots available
            optimal_flex_position_players = sorted(
                list(available_flex_players), key=lambda x: x.points, reverse=True)[:num_slots]

            for player in optimal_flex_position_players:
                allocated_flex_players.add(player)
                optimal_flex_players.append(player)

        return list(set(optimal_flex_players))

    def _is_player_eligible(self, player, week, inactives):
        return player.status in self.inactive_statuses or player.bye_week == week or player.full_name in inactives

    def _get_eligible_bench_players(self, team_roster, week, inactive_players):
        bench_players = [p for p in team_roster if p.selected_position == "BN"]  # exclude IR players
        eligible_bench_players = [p for p in bench_players if self._is_player_eligible(p, week, inactive_players)]
        return bench_players, eligible_bench_players

    def _calculate_standard_coaching_efficiency(self, optimal_full_lineup, team_name, team_roster, team_points,
                                                positions_filled_active, week, inactive_players, dq_eligible):
        # calculate optimal score
        optimal_score = sum([x.points for x in optimal_full_lineup])

        # calculate standard coaching efficiency
        try:
            standard_coaching_efficiency = (team_points / optimal_score) * 100
        except ZeroDivisionError:
            standard_coaching_efficiency = 0.0

        # apply standard coaching efficiency eligibility requirements if CE disqualification enabled (dq_ce=True)
        if dq_eligible:
            # bench_players = [
            #     p for p in team_roster if p.selected_position == "BN"
            # ]  # exclude IR players
            # ineligible_efficiency_player_count = len(
            #     [p for p in bench_players if self._is_player_eligible(p, week, inactive_players)])
            bench_players, eligible_bench_players = self._get_eligible_bench_players(
                team_roster, week, inactive_players)

            ineligible_efficiency_player_count = len(eligible_bench_players)

            if Counter(self.roster_active_slots) == Counter(positions_filled_active):
                num_bench_slots = self.roster_slot_counts.get("BN", 0)  # excludes IR players/slots
                num_bench_players = len(bench_players)
                # add empty bench slots to the ineligible efficiency bench player count
                if num_bench_players < num_bench_slots:
                    ineligible_efficiency_player_count += (num_bench_slots - num_bench_players)

                # divide bench slots by 2 and DQ team if number of ineligible players >= the ceiling of that value
                if ineligible_efficiency_player_count < ceil(num_bench_slots / 2.0):  # excludes IR players/slots
                    efficiency_disqualification = False
                else:
                    efficiency_disqualification = True
                    self.standard_coaching_efficiency_dqs[team_name] = ineligible_efficiency_player_count
            else:
                efficiency_disqualification = True
                self.standard_coaching_efficiency_dqs[team_name] = -1

            if efficiency_disqualification:
                standard_coaching_efficiency = "DQ"

        # print("TOTAL ACTUAL:", team_points)
        # print("TOTAL OPTIMAL:", optimal_score)
        # print("TOTAL SCE:", standard_coaching_efficiency)

        return standard_coaching_efficiency, optimal_score

    @staticmethod
    def _weighted_coaching_efficiency_sum_by_position(position, percent_constant=100):

        # ncm = comb(position["n"], position["m"])
        # print("nCm:", ncm)
        # prob = 1 / ncm
        # print("prob:", prob)
        # inverse = 1 - prob
        # print("inverse:", inverse)
        # starts = sum(position["starts"])
        # print("starts:", position["starts"])
        # print("start sum:", starts)
        # scores = sum(sorted(position["scores"], reverse=True)[:position["m"]])
        # print("scores:", sorted(position["scores"], reverse=True))
        # print("scores sum:", scores)
        # pct_opt = starts / scores
        # print("pct opt:", pct_opt)
        # pct_pts = c * pct_opt
        # print("pct pts:", pct_pts)

        # noinspection PyPep8Naming
        nCm_probability = 1 / comb(position["count"], position["slots"])
        # noinspection PyPep8Naming
        nCm_probability_complement = 1 - nCm_probability
        if nCm_probability <= 0.5:
            scaling_exponent = nCm_probability * pow(nCm_probability + 0.5, 2) + nCm_probability
        elif nCm_probability > 0.5:
            scaling_exponent = nCm_probability * sqrt(nCm_probability + 0.5) + nCm_probability
        else:
            scaling_exponent = 1
        # scaling_exponent = (0.5 * nCm_probability) + nCm_probability
        position_actual_score = sum(position["starter_scores"])
        position_optimal_score = sum(sorted(position["scores"], reverse=True)[:position["slots"]])

        weighted_coaching_efficiency_sum_by_position = \
            percent_constant * \
            pow(nCm_probability_complement, scaling_exponent) * \
            ((position_actual_score / position_optimal_score) if position_optimal_score != 0 else 0)

        return weighted_coaching_efficiency_sum_by_position

    def _calculate_weighted_coaching_efficiency(
            self, eligible_flex_players: Dict[str, List[BasePlayer]], team_roster: List[BasePlayer]):

        position_map = {
            pos: {
                "slots": slots,
                "count": 0,
                "starter_scores": [],
                "scores": []
            } for pos, slots in self.roster_slot_counts.items() if pos in self.roster_active_slots
        }

        # pprint(position_map)
        # print()
        #
        # pprint(self.roster_active_slots)
        # print()

        # pprint(self.flex_positions_dict)
        # print()

        # sys.exit()

        for position, group in groupby(
                sorted(team_roster, key=lambda x: x.primary_position), lambda x: x.primary_position):
            # print("POSITION:", position)
            # print("ROSTER SLOT COUNT: {0}".format(self.roster_slot_counts.get(position)))
            # print("-" * 10)
            # print()
            for player in list(group):  # type: BasePlayer
                # print("PLAYER NAME:", player.full_name)
                # print("DISPLAY POS:", player.display_position)
                # print("DISPLAY POS:", player.display_position.split(","))
                # print("PRIMARY POS:", player.primary_position)
                # print("SELECTED POS:", player.selected_position)
                # print("ELIGIBLE POSITIONS:", player.eligible_positions)
                # print("POINTS:", player.points)
                # print("~" * 10)
                # print()

                # update position map with starter scores for all positions
                if player.selected_position in self.roster_active_slots:
                    position_map[player.selected_position]["starter_scores"].append(player.points)

                # update position map with count and scores for all primary positions
                if position not in self._get_ordered_flex_positions_dict().keys():
                    position_map[position]["count"] += 1
                    position_map[position]["scores"].append(player.points)

                for flex_position, base_positions in self._get_ordered_flex_positions_dict().items():
                    # update position map with count and scores for all starting flex positions
                    if player.selected_position == flex_position:
                        position_map[player.selected_position]["count"] += 1
                        position_map[player.selected_position]["scores"].append(player.points)

                    # update position map with count and scores for all flex positions from benched players
                    elif (player.primary_position in base_positions or
                          set(player.display_position.split(",")).intersection(set(base_positions))) and \
                            player in eligible_flex_players[flex_position]:
                        position_map[flex_position]["count"] += 1
                        position_map[flex_position]["scores"].append(player.points)

            # print("-" * 100)
            # print()

        # if team_roster[1].owner_team_name != "papi palpatine":
        #     pprint(position_map)

            # print("X" * 100)
            # print("X" * 100)
            # print("X" * 100)
            #
            # pprint(eligible_flex_players)
            # sys.exit()

        # if team_roster[0].owner_team_name == "Tale of 2 Teams":
            # week 1
            # position_map["QB"]["starter_scores"] = [22.64]
            # position_map["QB"]["starter_scores"] = [10]
            # position_map["DEF"]["starter_scores"] = [7.5]
            # position_map["WR"]["starter_scores"] = [10.04, 4.4, 2.9]

            # week 2
            # position_map["QB"]["starter_scores"] = [14.28]
            # position_map["QB"]["starter_scores"] = [5.0]
            # position_map["QB"]["starter_scores"] = [22]
            # position_map["WR"]["starter_scores"] = [15.5, 13.4, 5.5]
            # position_map["WR"]["starter_scores"] = [15.5, 13.4, 2.5]

        weighted_coaching_efficiency = sum(
            self._weighted_coaching_efficiency_sum_by_position(pos) for pos in position_map.values())

        # print("TOTAL WCE:", weighted_coaching_efficiency)
        # print()
        # pprint(position_map)
        # print()
        # print("-" * 200)
        # print()

        return weighted_coaching_efficiency

    def execute_coaching_efficiency(self, team_name, team_roster, team_points, positions_filled_active, week,
                                    inactive_players, dq_eligible=False):
        logger.debug("Calculating coaching efficiency for team \"{0}\".".format(team_name))

        eligible_position_players = defaultdict(list)
        for player in team_roster:
            for position in self._get_eligible_positions(player):
                eligible_position_players[position].append(player)

        optimal_full_lineup = []
        optimal_primary_players = []
        for position, position_count in self.roster_slot_counts.items():
            # handle flex positions later...
            if position not in self.flex_positions_dict.keys():
                optimal_players_for_position = self._get_optimal_players(
                    eligible_position_players, position, position_count)
                optimal_primary_players.extend(optimal_players_for_position)

        optimal_full_lineup.extend(optimal_primary_players)

        eligible_flex_players = defaultdict(list)
        for position, players in eligible_position_players.items():
            eligible_flex_players[position] = [player for player in players if player not in optimal_primary_players]

        # now that we have optimal by position, figure out flex positions
        optimal_flex_players = list(set(self._get_optimal_flex(eligible_flex_players, optimal_primary_players)))

        optimal_full_lineup.extend(optimal_flex_players)

        # print("TEAM:", team_name)

        standard_coaching_efficiency, optimal_score = self._calculate_standard_coaching_efficiency(
            optimal_full_lineup, team_name, team_roster, team_points, positions_filled_active, week, inactive_players,
            dq_eligible)

        weighted_coaching_efficiency = self._calculate_weighted_coaching_efficiency(eligible_flex_players, team_roster)

        # # calculate optimal score
        # optimal_score = sum([x.points for x in optimal_full_lineup])
        #
        # # calculate coaching efficiency
        # try:
        #     coaching_efficiency = (team_points / optimal_score) * 100
        # except ZeroDivisionError:
        #     coaching_efficiency = 0.0
        #
        # # apply coaching efficiency eligibility requirements if CE disqualification enabled (dq_ce=True)
        # if dq_eligible:
        #     bench_players = [
        #         p for p in team_roster if p.selected_position == "BN"
        #     ]  # exclude IR players
        #     ineligible_efficiency_player_count = len(
        #         [p for p in bench_players if self._is_player_eligible(p, week, inactive_players)])
        #
        #     if Counter(self.roster_active_slots) == Counter(positions_filled_active):
        #         num_bench_slots = self.roster_slot_counts.get("BN", 0)  # excludes IR players/slots
        #         num_bench_players = len(bench_players)
        #         # add empty bench slots to the ineligible efficiency bench player count
        #         if num_bench_players < num_bench_slots:
        #             ineligible_efficiency_player_count += (num_bench_slots - num_bench_players)
        #
        #         # divide bench slots by 2 and DQ team if number of ineligible players >= the ceiling of that value
        #         if ineligible_efficiency_player_count < math.ceil(num_bench_slots / 2.0):  # excludes IR players/slots
        #             efficiency_disqualification = False
        #         else:
        #             efficiency_disqualification = True
        #             self.coaching_efficiency_dqs[team_name] = ineligible_efficiency_player_count
        #     else:
        #         efficiency_disqualification = True
        #         self.coaching_efficiency_dqs[team_name] = -1
        #
        #     if efficiency_disqualification:
        #         coaching_efficiency = "DQ"

        return standard_coaching_efficiency, weighted_coaching_efficiency, optimal_score
