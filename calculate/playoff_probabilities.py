__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"
# code snippets: https://github.com/cdtdev/ff_monte_carlo (originally written by https://github.com/cdtdev)

import copy
import datetime
import json
import logging
import os
import pickle
import random
import traceback

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class PlayoffProbabilities(object):

    def __init__(self, simulations, num_weeks, playoff_slots, data_dir, save_data=False, recalculate=False):
        self.simulations = int(simulations)
        self.num_weeks = int(num_weeks)
        self.playoff_slots = int(playoff_slots)
        self.data_dir = data_dir
        self.save_data = save_data
        self.recalculate = recalculate
        self.playoff_probs_data = {}

    def calculate(self, week, chosen_week, teams, remaining_matchups):

        try:
            if int(week) == int(chosen_week):
                if self.recalculate:
                    logger.info("Running %s Monte Carlo playoff simulations..." % "{0:,}".format(self.simulations))

                    begin = datetime.datetime.now()

                    num_wins_that_made_playoffs = [0] * self.num_weeks
                    num_wins_that_missed_playoffs = [0] * self.num_weeks
                    avg_wins = [0.0] * self.playoff_slots

                    sim_count = 1
                    while sim_count <= self.simulations:

                        temp_teams = copy.deepcopy(teams)

                        # create random binary results representing the rest of the matchups_by_week and add them to the existing wins
                        for week, matchups in remaining_matchups.items():
                            for matchup in matchups:
                                result = int(random.getrandbits(1))
                                if result == 1:
                                    temp_teams[matchup[0]].add_win()
                                else:
                                    temp_teams[matchup[1]].add_win()

                        # sort the teams
                        sorted_teams = sorted(temp_teams.values(), key=lambda x: x.wins_with_points, reverse=True)

                        num_wins_that_made_playoffs[
                            int(round(sorted_teams[self.playoff_slots - 1].get_wins_with_points(), 0)) - 1] += 1
                        num_wins_that_missed_playoffs[
                            int(round(sorted_teams[self.playoff_slots].get_wins_with_points(), 0)) - 1] += 1

                        # pick the teams making the playoffs
                        playoff_count = 1
                        while playoff_count <= self.playoff_slots:
                            teams[sorted_teams[playoff_count - 1].get_id()].add_playoff_tally()
                            avg_wins[playoff_count - 1] += round(sorted_teams[playoff_count - 1].get_wins_with_points(),
                                                                 0)
                            teams[sorted_teams[playoff_count - 1].get_id()].add_playoff_stats(playoff_count)
                            playoff_count += 1

                        sim_count += 1

                    for team in teams.values():

                        playoff_min_wins = round((avg_wins[self.playoff_slots - 1]) / self.simulations, 2)
                        if playoff_min_wins > team.get_wins():
                            needed_wins = np.rint(playoff_min_wins - team.get_wins())
                        else:
                            needed_wins = 0

                        self.playoff_probs_data[int(team.get_id())] = [
                            team.get_name(),
                            team.get_playoff_tally(),
                            team.get_playoff_stats(),
                            needed_wins
                        ]

                    delta = datetime.datetime.now() - begin
                    logger.info("...ran %s playoff simulations in %s\n" % ("{0:,}".format(self.simulations), str(delta)))

                    if self.save_data:
                        with open(os.path.join(
                                self.data_dir, "week_" + str(chosen_week), "playoff_probs_data.pkl"), "wb") as pp_out:
                            pickle.dump(self.playoff_probs_data, pp_out, pickle.HIGHEST_PROTOCOL)

                else:
                    logger.info("Using saved Monte Carlo playoff simulations for playoff probabilities.")

                    playoff_probs_data_file_path = os.path.join(
                        self.data_dir, "week_" + str(chosen_week), "playoff_probs_data.pkl")
                    if os.path.exists(playoff_probs_data_file_path):
                        with open(playoff_probs_data_file_path, "rb") as pp_in:
                            self.playoff_probs_data = pickle.load(pp_in)
                    else:
                        raise FileNotFoundError(
                            "FILE {} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY PERSISTED DATA!".format(
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


class Team(object):

    def __init__(self, team_id, name, manager, record, points_for, playoff_slots, simulations):
        self.team_id = team_id
        self.name = name
        self.manager = manager
        self.record = record
        self.points_for = float(points_for)
        self.wins_with_points = self.record.wins + (self.points_for / 1000000)
        self.playoff_tally = 0
        self.playoff_stats = [0] * int(playoff_slots)
        self.simulations = int(simulations)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

    def add_win(self):
        self.wins_with_points += 1

    def add_playoff_tally(self):
        self.playoff_tally += 1

    def add_playoff_stats(self, place):
        self.playoff_stats[place - 1] += 1

    def get_id(self):
        return self.team_id

    def get_name(self):
        return self.name

    def get_manager(self):
        return self.manager

    def get_wins(self):
        return self.record.get_wins()

    def get_losses(self):
        return self.record.get_losses()

    def get_ties(self):
        return self.record.get_ties()

    def get_points(self):
        return self.points_for

    def get_wins_with_points(self):
        return self.wins_with_points

    def get_playoff_tally(self):
        return round((self.playoff_tally / self.simulations) * 100.0, 2)

    def get_playoff_stats(self):
        return [round((stat / self.simulations) * 100.0, 2) for stat in self.playoff_stats]


class Record(object):

    def __init__(self, wins, losses, ties, percentage):
        self.wins = wins
        self.losses = losses
        self.ties = ties
        self.percentage = percentage

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)

    def get_wins(self):
        return self.wins

    def get_losses(self):
        return self.losses

    def get_ties(self):
        return self.ties

    def get_percentage(self):
        return self.percentage
