__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"
# code snippets: https://github.com/cdtdev/ff_monte_carlo (originally written by https://github.com/cdtdev)

import datetime
import json
import logging
import os
import pickle
import random
import traceback

import numpy as np

logger = logging.getLogger(__name__)


class PlayoffProbabilities(object):

    def __init__(self, simulations, num_weeks, num_playoff_slots, data_dir, save_data=False, recalculate=False,
                 dev_offline=False):
        self.simulations = int(simulations)
        self.num_weeks = int(num_weeks)
        self.num_playoff_slots = int(num_playoff_slots)
        self.data_dir = data_dir
        self.save_data = save_data
        self.recalculate = recalculate
        self.dev_offline = dev_offline
        self.playoff_probs_data = {}

    def calculate(self, week, week_for_report, standings, remaining_matchups):

        teams_for_playoff_probs = {}
        for team in standings:
            # noinspection PyTypeChecker
            teams_for_playoff_probs[team.team_id] = TeamWithPlayoffProbs(
                team.team_id,
                team.name,
                team.manager_str,
                int(team.wins),
                int(team.losses),
                int(team.ties),
                float(team.points_for),
                self.num_playoff_slots,
                self.simulations
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
                                result = int(random.getrandbits(1))
                                if result == 1:
                                    teams_for_playoff_probs[matchup[0]].add_win()
                                    teams_for_playoff_probs[matchup[1]].add_loss()
                                else:
                                    teams_for_playoff_probs[matchup[1]].add_win()
                                    teams_for_playoff_probs[matchup[0]].add_loss()

                        # sort the teams
                        sorted_teams = sorted(teams_for_playoff_probs.values(), key=lambda x: x.get_wins_with_points(),
                                              reverse=True)

                        # pick the teams making the playoffs
                        playoff_count = 1
                        while playoff_count <= self.num_playoff_slots:
                            teams_for_playoff_probs[sorted_teams[playoff_count - 1].team_id].add_playoff_tally()
                            avg_wins[playoff_count - 1] += \
                                round(sorted_teams[playoff_count - 1].get_wins_with_points(), 0)
                            teams_for_playoff_probs[sorted_teams[playoff_count - 1].team_id].add_playoff_stats(
                                playoff_count)
                            playoff_count += 1

                        for team in teams_for_playoff_probs.values():
                            team.reset_to_base_record()

                        sim_count += 1

                    for team in teams_for_playoff_probs.values():

                        playoff_min_wins = round((avg_wins[self.num_playoff_slots - 1]) / self.simulations, 2)
                        if playoff_min_wins > team.wins:
                            needed_wins = np.rint(playoff_min_wins - team.wins)
                        else:
                            needed_wins = 0

                        self.playoff_probs_data[int(team.team_id)] = [
                            team.name,
                            team.get_playoff_tally(),
                            team.get_playoff_stats(),
                            needed_wins
                        ]

                    delta = datetime.datetime.now() - begin
                    logger.info("...ran %s playoff simulation%s in %s\n" % ("{0:,}".format(
                        self.simulations), ("s" if self.simulations > 1 else ""), str(delta)))

                    if self.save_data:
                        with open(os.path.join(
                                self.data_dir,
                                "week_" + str(week_for_report),
                                "playoff_probs_data.pkl"), "wb") as pp_out:
                            pickle.dump(self.playoff_probs_data, pp_out, pickle.HIGHEST_PROTOCOL)

                else:
                    logger.info("Using saved Monte Carlo playoff simulations for playoff probabilities.")

                    playoff_probs_data_file_path = os.path.join(
                        self.data_dir, "week_" + str(week_for_report), "playoff_probs_data.pkl")
                    if os.path.exists(playoff_probs_data_file_path):
                        with open(playoff_probs_data_file_path, "rb") as pp_in:
                            self.playoff_probs_data = pickle.load(pp_in)
                    else:
                        raise FileNotFoundError(
                            "FILE {} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                                playoff_probs_data_file_path))

                return self.playoff_probs_data
            else:
                return None
        except Exception as e:
            logger.error("COULDN'T CALCULATE PLAYOFF PROBS WITH EXCEPTION: {}\n{}".format(e, traceback.format_exc()))
            return None

    def __str__(self):
        return json.dumps(self.__dict__, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.__dict__, indent=2, ensure_ascii=False)


class TeamWithPlayoffProbs(object):

    def __init__(self, team_id, name, manager, wins, losses, ties, points_for, playoff_slots, simulations):
        self.team_id = team_id
        self.name = name
        self.manager = manager
        self.base_wins = wins
        self.wins = wins
        self.base_losses = losses
        self.losses = losses
        self.ties = ties
        self.points_for = float(points_for)
        self.playoff_tally = 0
        self.playoff_stats = [0] * int(playoff_slots)
        self.simulations = int(simulations)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

    def add_win(self):
        self.wins += 1

    def add_loss(self):
        self.losses += 1

    def add_playoff_tally(self):
        self.playoff_tally += 1

    def add_playoff_stats(self, place):
        self.playoff_stats[place - 1] += 1

    def get_wins_with_points(self):
        return self.wins + (self.points_for / 1000000)

    def get_playoff_tally(self):
        return round((self.playoff_tally / self.simulations) * 100.0, 2)

    def get_playoff_stats(self):
        return [round((stat / self.simulations) * 100.0, 2) for stat in self.playoff_stats]

    def reset_to_base_record(self):
        self.wins = self.base_wins
        self.losses = self.base_losses
