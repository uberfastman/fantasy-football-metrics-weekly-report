# written by Wren J.R.
# code snippets taken from: http://www.reportlab.com/chartgallery/

from reportlab.graphics.charts.axes import XValueAxis
from reportlab.graphics.charts.legends import LineLegend
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.shapes import Drawing, _DrawingEditorMixin, Rect
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib.colors import PCMYKColor, black
from reportlab.lib.validators import Auto


# noinspection PyUnresolvedReferences
class LineChartGenerator(_DrawingEditorMixin, Drawing):
    """
        Chart Features
        ============
        - **background.fillColor** sets the CMYK fill color
        - **background.height**, **background.width**, **background.x**, and **background.y** define the size and position of the fill.
        - Note also that **legend.colorNamePairs** is set automatically based on the colors and names of the lines. This makes a lot of sense compared to other examples in which these are defined separately and may differ from the lines they are associated with.
    """

    def __init__(self, series_colors_cmyk, box_width, box_height, chart_width, chart_height, width=550, height=215,
                 *args, **kw):
        Drawing.__init__(self, width, height, *args, **kw)
        Drawing.hAlign = 'CENTER'

        font_name = 'Helvetica'
        # self.width = 550
        # self.height = 240
        self.width = box_width
        self.height = box_height
        self._add(self, LinePlot(), name='chart', validate=None, desc=None)
        self._add(self, LineLegend(), name='legend', validate=None, desc=None)

        # self.chart.width = 490
        # self.chart.height = 150
        self.chart.width = chart_width
        self.chart.height = chart_height
        self.chart.y = 60
        self.chart.x = 45
        self.chart.strokeWidth = 1

        for color in series_colors_cmyk:
            index = series_colors_cmyk.index(color)
            self.chart.lines[index].strokeColor = PCMYKColor(color[0], color[1], color[2], color[3], alpha=color[4])
            self.chart.lines[index].symbol = makeMarker('FilledCircle')
            self.chart.lines[index].symbol.strokeColor = PCMYKColor(color[0], color[1], color[2], color[3],
                                                                    alpha=color[4])
            self.chart.lines[index].symbol.size = 5
        self.chart.lines.strokeWidth = 2

        self.legend.colorNamePairs = Auto(obj=self.chart)
        self.legend.x = 5
        self.legend.y = 30
        # set size of swatches
        self.legend.dx = 0
        self.legend.dy = 0
        self.legend.fontName = font_name
        self.legend.fontSize = 8
        self.legend.alignment = 'right'
        self.legend.columnMaximum = 2
        self.legend.dxTextSpace = 4
        self.legend.variColumn = 1
        self.legend.boxAnchor = 'nw'
        self.legend.deltay = 15
        self.legend.autoXPadding = 20

        self.background = Rect(0, 0, self.width, self.height, strokeWidth=0, fillColor=PCMYKColor(0, 0, 10, 0))
        self.background.strokeColor = black
        self.background.fillOpacity = 0.25
        self.background.strokeWidth = 0
        self.background.x = 0
        self.background.fillColor = PCMYKColor(16, 12, 13, 0, alpha=30)

    def make_title(self, title):

        self._add(self, Label(), name='Title', validate=None, desc="The title at the top of the chart")

        self.Title.fontName = 'Helvetica-Bold'
        self.Title.fontSize = 14
        self.Title.x = 265
        self.Title.y = 225
        self.Title._text = title
        self.Title.maxWidth = 500
        self.Title.height = 20
        self.Title.textAnchor = 'middle'

    def make_x_axis(self, x_label, x_min, x_max, x_step):

        self._add(self, Label(), name='XLabel', validate=None, desc="The label on the horizontal axis")

        self.XLabel.fontName = 'Helvetica'
        self.XLabel.fontSize = 10
        self.XLabel.x = 22
        self.XLabel.y = 45
        self.XLabel.textAnchor = 'middle'
        self.XLabel.maxWidth = 500
        self.XLabel.height = 20
        self.XLabel._text = x_label

        self.chart.xValueAxis = XValueAxis()
        self.chart.xValueAxis.labels.boxAnchor = 'autox'
        self.chart.xValueAxis.valueMin = x_min
        self.chart.xValueAxis.valueMax = x_max
        self.chart.xValueAxis.valueStep = x_step
        self.chart.xValueAxis.labels.fontName = "Helvetica"
        self.chart.xValueAxis.labels.fontSize = 10
        self.chart.xValueAxis.visibleTicks = 1
        self.chart.xValueAxis.labels.rightPadding = 0
        self.chart.xValueAxis.labels.dx = 1
        # self.chart.xValueAxis.strokeWidth = 0
        # self.chart.xValueAxis.visibleAxis = 1
        # print(self.chart.xValueAxis.getProperties())
        # self.chart.xValueAxis.labels.angle = 45

    def make_y_axis(self, y_label, y_min, y_max, y_step):

        self._add(self, Label(), name='YLabel', validate=None, desc="The label on the vertical axis")

        self.YLabel.fontName = 'Helvetica'
        self.YLabel.fontSize = 10
        self.YLabel.x = 20
        self.YLabel.y = 140
        self.YLabel.angle = 90
        self.YLabel.textAnchor = 'middle'
        self.YLabel.maxWidth = 200
        self.YLabel.height = 20
        self.YLabel._text = y_label

        self.chart.yValueAxis.valueMin = y_min
        self.chart.yValueAxis.valueMax = y_max
        self.chart.yValueAxis.valueStep = y_step
        self.chart.yValueAxis.visibleGrid = 1
        self.chart.yValueAxis.visibleAxis = 1
        self.chart.yValueAxis.visibleTicks = 0
        self.chart.yValueAxis.labels.fontName = "Helvetica"
        self.chart.yValueAxis.labels.fontSize = 10
        self.chart.yValueAxis.labelTextFormat = '%0.0f'
        self.chart.yValueAxis.strokeWidth = 0
        self.chart.yValueAxis.gridStrokeWidth = 0.25
        self.chart.yValueAxis.labels.rightPadding = 5
        self.chart.yValueAxis.maximumTicks = 15
        self.chart.yValueAxis.rangeRound = 'both'
        self.chart.yValueAxis.avoidBoundFrac = 0.1
        self.chart.yValueAxis.labels.dx = 3
        self.chart.yValueAxis.forceZero = 0
        self.chart.yValueAxis.gridStrokeColor = PCMYKColor(100, 100, 100, 100, alpha=100)
        self.chart.yValueAxis.visible = 1
        self.chart.yValueAxis.strokeColor = black
        self.chart.yValueAxis.labelTextScale = 1
        self.chart.yValueAxis.labels.fillColor = black

    def make_data(self, data):

        self.chart.data = data

    def make_series_labels(self, series_labels):

        for i in range(len(series_labels)):
            self.chart.lines[i].name = series_labels[i]
