__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from typing import Any, List

import numpy as np

from ffmwr.calculate.metrics import CalculateMetrics
from ffmwr.report.data import ReportData
from ffmwr.utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class SeasonAverageCalculator(object):
    def __init__(self, team_names: List[str], report_data: ReportData, break_ties: bool):
        logger.debug("Initializing season averages.")

        self.team_names: List[str] = team_names
        self.report_data: ReportData = report_data
        self.break_ties: bool = break_ties

    def get_average(
        self,
        data: List[List[List[Any]]],
        key: str,
        with_percent: bool = False,
        first_ties: bool = False,
        reverse: bool = True,
    ) -> List[List[Any]]:
        logger.debug(f'Calculating season average from "{key}".')

        season_average_list = []
        team_index = 0
        for team in data:
            team_name = self.team_names[team_index]

            valid_values = [value[1] for value in team if (value[1] is not None and value[1] != "DQ")]
            average = np.mean(valid_values)
            season_average_value = f"{average:.2f}"

            season_average_list.append([team_name, season_average_value])
            team_index += 1
        ordered_average_values = sorted(season_average_list, key=lambda x: float(x[1]), reverse=reverse)
        index = 0
        for team in ordered_average_values:
            ordered_average_values[ordered_average_values.index(team)] = [index, team[0], team[1]]
            index += 1

        ordered_average_values = CalculateMetrics(None, None, None).resolve_season_average_ties(
            ordered_average_values, with_percent
        )

        ordered_season_average_list = []
        for ordered_team in getattr(self.report_data, key):
            for team in ordered_average_values:
                if ordered_team[1] == team[1]:
                    if with_percent:
                        ordered_team[3] = (
                            f"{float(str(ordered_team[3]).replace('%', '')):.2f}%" if ordered_team[3] != "DQ" else "DQ"
                        )
                        value = str(team[2])
                    elif key == "data_for_scores":
                        ordered_team[3] = f"{float(str(ordered_team[3])):.2f}"
                        value = str(team[2])
                    else:
                        value = f"{str(team[2])}"

                    if key == "data_for_scores":
                        ordered_team.insert(-1, value)
                    elif key == "data_for_coaching_efficiency" and self.break_ties and first_ties:
                        ordered_team.insert(-2, value)
                    else:
                        ordered_team.append(value)

                    ordered_season_average_list.append(ordered_team)

        return ordered_season_average_list
