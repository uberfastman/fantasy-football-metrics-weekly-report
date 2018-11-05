import numpy as np

from calculate.metrics import CalculateMetrics


class SeasonAverageCalculator(object):
    def __init__(self, team_names, report_info_dict):
        self.team_names = team_names
        self.report_info_dict = report_info_dict

    def get_average(self, data, key, with_percent_bool, bench_column_bool=True, reverse_bool=True):

        season_average_list = []
        team_index = 0
        for team in data:
            team_name = self.team_names[team_index]
            # season_average_value = "{0:.2f}".format(sum([float(week[1]) for week in team]) / float(len(team)))

            valid_values = [value[1] for value in team if value[1] is not None]
            average = np.mean(valid_values)
            season_average_value = "{0:.2f}".format(average)

            season_average_list.append([team_name, season_average_value])
            team_index += 1
        ordered_average_values = sorted(season_average_list, key=lambda x: float(x[1]), reverse=reverse_bool)
        index = 0
        for team in ordered_average_values:
            ordered_average_values[ordered_average_values.index(team)] = [index, team[0], team[1]]
            index += 1

        ordered_average_values = CalculateMetrics(None, None, None).resolve_season_average_ties(ordered_average_values,
                                                                                                with_percent_bool)

        ordered_season_average_list = []
        for ordered_team in self.report_info_dict.get(key):
            for team in ordered_average_values:
                if ordered_team[1] == team[1]:
                    if with_percent_bool:
                        ordered_team[3] = "{0:.2f}%".format(float(str(ordered_team[3]).replace("%", ""))) if \
                            ordered_team[3] != "DQ" else "DQ"
                        ordered_team.append(str(team[2]))

                    elif bench_column_bool:
                        ordered_team[3] = "{0:.2f}".format(float(str(ordered_team[3])))
                        ordered_team.insert(-1, str(team[2]))

                    else:
                        value = "{0}".format(str(team[2]))
                        if key == "zscore_results_data":
                            value = value.split(" ")[0]
                        ordered_team.append(value)

                    ordered_season_average_list.append(ordered_team)

        return ordered_season_average_list
