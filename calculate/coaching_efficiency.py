__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import math
from collections import Counter
from collections import defaultdict
from typing import List, Dict, Set, Union

from dao.base import BasePlayer, BaseLeague
from utilities.constants import prohibited_statuses
from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class RosterSlot(object):

    def __init__(self, position: str, max_allowed: int, assigned_count: int = 0):
        self.position: str = position
        self.max_allowed: int = max_allowed
        self.assigned_count: int = assigned_count
        self.assigned_players: List[BasePlayer] = []

    def __repr__(self):
        return (
            f"RosterSlot("
            f"position={self.position}, "
            f"max_allowed={self.max_allowed}, "
            f"assigned_count={self.assigned_count}, "
            f"assigned_players={[(p.full_name, p.points, p.eligible_positions) for p in self.assigned_players]}"
            f")"
        )

    def add_player(self, player: BasePlayer) -> Union[str, None]:
        if (self.assigned_count + 1) <= self.max_allowed:
            self.assigned_count += 1
            self.assigned_players.append(player)
            self.assigned_players.sort(key=lambda p: p.points, reverse=True)
            return self.position
        else:
            return None

    def remove_player(self, player_ndx: int = 0) -> BasePlayer:
        self.assigned_count -= 1
        return self.assigned_players.pop(player_ndx)

    def is_full(self):
        return self.assigned_count == self.max_allowed


