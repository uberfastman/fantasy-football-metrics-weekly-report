# code based on https://github.com/cdtdev/ff_monte_carlo (originally written by https://github.com/cdtdev)

import copy
import datetime
import random

import numpy as np


class PlayoffProbabilities(object):

    def __init__(self, simulations, num_weeks, week, playoff_slots, teams, matchups):
        self.simulations = simulations
        self.num_weeks = num_weeks
        self.week = week
        self.playoff_slots = playoff_slots
        self.teams = teams
        self.matchups = matchups

    def calculate(self, chosen_week):

        if int(self.week) == int(chosen_week):

            print("Running %s Monte Carlo playoff simulations..." % "{0:,}".format(self.simulations))

            begin = datetime.datetime.now()

            team_data = {}

            num_wins_that_made_playoffs = [0] * self.num_weeks
            num_wins_that_missed_playoffs = [0] * self.num_weeks
            avg_wins = [0.0] * self.playoff_slots

            sim_count = 1
            while sim_count <= self.simulations:

                temp_teams = copy.deepcopy(self.teams)

                # create random binary results representing the rest of the matchups and add them to the existing wins
                for week, matchups in self.matchups.items():
                    for matchup in matchups:
                        result = int(random.getrandbits(1))
                        if result == 1:
                            temp_teams[matchup[0]].add_win()
                        else:
                            temp_teams[matchup[1]].add_win()

                # sort the teams
                sorted_teams = sorted(temp_teams.values(), key=lambda x: x.get_wins_with_points(), reverse=True)

                num_wins_that_made_playoffs[int(round(sorted_teams[self.playoff_slots - 1].get_wins_with_points(), 0)) - 1] += 1
                num_wins_that_missed_playoffs[int(round(sorted_teams[self.playoff_slots].get_wins_with_points(), 0)) - 1] += 1

                # pick the teams making the playoffs
                playoff_count = 1
                while playoff_count <= self.playoff_slots:
                    self.teams[sorted_teams[playoff_count - 1].get_id()].add_playoff_tally()
                    avg_wins[playoff_count - 1] += round(sorted_teams[playoff_count - 1].get_wins_with_points(), 0)
                    self.teams[sorted_teams[playoff_count - 1].get_id()].add_playoff_stats(playoff_count)
                    playoff_count += 1

                sim_count += 1

            for team in self.teams.values():
                # print(
                #     team.get_name() + "\t" +
                #     str(team.get_playoff_tally()) + "\t" +
                #     "\t".join([str(stat) for stat in team.get_playoff_stats()])
                # )

                playoff_min_wins = round((avg_wins[self.playoff_slots - 1]) / self.simulations, 2)
                if playoff_min_wins > team.get_wins():
                    needed_wins = np.rint(playoff_min_wins - team.get_wins())
                else:
                    needed_wins = 0

                team_data[int(team.get_id())] = [
                    team.get_name(),
                    team.get_playoff_tally(),
                    team.get_playoff_stats(),
                    needed_wins
                ]

            # print()
            # print("Average # of wins for playoff spot")
            # playoff_count = 1
            # while playoff_count <= self.playoff_slots:
            #     print(str(playoff_count) + '\t' + str(round((avg_wins[playoff_count - 1]) / self.simulations, 2)))
            #     playoff_count += 1

            # print()
            # print("Histogram of wins required for final playoff spot")
            # playoffs_made_count = 1
            # while playoffs_made_count <= len(num_wins_that_made_playoffs):
            #     print(
            #         str(playoffs_made_count) + "\t" +
            #         str(round(((num_wins_that_made_playoffs[playoffs_made_count - 1]) /
            #                    (self.simulations * 1.0)) * 100, 3)) + "\t" +
            #         str(round(((num_wins_that_missed_playoffs[playoffs_made_count - 1]) /
            #                      (self.simulations * 1.0)) * 100, 3))
            #     )
            #     playoffs_made_count += 1
            #
            delta = datetime.datetime.now() - begin
            print("...ran %s playoff simulations in %s\n" % ("{0:,}".format(self.simulations), str(delta)))

            return team_data
        else:
            return None


class Team(object):

    def __init__(self, team_id, name, manager, record, points_for, playoff_slots, simulations):
        self.team_id = team_id
        self.name = name
        self.manager = manager
        self.record = record
        self.points_for = points_for
        self.wins_with_points = self.record.get_wins() + (self.points_for / 1000000)
        self.playoff_tally = 0
        self.playoff_stats = [0] * playoff_slots
        self.simulations = simulations

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


# if __name__ == '__main__':
#
#     sim = 1000
#     number_weeks = 13
#     current_week = 9
#     play_slots = 6
#
#     all_teams = {
#         1: Team(1, 'Kingsland Tough Bruddas', "joe", Record(3, 5, 0, .5), 715.3, play_slots, sim),
#         2: Team(2, 'Schroedingers Cats', "joe", Record(6, 2, 0, .5), 834.4, play_slots, sim),
#         3: Team(3, 'The Killer Brees', "joe", Record(5, 3, 0, .5), 767.3, play_slots, sim),
#         4: Team(4, 'Deez Nuts 4 Prez', "joe", Record(2, 6, 0, .5), 687.0, play_slots, sim),
#         5: Team(5, 'Oakeridge Overlords', "joe", Record(3, 5, 0, .5), 651.2, play_slots, sim),
#         6: Team(6, 'College Hillbilly', "joe", Record(4, 4, 0, .5), 710.9, play_slots, sim),
#         7: Team(7, 'Norwood Knuckles', "joe", Record(6, 2, 0, .5), 702.0, play_slots, sim),
#         8: Team(8, 'West City Possums', "joe", Record(4, 4, 0, .5), 722.2, play_slots, sim),
#         9: Team(9, 'Crazy Monkeys', "joe", Record(3, 5, 0, .5), 708.2, play_slots, sim),
#         10: Team(10, 'Mount Thunderbolts', "joe", Record(4, 4, 0, .5), 700.3, play_slots, sim),
#         11: Team(11, 'Southeast Bulls', "joe", Record(4, 4, 0, .5), 753.9, play_slots, sim),
#         12: Team(12, 'Te Puke Thunder', "joe", Record(4, 4, 0, .5), 740.5, play_slots, sim)
#     }
#
#     all_matchups = {
#         9: [
#             (3, 5),
#             (4, 12),
#             (6, 1),
#             (8, 11),
#             (9, 2),
#             (10, 7)
#         ],
#         10: [
#             (1, 8),
#             (2, 10),
#             (5, 9),
#             (7, 6),
#             (11, 4),
#             (12, 3)
#         ],
#         11: [
#             (3, 11),
#             (4, 1),
#             (6, 2),
#             (8, 7),
#             (9, 12),
#             (10, 5)
#         ],
#         12: [
#             (3, 1),
#             (4, 7),
#             (6, 5),
#             (8, 2),
#             (9, 11),
#             (10, 12)
#         ],
#         13: [
#             (1, 9),
#             (2, 4),
#             (5, 8),
#             (7, 3),
#             (11, 10),
#             (12, 6)
#         ],
#     }
#
#     pp = PlayoffProbabilities(sim, number_weeks, current_week, play_slots, all_teams, all_matchups)
#     pp.calculate()
