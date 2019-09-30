__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import numpy as np

from calculate.metrics import CalculateMetrics


class SeasonAverageCalculator(object):
    def __init__(self, team_names, report_data):
        self.team_names = team_names
        self.report_data = report_data

    def get_average(self, data, key, with_percent, bench_column=True, ce_first_ties=False, reverse=True):

        season_average_list = []
        team_index = 0
        for team in data:
            team_name = self.team_names[team_index]

            valid_values = [value[1] if value[1] else 0 for value in team]
            average = np.mean(valid_values)
            season_average_value = "{0:.2f}".format(average)

            season_average_list.append([team_name, season_average_value])
            team_index += 1
        ordered_average_values = sorted(season_average_list, key=lambda x: float(x[1]), reverse=reverse)
        index = 0
        for team in ordered_average_values:
            ordered_average_values[ordered_average_values.index(team)] = [index, team[0], team[1]]
            index += 1

        ordered_average_values = CalculateMetrics(None, None, None, None).resolve_season_average_ties(
            ordered_average_values, with_percent)

        ordered_season_average_list = []
        for ordered_team in getattr(self.report_data, key):
            for team in ordered_average_values:
                if ordered_team[1] == team[1]:
                    if with_percent:
                        ordered_team[3] = "{0:.2f}%".format(float(str(ordered_team[3]).replace("%", ""))) if \
                            ordered_team[3] != "DQ" else "DQ"

                        if key == "data_for_coaching_efficiency" and ce_first_ties:
                            ordered_team.insert(-2, str(team[2]))
                        else:
                            ordered_team.append(str(team[2]))

                    elif bench_column:
                        ordered_team[3] = "{0:.2f}".format(float(str(ordered_team[3])))
                        ordered_team.insert(-1, str(team[2]))

                    else:
                        value = "{0}".format(str(team[2]))
                        if key == "data_for_z_scores":
                            value = value.split(" ")[0]
                        ordered_team.append(value)

                    ordered_season_average_list.append(ordered_team)

        return ordered_season_average_list
