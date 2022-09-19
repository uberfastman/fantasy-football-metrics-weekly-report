__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from collections import defaultdict, Counter

import math

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
        self.coaching_efficiency_dqs = {}

    def get_eligible_positions(self, player):
        eligible = []
        for position in self.roster_slot_counts:
            eligible_positions = player.eligible_positions

            if position in self.roster_bench_slots:
                # do not tally eligible player for bench positions
                pass
            elif position in eligible_positions:
                eligible.append(position)

        return eligible

    @staticmethod
    def get_optimal_players(eligible_players, position, position_count):
        player_list = eligible_players[position]
        return sorted(player_list, key=lambda x: x.points, reverse=True)[:position_count]

    def get_optimal_flex(self, eligible_flex_players, optimal_position_lineup):

        optimal_flex_players = []
        allocated_flex_players = set()

        ordered_flex_positions_dict = {
            k: v for k, v in sorted(self.flex_positions_dict.items(), key=lambda item: len(item[1]))
        }

        for flex_position, base_positions in ordered_flex_positions_dict.items():
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

    def is_player_ineligible(self, player: BasePlayer, week, inactives):
        if player.points != 0.0:
            return False
        else:
            return player.status in self.inactive_statuses or player.bye_week == week or player.full_name in inactives

    def execute_coaching_efficiency(self, team_name, team_roster, team_points, positions_filled_active, week,
                                    inactive_players, dq_eligible=False):
        logger.debug("Calculating coaching efficiency for team \"{0}\".".format(team_name))

        eligible_position_players = defaultdict(list)
        for player in team_roster:
            for position in self.get_eligible_positions(player):
                eligible_position_players[position].append(player)

        optimal_full_lineup = []
        optimal_primary_lineup = []
        for position, position_count in self.roster_slot_counts.items():
            # handle flex positions later...
            if position not in self.flex_positions_dict.keys():
                optimal_players_for_position = self.get_optimal_players(
                    eligible_position_players, position, position_count)
                optimal_primary_lineup.extend(optimal_players_for_position)

        optimal_full_lineup.extend(optimal_primary_lineup)

        eligible_flex_players = defaultdict(list)
        for position, players in eligible_position_players.items():
            eligible_flex_players[position] = [player for player in players if player not in optimal_primary_lineup]

        # now that we have optimal by position, figure out flex positions
        optimal_flex_players = list(set(self.get_optimal_flex(eligible_flex_players, optimal_primary_lineup)))

        optimal_full_lineup.extend(optimal_flex_players)

        # calculate optimal score
        optimal_score = sum([x.points for x in optimal_full_lineup])

        # calculate coaching efficiency
        try:
            coaching_efficiency = (team_points / optimal_score) * 100
        except ZeroDivisionError:
            coaching_efficiency = 0.0

        # apply coaching efficiency eligibility requirements if CE disqualification enabled (dq_ce=True)
        if dq_eligible:
            bench_players = [
                p for p in team_roster if p.selected_position == "BN"
            ]  # exclude IR players
            ineligible_efficiency_player_count = len(
                [p for p in bench_players if self.is_player_ineligible(p, week, inactive_players)])

            if Counter(self.roster_active_slots) == Counter(positions_filled_active):
                num_bench_slots = self.roster_slot_counts.get("BN", 0)  # excludes IR players/slots
                num_bench_players = len(bench_players)
                # add empty bench slots to the ineligible efficiency bench player count
                if num_bench_players < num_bench_slots:
                    ineligible_efficiency_player_count += (num_bench_slots - num_bench_players)

                # divide bench slots by 2 and DQ team if number of ineligible players >= the ceiling of that value
                if ineligible_efficiency_player_count < math.ceil(num_bench_slots / 2.0):  # excludes IR players/slots
                    efficiency_disqualification = False
                else:
                    efficiency_disqualification = True
                    self.coaching_efficiency_dqs[team_name] = ineligible_efficiency_player_count
            else:
                efficiency_disqualification = True
                self.coaching_efficiency_dqs[team_name] = -1

            if efficiency_disqualification:
                coaching_efficiency = "DQ"

        return coaching_efficiency, optimal_score
