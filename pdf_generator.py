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

    def __init__(self, weekly_score_results, coaching_efficiency_results, weekly_luck_results, num_tied_scores, num_tied_efficiencies, num_tied_luck, efficiency_dq_count):

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
            ('TEXTCOLOR', (0, 1), (3, 1), colors.green),
            ('FONT', (0, 1), (3, 1), 'Helvetica-Oblique'),
            ('FONT', (0, 0), (3, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('GRID', (0, 0), (3, 0), 1.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
        ]

        self.style = TableStyle(table_style_list)

        tied_scores_table_style_list = list(table_style_list)
        index = 2
        while (num_tied_scores - 1) > 0:
            tied_scores_table_style_list.append(('TEXTCOLOR', (0, index), (3, index), colors.green))
            tied_scores_table_style_list.append(('FONT', (0, index), (3, index), 'Helvetica-Oblique'))
            num_tied_scores -= 1
            index += 1

        tied_efficiencies_table_style_list = list(table_style_list)
        index = 2
        while (num_tied_efficiencies - 1) > 0:
            tied_efficiencies_table_style_list.append(('TEXTCOLOR', (0, index), (3, index), colors.green))
            tied_efficiencies_table_style_list.append(('FONT', (0, index), (3, index), 'Helvetica-Oblique'))
            num_tied_efficiencies -= 1
            index += 1

        tied_luck_table_style_list = list(table_style_list)
        index = 2
        while (num_tied_luck - 1) > 0:
            tied_luck_table_style_list.append(('TEXTCOLOR', (0, index), (3, index), colors.green))
            tied_luck_table_style_list.append(('FONT', (0, index), (3, index), 'Helvetica-Oblique'))
            num_tied_luck -= 1
            index += 1

        self.style_tied_scores = TableStyle(tied_scores_table_style_list)
        self.style_tied_efficiencies = TableStyle(tied_efficiencies_table_style_list)
        self.style_tied_luck = TableStyle(tied_luck_table_style_list)

        dq_index = len(weekly_score_results) - efficiency_dq_count + 1

        if num_tied_efficiencies > 1:
            efficiencies_dq_table_style_list = list(tied_efficiencies_table_style_list)
        else:
            efficiencies_dq_table_style_list = list(table_style_list)

        if efficiency_dq_count > 0:

            while efficiency_dq_count > 0:
                efficiencies_dq_table_style_list.append(('TEXTCOLOR', (0, dq_index), (3, dq_index), colors.red))
                efficiency_dq_count -= 1
                dq_index += 1

        self.style_efficiency_dqs = TableStyle(efficiencies_dq_table_style_list)

        self.coaching_efficiency_results = coaching_efficiency_results
        self.weekly_score_results = weekly_score_results
        self.weekly_luck_results = weekly_luck_results

    def create_weekly_points_data(self):

        weekly_points_data = [["Place", "Team", "Manager", "Points"]]

        for team in self.weekly_score_results:
            weekly_points_data.append(team)

        return weekly_points_data

    def create_coaching_efficiency_data(self):

        weekly_coaching_data = [["Place", "Team", "Manager", "Coaching Efficiency (%)"]]

        for team in self.coaching_efficiency_results:
            weekly_coaching_data.append(team)

        return weekly_coaching_data

    def create_luck_data(self):

        weekly_luck_data = [["Place", "Team", "Manager", "Luck (%)"]]

        for team in self.weekly_luck_results:
            weekly_luck_data.append(team)

        return weekly_luck_data

    def create_weekly_points_table(self, weekly_points_data, tied_weekly_points_bool):

        weekly_points_table = Table(weekly_points_data, colWidths=[0.75 * inch, 1.75 * inch, 1.75 * inch, 2.00 * inch])

        if tied_weekly_points_bool:
            weekly_points_table.setStyle(self.style_tied_scores)
        else:
            weekly_points_table.setStyle(self.style)

        return weekly_points_table

    def create_coaching_efficiency_table(self, coaching_efficiency_data, tied_coaching_efficiency_bool, efficiency_dq_count):

        coaching_efficiency_table = Table(coaching_efficiency_data, colWidths=[0.75 * inch, 1.75 * inch, 1.75 * inch, 2.00 * inch])

        if tied_coaching_efficiency_bool:
            coaching_efficiency_table.setStyle(self.style_tied_efficiencies)
        else:
            coaching_efficiency_table.setStyle(self.style)

        if efficiency_dq_count > 0:
            coaching_efficiency_table.setStyle(self.style_efficiency_dqs)

        return coaching_efficiency_table

    def create_weekly_luck_table(self, weekly_luck_data, tied_weekly_luck_bool):

        weekly_luck_table = Table(weekly_luck_data, colWidths=[0.75 * inch, 1.75 * inch, 1.75 * inch, 2.00 * inch])

        if tied_weekly_luck_bool:
            weekly_luck_table.setStyle(self.style_tied_luck)
        else:
            weekly_luck_table.setStyle(self.style)

        return weekly_luck_table

    def create_report_title(self, report_title_text):

        report_title = Paragraph('''<para align=center spaceb=3><b>''' + report_title_text + '''</b></para>''', self.text_styleT)

        report_title_data = [[report_title]]
        report_title_table = Table(report_title_data, colWidths=[5 * inch] * 1)

        report_title_table.setStyle(self.title_style)

        return report_title_table

    def create_weekly_points_title(self):

        score_title = Paragraph('''<para align=center spaceb=3><b>Team Score Rankings</b></para>''', self.text_styleH)

        score_title_data = [[score_title]]
        score_title_table = Table(score_title_data, colWidths=[5 * inch] * 1)

        score_title_table.setStyle(self.title_style)

        return score_title_table

    def create_coaching_efficiency_title(self):

        coaching_title = Paragraph('''<para align=center spaceb=3><b>Team Coaching Efficiency Rankings</b></para>''', self.text_styleH)

        coaching_title_data = [[coaching_title]]
        coaching_title_table = Table(coaching_title_data, colWidths=[5 * inch] * 1)

        coaching_title_table.setStyle(self.title_style)

        return coaching_title_table

    def create_luck_title(self):

        luck_title = Paragraph('''<para align=center spaceb=3><b>Team Luck Rankings</b></para>''', self.text_styleH)

        luck_title_data = [[luck_title]]
        luck_title_table = Table(luck_title_data, colWidths=[5 * inch] * 1)

        luck_title_table.setStyle(self.title_style)

        return luck_title_table

    @staticmethod
    def generate_pdf(filename_with_path, report_title, report_footer_text, weekly_points_title, weekly_points_table, coaching_efficiency_title, coaching_efficiency_table, tied_efficiency_bool, luck_title, luck_table, tied_luck_bool, chart_data_list):

        elements = []
        spacer_small = Spacer(1, 0.05 * inch)
        spacer_large = Spacer(1, 0.10 * inch)

        doc = SimpleDocTemplate(filename_with_path, pagesize=LETTER, rightMargin=25, leftMargin=25, topMargin=10, bottomMargin=10)
        doc.pagesize = portrait(LETTER)

        elements.append(report_title)
        elements.append(spacer_large)
        elements.append(weekly_points_title)
        elements.append(weekly_points_table)
        elements.append(spacer_small)
        elements.append(coaching_efficiency_title)
        elements.append(coaching_efficiency_table)

        if tied_efficiency_bool:
            elements.append(spacer_small)
            if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == "5521":
                elements.append(Paragraph("<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*The league commissioner will resolve coaching efficiency ties manually. The winner will be the manager whose team contains the most players who have exceeded their average weekly fantasy points.</i>", getSampleStyleSheet()["Normal"]))
            else:
                elements.append(Paragraph("<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie for first place.</i>", getSampleStyleSheet()["Normal"]))

        elements.append(spacer_small)
        elements.append(luck_title)
        elements.append(luck_table)

        if tied_luck_bool:
            elements.append(Paragraph(
                "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie for first place.</i>",
                getSampleStyleSheet()["Normal"]))

        elements.append(PageBreak())

        series_names = chart_data_list[0]
        points_data = chart_data_list[1]
        efficiency_data = chart_data_list[2]
        luck_data = chart_data_list[3]

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

        points_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width, chart_height)
        points_line_chart.make_title("Weekly Points")
        points_line_chart.make_data(points_data)
        points_line_chart.make_x_axis("Weeks", 0, len(points_data[0]) + 1, 1)
        points_line_chart.make_y_axis("Fantasy Points", points_min, points_max, 10.00)
        points_line_chart.make_series_labels(series_names)

        elements.append(points_line_chart)
        elements.append(spacer_small)

        coaching_efficiency_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width, chart_height)
        coaching_efficiency_line_chart.make_title("Weekly Coaching Efficiency")
        coaching_efficiency_line_chart.make_data(efficiency_data)
        coaching_efficiency_line_chart.make_x_axis("Weeks", 0, len(points_data[0]) + 1, 1)
        coaching_efficiency_line_chart.make_y_axis("Coaching Efficiency (%)", 55.00, 95.00, 5.00)
        coaching_efficiency_line_chart.make_series_labels(series_names)

        elements.append(coaching_efficiency_line_chart)
        elements.append(spacer_small)

        luck_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width, chart_height)
        luck_line_chart.make_title("Weekly Luck")
        luck_line_chart.make_data(luck_data)
        luck_line_chart.make_x_axis("Weeks", 0, len(luck_data[0]) + 1, 1)
        luck_line_chart.make_y_axis("Luck (%)", -80.00, 90.00, 20.00)
        luck_line_chart.make_series_labels(series_names)

        elements.append(luck_line_chart)
        elements.append(spacer_large)

        elements.append(Paragraph(report_footer_text, getSampleStyleSheet()["Normal"]))

        if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id") and bool(distutils.strtobool(config.get("Data_Settings", "include_team_stats"))):

            temp_stylesheet = getSampleStyleSheet()
            temp_title_style = temp_stylesheet['Heading3']
            temp_text_style = temp_stylesheet["BodyText"]

            elements.append(PageBreak())

            team_index = 0
            for team_name in series_names:

                team_points_average = "{0:.2f}".format(sum([float(i[1]) for i in points_data[team_index]]) / float(len(points_data[team_index])))
                team_efficiency_average = "{0:.2f}".format(sum([float(i[1]) for i in efficiency_data[team_index]]) / float(len(efficiency_data[team_index])))
                team_luck_average = "{0:.2f}".format(sum([float(i[1]) for i in luck_data[team_index]]) / float(len(luck_data[team_index])))

                elements.append(Paragraph('''<para align=center spaceb=3><b>''' + team_name + ''' Team Stats</b></para>''', temp_title_style))
                elements.append(spacer_large)
                elements.append(Paragraph('''<para align=left spaceb=3>Average Points (whole season): ''' + str(team_points_average) + '''</para>''', temp_text_style))
                elements.append(spacer_small)
                elements.append(Paragraph('''<para align=left spaceb=3>Average Coaching Efficiency (whole season): ''' + str(team_efficiency_average) + '''</para>''', temp_text_style))
                elements.append(spacer_small)
                elements.append(Paragraph('''<para align=left spaceb=3>Average Luck (whole season): ''' + str(team_luck_average) + '''</para>''', temp_text_style))
                elements.append(spacer_small)

                small_box_width = 400
                small_box_height = 175
                small_chart_width = 356
                small_chart_height = 110

                team_points_line_chart = LineChartGenerator([series_colors[team_index]], small_box_width, small_box_height, small_chart_width, small_chart_height)
                team_points_line_chart.make_title(team_name + " Weekly Points")
                team_points_line_chart.make_data([points_data[team_index]])
                team_points_line_chart.make_x_axis("Weeks", 0, len(points_data[team_index]) + 1, 1)
                team_points_line_chart.make_y_axis("Fantasy Points", 80.00, 190.00, 10.00)
                team_points_line_chart.make_series_labels([series_names[team_index]])

                elements.append(team_points_line_chart)
                elements.append(spacer_small)

                team_coaching_efficiency_line_chart = LineChartGenerator([series_colors[team_index]], small_box_width, small_box_height, small_chart_width, small_chart_height)
                team_coaching_efficiency_line_chart.make_title(team_name + " Weekly Coaching Efficiency")
                team_coaching_efficiency_line_chart.make_data([efficiency_data[team_index]])
                team_coaching_efficiency_line_chart.make_x_axis("Weeks", 0, len(points_data[team_index]) + 1, 1)
                team_coaching_efficiency_line_chart.make_y_axis("Coaching Efficiency (%)", 55.00, 95.00, 5.00)
                team_coaching_efficiency_line_chart.make_series_labels([series_names[team_index]])

                elements.append(team_coaching_efficiency_line_chart)
                elements.append(spacer_small)

                team_luck_line_chart = LineChartGenerator([series_colors[team_index]], small_box_width, small_box_height, small_chart_width, small_chart_height)
                team_luck_line_chart.make_title(team_name + " Weekly Luck")
                team_luck_line_chart.make_data([luck_data[team_index]])
                team_luck_line_chart.make_x_axis("Weeks", 0, len(luck_data[team_index]) + 1, 1)
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
