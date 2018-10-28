from collections import defaultdict


# noinspection PyTypeChecker
class Breakdown(object):
    def __init__(self):
        pass

    @staticmethod
    def execute_breakdown(teams, matchups_list):

        result = defaultdict(dict)
        matchups = {name: value["result"] for pair in matchups_list for name, value in list(pair.items())}

        for team_name in teams:
            team = teams[team_name]
            record = {
                "W": 0,
                "L": 0,
                "T": 0
            }

            for team_name2, team2 in list(teams.items()):
                if team["team_id"] == team2["team_id"]:
                    continue
                score1 = team["score"]
                score2 = team2["score"]
                if score1 > score2:
                    record["W"] += 1
                elif score1 < score2:
                    record["L"] += 1
                else:
                    record["T"] += 1

            result[team_name]["breakdown"] = record

            # calc luck %
            # TODO: assuming no ties...  how are tiebreakers handled?
            luck = 0.0
            # number of teams excluding current team
            num_teams = float(len(list(teams.keys()))) - 1

            if record["W"] != 0 and record["L"] != 0:
                matchup_result = matchups[team_name]
                if matchup_result == "W" or matchup_result == "T":
                    luck = (record["L"] + record["T"]) / num_teams
                else:
                    luck = 0 - (record["W"] + record["T"]) / num_teams

            result[team_name]["luck"] = luck

        for team in teams:
            teams[team]["luck"] = result[team]["luck"] * 100
            teams[team]["breakdown"] = result[team]["breakdown"]
            teams[team]["matchup_result"] = result[team]

        return result
