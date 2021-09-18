__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"
# code snippets: https://github.com/cdtdev/ff_monte_carlo (originally written by https://github.com/cdtdev)

import datetime
import itertools
import json
import os
import random
import traceback
from copy import deepcopy
from utils.app_config_parser import AppConfigParser

import numpy as np

from report.logger import get_logger

logger = get_logger(__name__, propagate=False)


class PlayoffProbabilities(object):

    def __init__(self, config: AppConfigParser, simulations, num_weeks, num_playoff_slots, data_dir, num_divisions=0,
                 save_data=False, recalculate=False, dev_offline=False):
        logger.debug("Initializing playoff probabilities.")

        self.config = config
        self.simulations = int(simulations) if simulations is not None else self.config.getint(
            "Settings", "num_playoff_simulations", fallback=100000)
        self.num_weeks = int(num_weeks)
        self.num_playoff_slots = int(num_playoff_slots)
        self.data_dir = data_dir
        self.num_divisions = num_divisions
        self.save_data = save_data
        self.recalculate = recalculate
        self.dev_offline = dev_offline
        self.playoff_probs_data = {}

    def calculate(self, week, week_for_report, standings, remaining_matchups):
        logger.debug("Calculating playoff probabilities.")

        # with open("playoff_prob_standings.json", "w") as pps:
        #     json.dump(standings, pps, indent=2)
        #
        # with open("playoff_prob_remaining_matchups.json", "w") as pprm:
        #     json.dump(remaining_matchups, pprm, indent=2)

        teams_for_playoff_probs = {}
        for team in standings:
            # noinspection PyTypeChecker,PyUnresolvedReferences
            teams_for_playoff_probs[team.team_id] = TeamWithPlayoffProbs(
                team.team_id,
                team.name,
                team.manager_str,
                int(team.record.get_wins()),
                int(team.record.get_losses()),
                int(team.record.get_ties()),
                float(team.record.get_points_for()),
                self.num_playoff_slots,
                self.simulations,
                team.division,
                int(team.record.get_division_wins()),
                int(team.record.get_division_losses()),
                int(team.record.get_division_ties()),
                float(team.record.get_division_points_for())
            )

        try:
            if int(week) == int(week_for_report):
                if self.recalculate:
                    logger.info("Running %s Monte Carlo playoff simulation%s..." % ("{0:,}".format(
                        self.simulations), ("s" if self.simulations > 1 else "")))

                    begin = datetime.datetime.now()
                    avg_wins = [0.0] * self.num_playoff_slots
                    sim_count = 1
                    while sim_count <= self.simulations:
                        # create random binary results representing the rest of the season matchups and add them to the
                        # existing wins
                        for week, matchups in remaining_matchups.items():
                            for matchup in matchups:
                                team_1 = teams_for_playoff_probs[matchup[0]]
                                team_2 = teams_for_playoff_probs[matchup[1]]
                                result = int(random.getrandbits(1))
                                if result == 1:
                                    team_1.add_win()
                                    team_2.add_loss()
                                    if self.num_divisions > 0:
                                        if team_1.division and team_2.division and team_1.division == team_2.division:
                                            team_1.add_division_win()
                                            team_2.add_division_loss()
                                else:
                                    team_2.add_win()
                                    team_1.add_loss()
                                    if self.num_divisions > 0:
                                        if team_1.division and team_2.division and team_1.division == team_2.division:
                                            team_2.add_division_win()
                                            team_1.add_division_loss()

                        if self.num_divisions > 0:
                            sorted_divisions = self.group_by_division(teams_for_playoff_probs)

                            num_playoff_slots_per_division_without_leader = self.config.getint(
                                "Settings", "num_playoff_slots_per_division", fallback=1) - 1

                            # pick the teams making the playoffs
                            division_winners = []
                            division_qualifiers = []
                            remaining_teams = []
                            for division in sorted_divisions.values():
                                division_winners.append(division[0])

                                div_qual_count = deepcopy(num_playoff_slots_per_division_without_leader)
                                for remaining_team in division[1:]:
                                    if div_qual_count > 0:
                                        division_qualifiers.append(remaining_team)
                                    else:
                                        remaining_teams.append(remaining_team)
                                    div_qual_count -= 1

                            division_winners = sorted(
                                division_winners, key=lambda x: x.get_wins_with_points(), reverse=True)
                            division_qualifiers = sorted(
                                division_qualifiers, key=lambda x: x.get_wins_with_points(), reverse=True)
                            remaining_teams = sorted(
                                remaining_teams, key=lambda x: x.get_wins_with_points(), reverse=True)

                            playoff_count = 1
                            for team in division_winners:
                                teams_for_playoff_probs[division_winners[playoff_count - 1].team_id].add_playoff_tally()
                                avg_wins[playoff_count - 1] += \
                                    round(division_winners[playoff_count - 1].get_wins_with_points(), 0)
                                teams_for_playoff_probs[team.team_id].add_playoff_stats(playoff_count)
                                teams_for_playoff_probs[team.team_id].add_division_leader_tally()
                                playoff_count += 1

                            if (len(division_winners) < self.num_playoff_slots) and (len(division_qualifiers) > 0):
                                if len(division_qualifiers) <= (self.num_playoff_slots - len(division_winners)):
                                    remaining_playoff_count = 1
                                    for division_qualifier_count in range(1, len(division_qualifiers) + 1):
                                        teams_for_playoff_probs[division_qualifiers[
                                            remaining_playoff_count - 1].team_id].add_playoff_tally()
                                        avg_wins[
                                            len(division_winners) + remaining_playoff_count - 1] += \
                                            round(division_qualifiers[
                                                      remaining_playoff_count - 1].get_wins_with_points(), 0)
                                        teams_for_playoff_probs[
                                            division_qualifiers[remaining_playoff_count - 1].team_id].add_playoff_stats(
                                            len(division_winners) + remaining_playoff_count)
                                        teams_for_playoff_probs[
                                            division_qualifiers[
                                                remaining_playoff_count - 1].team_id].add_division_qualifier_tally()
                                        remaining_playoff_count += 1
                                else:
                                    raise ValueError("Specified number of playoff qualifiers per division ({0}) exceeds"
                                                     " available league playoff spots. Please correct the value of "
                                                     "\"num_playoff_slots_per_division\" in \"config.ini\".".format(
                                                        num_playoff_slots_per_division_without_leader + 1))

                            if (len(division_winners) + len(division_qualifiers)) < self.num_playoff_slots:
                                remaining_playoff_count = 1
                                while remaining_playoff_count <= \
                                        (self.num_playoff_slots - len(division_winners) - len(division_qualifiers)):
                                    teams_for_playoff_probs[remaining_teams[
                                        remaining_playoff_count - 1].team_id].add_playoff_tally()
                                    avg_wins[len(division_winners) + len(division_qualifiers) +
                                             remaining_playoff_count - 1] += \
                                        round(remaining_teams[remaining_playoff_count - 1].get_wins_with_points(), 0)
                                    teams_for_playoff_probs[
                                        remaining_teams[remaining_playoff_count - 1].team_id].add_playoff_stats(
                                        len(division_winners) + len(division_qualifiers) + remaining_playoff_count)
                                    remaining_playoff_count += 1

                        else:
                            # sort the teams
                            sorted_teams = sorted(
                                teams_for_playoff_probs.values(), key=lambda x: x.get_wins_with_points(), reverse=True)

                            # pick the teams making the playoffs
                            playoff_count = 1
                            while playoff_count <= self.num_playoff_slots:
                                teams_for_playoff_probs[sorted_teams[playoff_count - 1].team_id].add_playoff_tally()
                                avg_wins[playoff_count - 1] += \
                                    round(sorted_teams[playoff_count - 1].get_wins_with_points(), 0)
                                teams_for_playoff_probs[sorted_teams[playoff_count - 1].team_id].add_playoff_stats(
                                    playoff_count)
                                playoff_count += 1

                        for team in teams_for_playoff_probs.values():  # type: TeamWithPlayoffProbs
                            team.reset_to_base_record()

                        sim_count += 1

                    modified_team_names = {team_id: "" for team_id in teams_for_playoff_probs.keys()}
                    if self.num_divisions > 0:
                        sorted_divisions = self.group_by_division(teams_for_playoff_probs)

                        num_playoff_slots_per_division_without_leader = self.config.getint(
                            "Settings", "num_playoff_slots_per_division", fallback=1) - 1

                        for division in sorted_divisions.values():
                            ranked_division = sorted(
                                division,
                                key=lambda x: (
                                    x.division_leader_tally,
                                    x.division_qualifier_tally
                                ),
                                reverse=True
                            )
                            modified_team_names[ranked_division[0].team_id] = "†"
                            teams_for_playoff_probs[ranked_division[0].team_id].is_predicted_division_leader = True

                            division_qualifier_count = deepcopy(num_playoff_slots_per_division_without_leader)
                            if division_qualifier_count > 0:
                                for division_ndx in range(1, division_qualifier_count + 1):
                                    modified_team_names[ranked_division[division_ndx].team_id] = "‡"
                                    teams_for_playoff_probs[
                                        ranked_division[division_ndx].team_id].is_predicted_division_qualifier = True

                                    division_qualifier_count -= 1

                    for team in teams_for_playoff_probs.values():  # type: TeamWithPlayoffProbs
                        playoff_min_wins = round((avg_wins[self.num_playoff_slots - 1]) / self.simulations, 2)
                        if playoff_min_wins > team.wins:
                            needed_wins = np.rint(playoff_min_wins - team.wins)
                        else:
                            needed_wins = 0

                        self.playoff_probs_data[int(team.team_id)] = [
                            team.name + modified_team_names[team.team_id],
                            team.get_playoff_chance_percentage(),
                            team.get_playoff_stats(),
                            needed_wins,
                            # add value for if team was predicted division winner to pass to the later sort function
                            team.is_predicted_division_leader,
                            # add value for if team was predicted division qualifier to pass to the later sort function
                            team.is_predicted_division_qualifier
                        ]

                    delta = datetime.datetime.now() - begin
                    logger.info("...ran %s playoff simulation%s in %s\n" % ("{0:,}".format(
                        self.simulations), ("s" if self.simulations > 1 else ""), str(delta)))

                    if self.save_data:
                        save_dir = os.path.join(self.data_dir, "week_" + str(week_for_report))
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir)

                        with open(os.path.join(save_dir, "playoff_probs_data.json"), "w") as pp_out:
                            json.dump(self.playoff_probs_data, pp_out, ensure_ascii=False, indent=2)

                else:
                    logger.info("Using saved Monte Carlo playoff simulations for playoff probabilities.")

                    playoff_probs_data_file_path = os.path.join(
                        self.data_dir, "week_" + str(week_for_report), "playoff_probs_data.json")
                    if os.path.exists(playoff_probs_data_file_path):
                        with open(playoff_probs_data_file_path, "r") as pp_in:
                            self.playoff_probs_data = json.load(pp_in)
                    else:
                        raise FileNotFoundError(
                            "FILE {0} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                                playoff_probs_data_file_path))

                return self.playoff_probs_data
            else:
                logger.debug("No predicted playoff standings calculated for week {0}. The Fantasy Football Metrics "
                             "Weekly Report application currently only supports playoff predictions when run for the "
                             "current week.".format(week))
                return None
        except Exception as e:
            logger.error("COULDN'T CALCULATE PLAYOFF PROBS WITH EXCEPTION: {0}\n{1}".format(e, traceback.format_exc()))
            return None

    def group_by_division(self, teams_for_playoff_probs):
        # group teams into divisions
        division_groups = [
            list(group) for key, group in itertools.groupby(
                sorted(teams_for_playoff_probs.values(), key=lambda x: x.division),
                lambda x: str(x.division))
        ]

        # sort the teams
        sorted_divisions = {}
        for division_num in range(1, self.num_divisions + 1):
            sorted_divisions[division_num] = sorted(
                division_groups[division_num - 1],
                key=lambda x: (
                    x.get_wins_with_points(),
                    -x.losses,
                    x.ties,
                    x.get_division_wins_with_points(),
                    -x.division_losses,
                    x.division_ties
                ),
                reverse=True
            )

        return sorted_divisions

    def __str__(self):
        return json.dumps(self.__dict__, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.__dict__, indent=2, ensure_ascii=False)


class TeamWithPlayoffProbs(object):

    def __init__(self, team_id, name, manager, wins, losses, ties, points_for, playoff_slots, simulations,
                 division=None, division_wins=0, division_losses=0, division_ties=0, division_points_for=0):
        self.team_id = team_id
        self.name = name
        self.manager = manager
        self.division = division
        self.base_wins = wins
        self.wins = wins
        self.base_division_wins = division_wins
        self.division_wins = division_wins
        self.base_losses = losses
        self.losses = losses
        self.base_division_losses = division_losses
        self.division_losses = division_losses
        self.ties = ties
        self.division_ties = division_ties
        self.points_for = float(points_for)
        self.division_points_for = float(division_points_for)
        self.division_leader_tally = 0
        self.division_qualifier_tally = 0
        self.is_predicted_division_leader = False
        self.is_predicted_division_qualifier = False
        self.playoff_tally = 0
        self.playoff_stats = [0] * int(playoff_slots)
        self.simulations = int(simulations)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

    def add_win(self):
        self.wins += 1

    def add_division_win(self):
        self.division_wins += 1

    def add_loss(self):
        self.losses += 1

    def add_division_loss(self):
        self.division_losses += 1

    def add_division_leader_tally(self):
        self.division_leader_tally += 1

    def add_division_qualifier_tally(self):
        self.division_qualifier_tally += 1

    def add_playoff_tally(self):
        self.playoff_tally += 1

    def add_playoff_stats(self, place):
        self.playoff_stats[place - 1] += 1

    def get_wins_with_points(self):
        return self.wins + (self.points_for / 1000000)

    def get_division_wins_with_points(self):
        return self.division_wins + (self.division_points_for / 1000000)

    def get_playoff_chance_percentage(self):
        return round((self.playoff_tally / self.simulations) * 100.0, 2)

    def get_playoff_stats(self):
        return [round((stat / self.simulations) * 100.0, 2) for stat in self.playoff_stats]

    def reset_to_base_record(self):
        self.wins = self.base_wins
        self.losses = self.base_losses
        self.division_wins = self.base_division_wins
        self.division_losses = self.base_division_losses


if __name__ == "__main__":

    local_config = AppConfigParser()
    local_config.read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"))

    playoff_probs = PlayoffProbabilities(
        local_config,
        simulations=100,
        num_weeks=13,
        num_playoff_slots=6,
        data_dir="."
    )

    # playoff_probs.calculate(week=8, week_for_report=7,)
