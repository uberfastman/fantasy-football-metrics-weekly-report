import numpy as np


class ZScore(object):

    def __init__(self, weekly_teams):
        self.weekly_teams = weekly_teams

    def execute(self):

        results = {}

        # can only determine z_score
        can_calculate = len(self.weekly_teams) > 2

        # just grab first week team names
        # could be done in constructor or something
        for team_id in self.weekly_teams[0]:
            z_score = None

            if can_calculate:

                scores = [week[team_id].get("score") for week in self.weekly_teams]

                scores_excluding_current = scores[:-1]
                current_score = scores[-1]

                std = np.std(scores_excluding_current)
                mean = np.mean(scores_excluding_current)
                z_score = (current_score - mean) / std

            results[team_id] = z_score

        return results
