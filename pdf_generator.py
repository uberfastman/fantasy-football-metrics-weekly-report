# Written by: Wren J. Rudolph
from __future__ import print_function
from __future__ import print_function

import distutils.util as distutils
from ConfigParser import ConfigParser

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, inch, portrait
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import Spacer

from chart_generator import LineChartGenerator

config = ConfigParser()
config.read('config.ini')


class PdfGenerator(object):
    def __init__(self,
                 weekly_standings_results,
                 weekly_score_results,
                 weekly_coaching_efficiency_results,
                 weekly_luck_results,
                 num_tied_scores,
                 num_tied_efficiencies,
                 num_tied_luck,
                 efficiency_dq_count,
                 league_id,
                 report_title_text,
                 report_footer_text,
                 standings_title_text,
                 points_title_text,
                 tied_weekly_score_bool,
                 coaching_efficiency_title_text,
                 tied_weekly_coaching_efficiency_bool,
                 luck_title_text,
                 tied_weekly_luck_bool):

        self.weekly_standings_results = weekly_standings_results
        self.weekly_score_results = weekly_score_results
        self.weekly_coaching_efficiency_results = weekly_coaching_efficiency_results
        self.weekly_luck_results = weekly_luck_results
        self.num_tied_scores = num_tied_scores
        self.num_tied_efficiencies = num_tied_efficiencies
        self.num_tied_luck = num_tied_luck
        self.efficiency_dq_count = efficiency_dq_count
        self.league_id = league_id
        self.report_footer_text = report_footer_text
        self.tied_points_bool = tied_weekly_score_bool
        self.tied_efficiency_bool = tied_weekly_coaching_efficiency_bool
        self.tied_luck_bool = tied_weekly_luck_bool

        # Configure style and word wrap
        self.stylesheet = getSampleStyleSheet()
        self.text_style = self.stylesheet["BodyText"]
        self.text_styleN = self.stylesheet['Normal']
        self.text_styleH = self.stylesheet['Heading3']
        self.text_styleT = self.stylesheet['Heading2']
        self.text_style.wordWrap = 'CJK'

        title_table_style_list = [
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ]

        self.title_style = TableStyle(title_table_style_list)

        # Reportlab fonts: https://github.com/mattjmorrison/ReportLab/blob/master/src/reportlab/lib/fonts.py
        table_style_list = [
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.green),
            ('FONT', (0, 1), (-1, 1), 'Helvetica-Oblique'),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('GRID', (0, 0), (-1, 0), 1.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
        ]

        self.style = TableStyle(table_style_list)

        self.num_tied_scores = num_tied_scores
        tied_scores_iterator = num_tied_scores + 1
        tied_scores_table_style_list = list(table_style_list)

        if league_id == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):
            tied_scores_table_style_list.append(('TEXTCOLOR', (0, 1), (-1, 1), colors.green))
            tied_scores_table_style_list.append(('FONT', (0, 1), (-1, 1), 'Helvetica-Oblique'))
        else:
            index = 1
            while tied_scores_iterator > 0:
                tied_scores_table_style_list.append(('TEXTCOLOR', (0, index), (-1, index), colors.green))
                tied_scores_table_style_list.append(('FONT', (0, index), (-1, index), 'Helvetica-Oblique'))
                tied_scores_iterator -= 1
                index += 1

        tied_efficiencies_iterator = num_tied_efficiencies + 1
        tied_efficiencies_table_style_list = list(table_style_list)
        index = 1
        while tied_efficiencies_iterator > 0:
            tied_efficiencies_table_style_list.append(('TEXTCOLOR', (0, index), (3, index), colors.green))
            tied_efficiencies_table_style_list.append(('FONT', (0, index), (3, index), 'Helvetica-Oblique'))
            tied_efficiencies_iterator -= 1
            index += 1

        tied_luck_iterator = num_tied_luck + 1
        tied_luck_table_style_list = list(table_style_list)
        index = 1
        while tied_luck_iterator > 0:
            tied_luck_table_style_list.append(('TEXTCOLOR', (0, index), (3, index), colors.green))
            tied_luck_table_style_list.append(('FONT', (0, index), (3, index), 'Helvetica-Oblique'))
            tied_luck_iterator -= 1
            index += 1

        self.style_tied_scores = TableStyle(tied_scores_table_style_list)
        self.style_tied_efficiencies = TableStyle(tied_efficiencies_table_style_list)
        self.style_tied_luck = TableStyle(tied_luck_table_style_list)

        dq_index = len(weekly_score_results) - efficiency_dq_count + 1

        if num_tied_efficiencies > 0:
            efficiencies_dq_table_style_list = list(tied_efficiencies_table_style_list)
        else:
            efficiencies_dq_table_style_list = list(table_style_list)

        if efficiency_dq_count > 0:

            while efficiency_dq_count > 0:
                efficiencies_dq_table_style_list.append(('TEXTCOLOR', (0, dq_index), (3, dq_index), colors.red))
                efficiency_dq_count -= 1
                dq_index += 1

        self.style_efficiency_dqs = TableStyle(efficiencies_dq_table_style_list)

        # options: "document", "section", or None/empty
        self.report_title = self.create_title(report_title_text, element_type="document")
        self.standings_title = self.create_title(standings_title_text, element_type="section")
        self.points_title = self.create_title(points_title_text, element_type="section")
        self.efficiency_title = self.create_title(coaching_efficiency_title_text, element_type="section")
        self.luck_title = self.create_title(luck_title_text, element_type="section")

    def create_title(self, title_text, element_type=None):

        if element_type == "document":
            title_text_style = self.text_styleT
        elif element_type == "section":
            title_text_style = self.text_styleH
        else:
            title_text_style = self.text_styleN

        title = Paragraph('''<para align=center spaceb=3><b>''' + title_text + '''</b></para>''', title_text_style)
        title_table = Table([[title]], colWidths=[5 * inch] * 1)
        title_table.setStyle(self.title_style)
        return title_table

    def create_data_table(self, col_headers, data, table_style_for_ties, col_widths=None, tied_metric_bool=False):

        [col_headers.append(item) for item in data]
        table = Table(col_headers, colWidths=col_widths)

        if tied_metric_bool:
            table.setStyle(table_style_for_ties)
        else:
            table.setStyle(self.style)
        return table

    def generate_pdf(self, filename_with_path, chart_data_list):

        elements = []
        spacer_small = Spacer(1, 0.05 * inch)
        spacer_large = Spacer(1, 0.10 * inch)
        metric_scores_col_widths = [0.75 * inch, 1.75 * inch, 1.75 * inch, 2.00 * inch]

        doc = SimpleDocTemplate(filename_with_path, pagesize=LETTER, rightMargin=25, leftMargin=25, topMargin=10,
                                bottomMargin=10)
        doc.pagesize = portrait(LETTER)

        elements.append(self.report_title)
        elements.append(spacer_large)

        elements.append(self.standings_title)
        standings_headers = [
            ["Place", "Team", "Manager", "Record", "Points For", "Points Against", "Streak", "Waiver", "Moves",
             "Trades"]]
        standings_col_widths = [0.50 * inch, 1.75 * inch, 1.00 * inch, 1.00 * inch, 0.80 * inch, 1.10 * inch,
                                0.50 * inch, 0.50 * inch, 0.50 * inch, 0.50 * inch]
        elements.append(
            self.create_data_table(standings_headers, self.weekly_standings_results, self.style, standings_col_widths))

        elements.append(PageBreak())
        elements.append(self.points_title)
        points_headers = [["Place", "Team", "Manager", "Points"]]
        if self.num_tied_scores > 0:
            if self.league_id == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):
                points_headers[0].append("Bench Points")
            else:
                for index, team in enumerate(self.weekly_score_results):
                    self.weekly_score_results[index] = team[:-1]
        else:
            for index, team in enumerate(self.weekly_score_results):
                self.weekly_score_results[index] = team[:-1]

        elements.append(self.create_data_table(points_headers, self.weekly_score_results, self.style_tied_scores,
                                               metric_scores_col_widths, self.tied_points_bool))

        if self.tied_points_bool:
            if self.league_id != config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):
                elements.append(Paragraph(
                    "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie for first place.</i>",
                    getSampleStyleSheet()["Normal"]))

        elements.append(spacer_small)
        elements.append(self.efficiency_title)
        efficiency_headers = [["Place", "Team", "Manager", "Coaching Efficiency (%)"]]
        coaching_efficiency_table = self.create_data_table(efficiency_headers, self.weekly_coaching_efficiency_results,
                                                           self.style_tied_efficiencies, metric_scores_col_widths,
                                                           self.tied_efficiency_bool)
        if self.efficiency_dq_count > 0:
            coaching_efficiency_table.setStyle(self.style_efficiency_dqs)
        elements.append(coaching_efficiency_table)

        if self.tied_efficiency_bool:
            elements.append(spacer_small)
            if self.league_id == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):
                elements.append(Paragraph(
                    "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*The league commissioner will resolve coaching efficiency ties manually. The winner will be the manager whose team contains the most players who have exceeded their average weekly fantasy points.</i>",
                    getSampleStyleSheet()["Normal"]))
            else:
                elements.append(Paragraph(
                    "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie for first place.</i>",
                    getSampleStyleSheet()["Normal"]))

        elements.append(spacer_small)
        elements.append(self.luck_title)
        luck_headers = [["Place", "Team", "Manager", "Luck (%)"]]
        elements.append(self.create_data_table(luck_headers, self.weekly_luck_results, self.style_tied_luck,
                                               metric_scores_col_widths, self.tied_luck_bool))

        if self.tied_luck_bool:
            elements.append(Paragraph(
                "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie for first place.</i>",
                getSampleStyleSheet()["Normal"]))

        elements.append(PageBreak())

        series_names = chart_data_list[0]
        points_data = chart_data_list[1]
        efficiency_data = chart_data_list[2]
        luck_data = chart_data_list[3]

        # Remove any zeros from coaching efficiency to make table prettier
        for team in efficiency_data:
            week_index = 0
            for week in team:
                if week[1] == 0.0:
                    del team[week_index]
                week_index += 1

        series_colors = [
            [100, 0, 0, 0, 100],
            [100, 50, 0, 0, 100],
            [100, 100, 0, 0, 100],
            [50, 100, 0, 0, 100],
            [0, 100, 0, 0, 100],
            [0, 100, 50, 0, 100],
            [0, 100, 100, 0, 100],
            [0, 50, 100, 0, 100],
            [0, 0, 100, 0, 100],
            [50, 0, 100, 0, 100],
            [100, 0, 100, 0, 100],
            [100, 0, 50, 0, 100]
        ]

        box_width = 550
        box_height = 240
        chart_width = 490
        chart_height = 150

        # fit y-axis of points table
        scores = [weeks[1] for teams in points_data for weeks in teams]
        points_min = min(scores)
        points_max = max(scores)

        # fit y-axis of coaching efficiency table
        coaching_efficiency_scores = [weeks[1] for teams in efficiency_data for weeks in teams]
        coaching_efficiency_min = min(coaching_efficiency_scores)
        coaching_efficiency_max = max(coaching_efficiency_scores)

        # fit y-axis of luck table
        luck_scores = [weeks[1] for teams in luck_data for weeks in teams]
        luck_min = min(luck_scores)
        luck_max = max(luck_scores)

        points_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width, chart_height)
        points_line_chart.make_title("Weekly Points")
        points_line_chart.make_data(points_data)
        points_line_chart.make_x_axis("Weeks", 0, len(points_data[0]) + 1, 1)
        points_line_chart.make_y_axis("Fantasy Points", points_min, points_max, 10.00)
        points_line_chart.make_series_labels(series_names)

        elements.append(points_line_chart)
        elements.append(spacer_small)

        coaching_efficiency_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width,
                                                            chart_height)
        coaching_efficiency_line_chart.make_title("Weekly Coaching Efficiency")
        coaching_efficiency_line_chart.make_data(efficiency_data)
        coaching_efficiency_line_chart.make_x_axis("Weeks", 0, len(points_data[0]) + 1, 1)
        coaching_efficiency_line_chart.make_y_axis("Coaching Efficiency (%)", coaching_efficiency_min,
                                                   coaching_efficiency_max, 5.00)
        coaching_efficiency_line_chart.make_series_labels(series_names)

        elements.append(coaching_efficiency_line_chart)
        elements.append(spacer_small)

        luck_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width, chart_height)
        luck_line_chart.make_title("Weekly Luck")
        luck_line_chart.make_data(luck_data)
        luck_line_chart.make_x_axis("Weeks", 0, len(points_data[0]) + 1, 1)
        luck_line_chart.make_y_axis("Luck (%)", luck_min, luck_max, 20.00)
        luck_line_chart.make_series_labels(series_names)

        elements.append(luck_line_chart)
        elements.append(spacer_large)

        elements.append(Paragraph(self.report_footer_text, getSampleStyleSheet()["Normal"]))

        if self.league_id == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id") and bool(
                distutils.strtobool(config.get("Data_Settings", "include_team_stats"))):

            temp_stylesheet = getSampleStyleSheet()
            temp_title_style = temp_stylesheet['Heading3']
            temp_text_style = temp_stylesheet["BodyText"]

            elements.append(PageBreak())

            team_index = 0
            for team_name in series_names:
                team_points_average = "{0:.2f}".format(
                    sum([float(i[1]) for i in points_data[team_index]]) / float(len(points_data[team_index])))
                team_efficiency_average = "{0:.2f}".format(
                    sum([float(i[1]) for i in efficiency_data[team_index]]) / float(len(efficiency_data[team_index])))
                team_luck_average = "{0:.2f}".format(
                    sum([float(i[1]) for i in luck_data[team_index]]) / float(len(luck_data[team_index])))

                elements.append(
                    Paragraph('''<para align=center spaceb=3><b>''' + team_name + ''' Team Stats</b></para>''',
                              temp_title_style))
                elements.append(spacer_large)
                elements.append(Paragraph('''<para align=left spaceb=3>Average Points (whole season): ''' + str(
                    team_points_average) + '''</para>''', temp_text_style))
                elements.append(spacer_small)
                elements.append(Paragraph(
                    '''<para align=left spaceb=3>Average Coaching Efficiency (whole season): ''' + str(
                        team_efficiency_average) + '''</para>''', temp_text_style))
                elements.append(spacer_small)
                elements.append(Paragraph('''<para align=left spaceb=3>Average Luck (whole season): ''' + str(
                    team_luck_average) + '''</para>''', temp_text_style))
                elements.append(spacer_small)

                small_box_width = 400
                small_box_height = 175
                small_chart_width = 356
                small_chart_height = 110

                team_points_line_chart = LineChartGenerator([series_colors[team_index]], small_box_width,
                                                            small_box_height, small_chart_width, small_chart_height)
                team_points_line_chart.make_title(team_name + " Weekly Points")
                team_points_line_chart.make_data([points_data[team_index]])
                team_points_line_chart.make_x_axis("Weeks", 0, len(points_data[team_index]) + 1, 1)
                team_points_line_chart.make_y_axis("Fantasy Points", points_min, points_max, 10.00)
                team_points_line_chart.make_series_labels([series_names[team_index]])

                elements.append(team_points_line_chart)
                elements.append(spacer_small)

                team_coaching_efficiency_line_chart = LineChartGenerator([series_colors[team_index]], small_box_width,
                                                                         small_box_height, small_chart_width,
                                                                         small_chart_height)
                team_coaching_efficiency_line_chart.make_title(team_name + " Weekly Coaching Efficiency")
                team_coaching_efficiency_line_chart.make_data([efficiency_data[team_index]])
                team_coaching_efficiency_line_chart.make_x_axis("Weeks", 0, len(points_data[team_index]) + 1, 1)
                team_coaching_efficiency_line_chart.make_y_axis("Coaching Efficiency (%)", 55.00, 95.00, 5.00)
                team_coaching_efficiency_line_chart.make_series_labels([series_names[team_index]])

                elements.append(team_coaching_efficiency_line_chart)
                elements.append(spacer_small)

                team_luck_line_chart = LineChartGenerator([series_colors[team_index]], small_box_width,
                                                          small_box_height, small_chart_width, small_chart_height)
                team_luck_line_chart.make_title(team_name + " Weekly Luck")
                team_luck_line_chart.make_data([luck_data[team_index]])
                team_luck_line_chart.make_x_axis("Weeks", 0, len(points_data[team_index]) + 1, 1)
                team_luck_line_chart.make_y_axis("Luck (%)", -80.00, 90.00, 20.00)
                team_luck_line_chart.make_series_labels([series_names[team_index]])

                elements.append(team_luck_line_chart)
                elements.append(spacer_large)
                elements.append(PageBreak())

                team_index += 1

        print("generating pdf...\n")
        doc.build(elements)
        print("... pdf generated!\n")

        return doc.filename
