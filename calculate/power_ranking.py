import pandas as pd


# noinspection PyTypeChecker
class PowerRanking(object):
    def __init__(self):
        pass

    @staticmethod
    def power_ranking(row):
        result = (row["score_rank"] + row["coach_rank"] + row["luck_rank"]) / 3.0

        return result

    def execute_power_ranking(self, teams):
        """
        avg of (weekly points rank + weekly overall win rank)
        """

        teams = [teams[key] for key in teams]

        df = pd.DataFrame.from_dict(teams)

        df["score_rank"] = df["score"].rank()
        df["coach_rank"] = df["coaching_efficiency"].rank()
        df["luck_rank"] = df["luck"].rank()
        df["power_rank"] = df.apply(self.power_ranking, axis=1).rank(ascending=False)
        df["zscore_rank"] = df["zscore"].rank(ascending=False).fillna(0.0).astype(int)

        # convert to just return calculated results
        # TODO: this is probably not the best way?

        teams = df.to_dict(orient="records")

        results = {}

        for team in teams:
            results[team["name"]] = {
                "score_rank": team["score_rank"],
                "coach_rank": team["coach_rank"],
                "luck_rank": team["luck_rank"],
                "power_rank": team["power_rank"],
                "zscore_rank": team["zscore_rank"]
            }

        return results
