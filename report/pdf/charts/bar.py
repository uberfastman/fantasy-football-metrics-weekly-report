__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

# code snippets: http://www.reportlab.com/chartgallery/

import json
from typing import List, Any

from reportlab.graphics.charts.barcharts import HorizontalBarChart3D
from reportlab.graphics.charts.textlabels import Label
# noinspection PyProtectedMember
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin
from reportlab.lib.colors import PCMYKColor

from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


# noinspection PyUnresolvedReferences,PyPep8Naming
class HorizontalBarChart3DGenerator(_DrawingEditorMixin, Drawing):

    def __init__(self, data: List[List[Any]], font: str, font_size: int, x_axis_params: List[Any], box_width: int,
                 box_height: int, chart_width: int, chart_height: int, width: int = 550, height: int = 215, *args,
                 **kw):
        logger.debug(f"Generating 3D horizontal bar chart with data:\n{json.dumps(data, indent=2)}\n")

        num_teams = len(data)
        sorted_data = sorted(data, key=lambda x: x[3])

        data_colors = [[0, 0, 0, 0, 100]] * num_teams

        data_min = sorted_data[0]
        data_max = sorted_data[-1]

        data_without_min_max = sorted_data[1:-1]

        data_colors[data_min[0]] = [100, 0, 100, 0, 100]  # green
        data_colors[data_max[0]] = [0, 100, 100, 0, 100]  # red

        count = 1
        for team in data_without_min_max:
            data_colors[team[0]] = [
                100 - ((100 / num_teams) * count),
                (100 / num_teams) * count,
                100,
                0,
                100
            ]
            count += 1

        Drawing.__init__(self, width, height, *args, **kw)
        self._add(self, HorizontalBarChart3D(), name="chart", validate=None, desc=None)
        self._add(self, Label(), name="XLabel", validate=None, desc="The label on the horizontal axis")

        self.width = box_width
        self.height = box_height

        self.chart.x = 3.5 * len(max([team[1] for team in data], key=len))
        self.chart.y = -20

        self.chart.data = [[team[3] for team in data]]
        self.chart.width = chart_width
        self.chart.height = chart_height

        self.XLabel.fontName = font
        self.XLabel.fontSize = font_size
        self.XLabel.x = 275
        self.XLabel.y = -50
        self.XLabel.textAnchor = "middle"
        self.XLabel.maxWidth = 500
        self.XLabel.height = 20
        self.XLabel._text = x_axis_params[0]

        self.chart.valueAxis.forceZero = 1
        self.chart.valueAxis.visibleTicks = True
        self.chart.valueAxis.labels.boxAnchor = "autox"
        self.chart.valueAxis.valueMin = x_axis_params[1]
        self.chart.valueAxis.valueMax = x_axis_params[2]
        self.chart.valueAxis.valueStep = x_axis_params[3]
        self.chart.valueAxis.labels.fontName = font
        self.chart.valueAxis.labels.fontSize = font_size - 4
        self.chart.valueAxis.labels.rightPadding = 0
        self.chart.valueAxis.labels.dx = 1

        self.chart.categoryAxis.categoryNames = [team[1] for team in data]
        self.chart.categoryAxis.labels.fontName = font
        self.chart.categoryAxis.labels.fontSize = font_size - 4
        for i in range(0, num_teams):
            self.chart.categoryAxis.labels[i].fillColor = PCMYKColor(*data_colors[i])

        self.chart.barWidth = 20
        for i in range(0, num_teams):
            self.chart.bars[(0, i)].fillColor = PCMYKColor(*data_colors[i])