class CoachingEfficiency(object):

    def __init__(self, league):
        logger.debug("Initializing coaching efficiency.")

        self.inactive_statuses: List[str] = [
            status for status in prohibited_statuses
        ]

        self.league: BaseLeague = league
        self.roster_slot_counts: Dict[str, int] = self.league.roster_position_counts
        self.roster_active_slots: List[str] = self.league.roster_active_slots
        self.roster_bench_slots: List[str] = self.league.bench_positions
        self.flex_positions_dict: Dict[str, List[str]] = self.league.get_flex_positions_dict()
        self.roster_primary_slots: Set[str] = set(self.roster_active_slots).difference(self.flex_positions_dict.keys())
        self.roster_flex_slots: Set[str] = set(self.roster_active_slots).intersection(self.flex_positions_dict.keys())
        self.coaching_efficiency_dqs: Dict[str, int] = {}

    def _is_player_ineligible(self, player: BasePlayer, week, inactives):
        if player.points != 0.0:
            return False
        else:
            return player.status in self.inactive_statuses or player.bye_week == week or player.full_name in inactives

    def _get_player_open_positions(self, player: BasePlayer, optimal_lineup: Dict[str, RosterSlot]):

        eligible_positions = list(player.eligible_positions.intersection(set(self.roster_active_slots)))
        optimal_lineup_open_positions = {
            pos: roster_slot for pos, roster_slot in optimal_lineup.items() if pos in eligible_positions
        }

        # retrieve list of player eligible positions that still have open slots
        open_positions = [
            pos for pos, roster_slot in optimal_lineup_open_positions.items() if not roster_slot.is_full()
        ]

        return open_positions

        # TODO: support reassigning players more than one position away
        # assigned_eligible_positions = {
        #     k for k, v in optimal_lineup_eligible_positions.items() if (v.get("slots") - v.get("count")) == 0
        # }
        #
        # if open_positions:
        #     return open_positions
        # else:
        #     if assigned_eligible_positions.issubset(assigned_positions):
        #         return []
        #     else:
        #         assigned_positions.update(assigned_eligible_positions)
        #
        #         next_player_tier_unassigned_positions = []
        #         for pos in assigned_eligible_positions:
        #             for p in optimal_lineup.get(pos).get("players"):
        #                 next_player_tier_unassigned_positions += self._get_player_open_positions(
        #                     p, optimal_lineup, pos, assigned_positions
        #                 )
        #         return next_player_tier_unassigned_positions

    @staticmethod
    def _create_open_slot_if_possible(unassigned_player: BasePlayer,
                                      players_with_open_slots: Dict[str, List[Dict[str, Union[BasePlayer, List[str]]]]],
                                      optimal_lineup: Dict[str, RosterSlot]):

        for pos, assigned_players_info in players_with_open_slots.items():
            for assigned_player in assigned_players_info:
                open_positions = assigned_player["open_positions"]
                if len(open_positions) > 0:
                    player: BasePlayer
                    for player_ndx, player in enumerate(optimal_lineup.get(pos).assigned_players):
                        # check if any players in position match the potentially replaceable player
                        if assigned_player["assigned_player"].player_id == player.player_id:
                            # remove the replaceable player from their current optimal lineup position
                            movable_player = optimal_lineup.get(pos).remove_player(player_ndx)
                            # replace the replaceable player with the unassigned player
                            optimal_lineup.get(pos).add_player(unassigned_player)
                            # add the removed replaceable player to a different open optimal lineup position
                            optimal_lineup.get(open_positions[0]).add_player(movable_player)

                            return pos
        return None

    def _assign_player_to_optimal_slot(self, player: BasePlayer, optimal_lineup: Dict[str, RosterSlot]):

        # get player eligible positions based on league roster
        eligible_positions = list(player.eligible_positions.intersection(set(self.roster_active_slots)))

        # separate primary positions from flex positions in order to fill primary positions first
        eligible_primary_positions = list(
            player.eligible_positions.intersection(eligible_positions).intersection(self.roster_primary_slots)
        )
        eligible_flex_positions = list(
            player.eligible_positions.intersection(eligible_positions).intersection(self.roster_flex_slots)
        )

        assigned_pos = None
        point_diffs: Dict[str, float] = {}
        players_with_eligible_open_slots: Dict[str, List[Dict[str, Union[BasePlayer, List[str]]]]] = defaultdict(list)
        for eligible_pos in eligible_primary_positions + eligible_flex_positions:

            if not optimal_lineup.get(eligible_pos).is_full():
                # assign player to optimal lineup if eligible position has open slot
                assigned_pos = optimal_lineup.get(eligible_pos).add_player(player)
                break
            else:
                # collect point differences between player and all players they could potentially replace
                point_diffs[eligible_pos] = player.points - optimal_lineup.get(eligible_pos).assigned_players[-1].points
                for assigned_player in optimal_lineup.get(eligible_pos).assigned_players:
                    players_with_eligible_open_slots[eligible_pos].append(
                        {
                            "assigned_player": assigned_player,
                            "open_positions": self._get_player_open_positions(assigned_player, optimal_lineup),
                        }
                    )

        if assigned_pos:
            return assigned_pos
        else:
            # if no open positions get the highest point difference between player and potentially replaceable players
            try:
                max_point_diff = max(point_diffs.values())
            except ValueError:
                # handle when a team roster contains a player without any eligible league roster positions
                return None
            if max_point_diff <= 0:
                # if no positive point difference check if any potentially replaceable players
                return self._create_open_slot_if_possible(player, players_with_eligible_open_slots, optimal_lineup)

            # collect all positions that share the max point difference with the player
            max_point_diff_positions = [
                pos for pos, point_diff in point_diffs.items() if point_diff == max_point_diff
            ]
            if len(max_point_diff_positions) == 1:
                max_point_diff_position = max_point_diff_positions[0]
            else:
                # favor selection of primary position over flex position max point different position
                max_point_diff_primary_positions = list(
                    set(max_point_diff_positions).intersection(eligible_primary_positions)
                )
                if len(max_point_diff_primary_positions) > 0:
                    max_point_diff_position = max_point_diff_primary_positions[0]
                else:
                    max_point_diff_position = max_point_diff_positions[0]

            # remove replaceable player from their slot and replace them with eligible player
            replaced_player = optimal_lineup.get(max_point_diff_position).remove_player()
            optimal_lineup.get(max_point_diff_position).add_player(player)

        # assign replaced player to new optimal lineup position
        return self._assign_player_to_optimal_slot(replaced_player, optimal_lineup)

    def execute_coaching_efficiency(self, team_name, team_roster, team_points, positions_filled_active, week,
                                    inactive_players, dq_eligible=False):
        logger.debug(f"Calculating week {week} coaching efficiency for team \"{team_name}\".")

        # create empty team optimal lineup
        optimal_lineup: Dict[str, RosterSlot] = {}
        for pos, slots in self.roster_slot_counts.items():
            if pos not in self.roster_bench_slots and slots > 0:
                # pos_info = {"slots": slots, "count": 0, "players": []}
                # optimal_lineup[pos] = pos_info
                optimal_lineup[pos] = RosterSlot(pos, max_allowed=slots)

        # sort roster by points from highest to lowest
        team_roster_by_points: List[BasePlayer] = sorted(
            [p for p in team_roster if p.selected_position != "IR"],
            key=lambda p: p.points,
            reverse=True
        )

        # assign each player from highest-scoring to lowest to maximize points
        for player in team_roster_by_points:
            self._assign_player_to_optimal_slot(player, optimal_lineup)

        # calculate optimal score
        optimal_score = round(
            sum([p.points for roster_slot in optimal_lineup.values() for p in roster_slot.assigned_players]), 2
        )

        # calculate coaching efficiency
        try:
            coaching_efficiency = (team_points / optimal_score) * 100
        except ZeroDivisionError:
            coaching_efficiency = 0.0

        logger.debug(
            f"\n"
            f"               TEAM: {team_name}\n"
            f"             POINTS: {team_points}\n"
            f"     OPTIMAL POINTS: {optimal_score}\n"
            f"COACHING EFFICIENCY: {coaching_efficiency}\n"
        )
        for pos, roster_slot in optimal_lineup.items():
            logger.debug(
                f"\n"
                f"Position: {pos}\n"
                f"  {roster_slot.assigned_count}/{roster_slot.max_allowed}: "
                f"{[(p.full_name, p.points, p.eligible_positions) for p in roster_slot.assigned_players]}\n"
                f"-----"
            )

        # apply coaching efficiency eligibility requirements if CE disqualification enabled (dq_ce=True)
        if dq_eligible:
            bench_players = [
                p for p in team_roster if p.selected_position == "BN"
            ]  # exclude IR players
            ineligible_efficiency_player_count = len(
                [p for p in bench_players if self._is_player_ineligible(p, week, inactive_players)])

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
