__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

# code snippets: https://www.reportlab.com/snippets/4/

import json
from typing import List, Any

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
# noinspection PyProtectedMember
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin
from reportlab.lib.colors import HexColor, black
from reportlab.lib.colors import white

from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


# noinspection PyUnresolvedReferences
class BreakdownPieDrawing(_DrawingEditorMixin, Drawing):

    def __init__(self, labels: List[str], data: List[float], width: int = 400, height: int = 200,
                 font: str = "Helvetica", *args, **kw):
        logger.debug(f"Generating pie chart with data:\n{json.dumps(data, indent=2)}\n")

        # see https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/ for colors
        pdf_chart_colors = [
            HexColor("#e6194b"),  # red
            HexColor("#3cb44b"),  # green
            HexColor("#ffe119"),  # yellow
            HexColor("#0082c8"),  # blue
            HexColor("#f58231"),  # orange
            HexColor("#911eb4"),  # purple
            HexColor("#46f0f0"),  # cyan
            HexColor("#f032e6"),  # magenta
            HexColor("#d2f53c"),  # lime
            HexColor("#fabebe"),  # pink
            HexColor("#008080"),  # teal
            HexColor("#e6beff")  # ,  # lavender
            # HexColor("#800000"),  # maroon
            # HexColor("#9A6324"),  # brown
            # HexColor("#808000"),  # olive
            # HexColor("#000075"),  # navy
            # HexColor("#aaffc3"),  # mint
            # HexColor("#fabebe"),  # pink
            # HexColor("#ffd8b1"),  # apricot
            # HexColor("#fffac8")  # beige
        ]

        Drawing.__init__(self, width, height, *args, **kw)
        # adding a pie chart to the drawing
        self._add(self, Pie(), name="pie", validate=None, desc=None)
        self.pie.width = 150
        self.pie.height = self.pie.width
        self.pie.x = 75
        self.pie.y = (height - self.pie.height) / 2
        # self.pie.data = [26.90, 13.30, 11.10, 9.40, 8.50, 7.80, 7.00, 6.20, 8.80, 1.00]
        # replace negative scores with 0.0 so that pie chart does not display negative values as a positive slice
        filtered_data = []
        for score in data:
            if score >= 0:
                filtered_data.append(score)
            else:
                filtered_data.append(0.0)
        self.pie.data = filtered_data
        # self.pie.labels = ['Financials', 'Energy', 'Health Care', 'Telecoms', 'Consumer', 'Consumer 2', 'Industrials',
        #                    'Materials', 'Other', 'Liquid Assets']
        self.pie.labels = labels
        self.pie.simpleLabels = 1
        self.pie.slices.label_visible = 0
        self.pie.slices.fontColor = None
        self.pie.slices.strokeColor = white
        self.pie.slices.strokeWidth = 1
        # adding legend
        self._add(self, Legend(), name="legend", validate=None, desc=None)
        self.legend.x = 235
        self.legend.y = height / 2
        self.legend.dx = 8
        self.legend.dy = 8
        self.legend.fontName = font
        self.legend.fontSize = 7
        self.legend.boxAnchor = "w"
        self.legend.columnMaximum = 10
        self.legend.strokeWidth = 1
        self.legend.strokeColor = black
        self.legend.deltax = 75
        self.legend.deltay = 10
        self.legend.autoXPadding = 5
        self.legend.yGap = 0
        self.legend.dxTextSpace = 5
        self.legend.alignment = "right"
        self.legend.dividerLines = 1 | 2 | 4
        self.legend.dividerOffsY = 4.5
        self.legend.subCols.rpad = 30
        data_len = len(self.pie.data)
        self.set_items(data_len, self.pie.slices, "fillColor", pdf_chart_colors)
        self.legend.colorNamePairs = [
            (self.pie.slices[i].fillColor, (self.pie.labels[i][0:20], f"{data[i]:0.2f}")) for i in range(data_len)]

    @staticmethod
    def set_items(data_len: int, obj: Any, attr: str, values: List[Any]):
        m = len(values)
        i = m // data_len
        for j in range(data_len):
            setattr(obj[j], attr, values[j * i % m])
