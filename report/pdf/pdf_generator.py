# written by Wren J.R.
# contributors: Kevin N., Joe M., /u/softsign

from configparser import ConfigParser

from reportlab.graphics.shapes import Line, Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, inch, portrait
from reportlab.lib.enums import TA_CENTER

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image
from reportlab.platypus import PageBreak
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import Spacer
from reportlab.lib.styles import ParagraphStyle


from report.pdf.line_chart_generator import LineChartGenerator
from report.pdf.pie_chart_generator import BreakdownPieDrawing
from report.pdf.utils import get_image

config = ConfigParser()
config.read("config.ini")


class PdfGenerator(object):
    def __init__(self,
                 league_id,
                 week,
                 test_dir,
                 break_ties_bool,
                 report_title_text,
                 standings_title_text,
                 scores_title_text,
                 top_scorers_title_text,
                 coaching_efficiency_title_text,
                 luck_title_text,
                 power_ranking_title_text,
                 zscores_title_text,
                 report_footer_text,
                 report_info_dict,
                 bad_boy_title_text
                 ):

        self.league_id = league_id
        self.week = week
        self.test_dir = test_dir
        self.break_ties_bool = break_ties_bool
        self.current_standings_data = report_info_dict.get("current_standings_data")
        self.score_results_data = report_info_dict.get("score_results_data")
        self.coaching_efficiency_results_data = report_info_dict.get("coaching_efficiency_results_data")
        self.luck_results_data = report_info_dict.get("luck_results_data")
        self.power_ranking_results_data = report_info_dict.get("power_ranking_results_data")
        self.zscore_results_data = report_info_dict.get("zscore_results_data")
        self.bad_boy_results_data = report_info_dict.get("bad_boy_results_data")
        self.num_tied_scores = report_info_dict.get("num_tied_scores")
        self.num_tied_coaching_efficiencies = report_info_dict.get("num_tied_coaching_efficiencies")
        self.num_tied_lucks = report_info_dict.get("num_tied_lucks")
        self.num_tied_power_rankings = report_info_dict.get("num_tied_power_rankings")
        self.num_tied_bad_boys = report_info_dict.get("num_tied_bad_boys")
        self.efficiency_dq_count = report_info_dict.get("efficiency_dq_count")
        self.tied_scores_bool = report_info_dict.get("tied_scores_bool")
        self.tied_coaching_efficiencies_bool = report_info_dict.get("tied_coaching_efficiencies_bool")
        self.tied_lucks_bool = report_info_dict.get("tied_lucks_bool")
        self.tied_power_rankings_bool = report_info_dict.get("tied_power_rankings_bool")
        self.tied_bad_boy_bool = report_info_dict.get("tied_bad_boy_bool")
        self.tie_for_first_score = report_info_dict.get("tie_for_first_score")
        self.tie_for_first_coaching_efficiency = report_info_dict.get("tie_for_first_coaching_efficiency")
        self.tie_for_first_luck = report_info_dict.get("tie_for_first_luck")
        self.tie_for_first_power_ranking = report_info_dict.get("tie_for_first_power_ranking")
        self.tie_for_first_bad_boy = report_info_dict.get("tie_for_first_bad_boy")
        self.num_tied_for_first_scores = report_info_dict.get("num_tied_for_first_scores")
        self.num_tied_for_first_coaching_efficiency = report_info_dict.get("num_tied_for_first_coaching_efficiency")
        self.num_tied_for_first_luck = report_info_dict.get("num_tied_for_first_luck")
        self.num_tied_for_first_power_ranking = report_info_dict.get("num_tied_for_first_power_ranking")
        self.num_tied_for_first_bad_boy = report_info_dict.get("num_tied_for_first_bad_boy")
        self.weekly_points_by_position_data = report_info_dict.get("weekly_points_by_position_data")
        self.season_average_team_points_by_position = report_info_dict.get("season_average_points_by_position")
        self.weekly_top_scorers = report_info_dict.get("weekly_top_scorers")

        # team data for use on team specific stats pages
        self.team_data = report_info_dict.get("team_results")

        # generic document elements
        self.metrics_5_col_widths = [0.75 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch]
        self.metrics_4_col_widths = [1.00 * inch, 2.25 * inch, 2.25 * inch, 2.25 * inch]

        self.power_ranking_col_widths = [1.00 * inch, 2.50 * inch, 2.50 * inch, 1.75 * inch]
        self.line_separator = Drawing(100, 1)
        self.line_separator.add(Line(0, -65, 550, -65, strokeColor=colors.black, strokeWidth=1))
        self.spacer_twentieth_inch = Spacer(1, 0.05 * inch)
        self.spacer_tenth_inch = Spacer(1, 0.10 * inch)
        self.spacer_half_inch = Spacer(1, 0.50 * inch)
        self.spacer_five_inch = Spacer(1, 5.00 * inch)
        self.page_break = PageBreak()

        # Configure style and word wrap
        self.stylesheet = getSampleStyleSheet()
        self.stylesheet.add(ParagraphStyle(name='HC',
                                           parent=self.stylesheet['Normal'],
                                           fontSize=14,
                                           alignment=TA_CENTER,
                                           spaceAfter=6),
                            alias='header-centered')

        self.text_style = self.stylesheet["BodyText"]
        self.text_styleN = self.stylesheet["Normal"]
        self.text_styleD = self.stylesheet["Heading1"]
        self.text_styleT = self.stylesheet["Heading2"]
        self.text_styleH = self.stylesheet["Heading3"]
        self.text_style_title = self.stylesheet["HC"]
        self.text_style.wordWrap = "CJK"

        title_table_style_list = [
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ]

        self.title_style = TableStyle(title_table_style_list)

        # Reportlab fonts: https://github.com/mattjmorrison/ReportLab/blob/master/src/reportlab/lib/fonts.py
        table_style_list = [
            ("TEXTCOLOR", (0, 1), (-1, 1), colors.green),
            ("FONT", (0, 1), (-1, 1), "Helvetica-Oblique"),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
            ("GRID", (0, 0), (-1, 0), 1.5, colors.black),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)
        ]
        self.style = TableStyle(table_style_list)
        self.style_no_highlight = TableStyle(table_style_list[2:])
        red_highlight = table_style_list.copy()
        red_highlight[0] = ("TEXTCOLOR", (0, 1), (-1, 1), colors.darkred)
        self.style_red_highlight = TableStyle(red_highlight)

        boom_bust_table_style_list = [
            ("TEXTCOLOR", (0, 0), (0, -1), colors.green),
            ("TEXTCOLOR", (1, 0), (1, -1), colors.darkred),
            ("FONT", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONT", (0, 1), (-1, 1), "Helvetica-Oblique"),
            ("FONTSIZE", (0, 0), (-1, 0), 16),
            ("FONTSIZE", (0, 1), (-1, -2), 14),
            ("FONTSIZE", (0, -1), (-1, -1), 20),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ]
        self.boom_bust_table_style = TableStyle(boom_bust_table_style_list)

        # report specific document elements
        self.standings_headers = [
            ["Place", "Team", "Manager", "Record", "Points For", "Points Against", "Streak", "Waiver", "Moves",
             "Trades"]]
        self.standings_col_widths = [0.50 * inch, 1.75 * inch, 1.00 * inch, 1.00 * inch, 0.80 * inch, 1.10 * inch,
                                     0.50 * inch, 0.50 * inch, 0.50 * inch, 0.50 * inch]
        self.bad_boy_col_widths = [0.75 * inch, 1.75 * inch, 1.25 * inch, 1.25 * inch, 1.75 * inch, 1.00 * inch]
        self.power_ranking_headers = [["Power Rank", "Team", "Manager", "Season Avg. (Place)"]]
        self.scores_headers = [["Place", "Team", "Manager", "Points", "Season Avg. (Place)"]]
        self.weekly_top_scorer_headers = [["Week", "Team", "Manager", "Score"]]
        self.efficiency_headers = [["Place", "Team", "Manager", "Coaching Efficiency (%)", "Season Avg. (Place)"]]
        self.luck_headers = [["Place", "Team", "Manager", "Luck (%)", "Season Avg. (Place)"]]
        self.bad_boy_headers = [["Place", "Team", "Manager", "Bad Boy Pts", "Worst Offense", "# Offenders"]]
        self.zscores_headers = [["Place", "Team", "Manager", "Z-Score"]]
        self.tie_for_first_footer = "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie(s).</i>"
        self.break_efficiency_ties_footer = "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*The league commissioner will " \
                                            "resolve coaching efficiency ties manually. The tiebreaker goes " \
                                            "to the manager whose team contains the most players who have " \
                                            "exceeded their average weekly fantasy points. If there is still " \
                                            "a tie after that, the manager whose players exceeded their " \
                                            "season average score by the highest cumulative percent wins.</i>"

        self.style_efficiency_dqs = None
        self.style_tied_scores = self.set_tied_values_style(self.num_tied_scores, table_style_list, "scores")
        self.style_tied_efficiencies = self.set_tied_values_style(self.num_tied_coaching_efficiencies, table_style_list,
                                                                  "coaching_efficiency")
        self.style_tied_luck = self.set_tied_values_style(self.num_tied_lucks, table_style_list, "luck")
        self.style_tied_power_rankings = self.set_tied_values_style(self.num_tied_power_rankings, table_style_list,
                                                                    "power_ranking")
        self.style_tied_bad_boy = self.set_tied_values_style(self.num_tied_bad_boys, table_style_list, "bad_boy")

        # options: "document", "section", or None
        self.report_title = self.create_title(report_title_text, element_type="document")
        self.standings_title = self.create_title(standings_title_text, element_type="section", anchor="<a name = page3.html#0></a>")
        self.power_ranking_title = self.create_title(power_ranking_title_text, element_type="section", anchor="<a name = page3.html#1></a>")
        self.zscores_title = self.create_title(zscores_title_text, element_type="section", anchor="<a name = page3.html#2></a>")
        self.scores_title = self.create_title(scores_title_text, element_type="section")
        self.top_scorers_title = self.create_title(top_scorers_title_text, element_type="section")
        self.efficiency_title = self.create_title(coaching_efficiency_title_text, element_type="section")
        self.luck_title = self.create_title(luck_title_text, element_type="section")
        self.bad_boy_title = self.create_title(bad_boy_title_text, element_type="section")
        footer_data = [[self.spacer_five_inch],
                       [Paragraph(report_footer_text, getSampleStyleSheet()["Normal"])]]
        self.report_footer = Table(footer_data, colWidths=7.75 * inch)

    def set_tied_values_style(self, num_tied_values, table_style_list, metric_type):

        num_tied_for_first = num_tied_values
        if metric_type == "scores":
            if not self.tie_for_first_score:
                num_tied_for_first = 0
            else:
                num_tied_for_first = self.num_tied_for_first_scores
        elif metric_type == "coaching_efficiency":
            if not self.tie_for_first_coaching_efficiency:
                num_tied_for_first = 0
            else:
                num_tied_for_first = self.num_tied_for_first_coaching_efficiency
        elif metric_type == "luck":
            if not self.tie_for_first_luck:
                num_tied_for_first = 0
            else:
                num_tied_for_first = self.num_tied_for_first_luck
        elif metric_type == "power_ranking":
            if not self.tie_for_first_power_ranking:
                num_tied_for_first = 0
            else:
                num_tied_for_first = self.num_tied_for_first_power_ranking
        elif metric_type == "bad_boy":
            if not self.tie_for_first_bad_boy:
                num_tied_for_first = 0
            else:
                num_tied_for_first = self.num_tied_for_first_bad_boy

        tied_values_table_style_list = list(table_style_list)
        if metric_type == "scores" and self.break_ties_bool:
            tied_values_table_style_list.append(("TEXTCOLOR", (0, 1), (-1, 1), colors.green))
            tied_values_table_style_list.append(("FONT", (0, 1), (-1, 1), "Helvetica-Oblique"))
        else:
            iterator = num_tied_for_first
            index = 1
            if metric_type == "bad_boy":
                color = colors.darkred
            else:
                color = colors.green
            while iterator > 0:
                tied_values_table_style_list.append(("TEXTCOLOR", (0, index), (-1, index), color))
                tied_values_table_style_list.append(("FONT", (0, index), (-1, index), "Helvetica-Oblique"))
                iterator -= 1
                index += 1

        if metric_type == "coaching_efficiency":
            if self.efficiency_dq_count > 0:
                dq_index = len(self.score_results_data) - self.efficiency_dq_count + 1

                if self.num_tied_coaching_efficiencies > 0:
                    efficiencies_dq_table_style_list = list(tied_values_table_style_list)
                else:
                    efficiencies_dq_table_style_list = list(table_style_list)

                eff_dq_count = self.efficiency_dq_count
                while eff_dq_count > 0:
                    efficiencies_dq_table_style_list.append(("TEXTCOLOR", (0, dq_index), (-1, -1), colors.red))
                    eff_dq_count -= 1
                    dq_index += 1
                self.style_efficiency_dqs = TableStyle(efficiencies_dq_table_style_list)

        return TableStyle(tied_values_table_style_list)

    def create_section(self, elements, title, headers, data, table_style, table_style_ties, col_widths, trailing_element,
                       tied_metric_bool=False, metric_type=None):

        elements.append(title)
        elements.append(self.spacer_tenth_inch)

        if metric_type == "scores":
            if self.num_tied_scores > 0:
                if self.break_ties_bool:
                    self.scores_headers[0].append("Bench Points")
                else:
                    for index, team in enumerate(self.score_results_data):
                        self.score_results_data[index] = team[:-1]
            else:
                for index, team in enumerate(self.score_results_data):
                    self.score_results_data[index] = team[:-1]

        if metric_type == "top_scorers":
            temp_data = []
            for wk in data:
                entry = [
                    wk["week"],
                    wk["team"],
                    wk["manager"],
                    wk["score"]
                ]
                temp_data.append(entry)
                data = temp_data

        data_table = self.create_data_table(headers, data, table_style, table_style_ties, col_widths, tied_metric_bool)

        if metric_type == "coaching_efficiency":
            if self.efficiency_dq_count > 0:
                data_table.setStyle(self.style_efficiency_dqs)
        else:
            data_table.setStyle(table_style_ties)

        elements.append(data_table)
        self.add_tied_metric_footer(elements, metric_type)
        elements.append(trailing_element)

    def add_tied_metric_footer(self, elements, metric_type):

        if metric_type == "scores":
            if self.tied_scores_bool:
                if not self.break_ties_bool:
                    elements.append(self.spacer_twentieth_inch)
                    elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "coaching_efficiency":
            if self.tied_coaching_efficiencies_bool:
                elements.append(self.spacer_twentieth_inch)
                if self.break_ties_bool:
                    elements.append(
                        Paragraph(self.break_efficiency_ties_footer, getSampleStyleSheet()["Normal"]))
                else:
                    elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "luck":
            if self.tied_lucks_bool:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "power_rank":
            if self.tied_power_rankings_bool:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "bad_boy":
            if self.tied_bad_boy_bool:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

    def create_title(self, title_text, title_width=8.5, element_type=None, anchor=""):

        if element_type == "document":
            title_text_style = self.text_styleD
        elif element_type == "section":
            title_text_style = self.text_styleT
        else:
            title_text_style = self.text_styleH

        title = Paragraph('''<para align=center><b>''' + anchor + title_text + '''</b></para>''', title_text_style)
        title_table = Table([[title]], colWidths=[title_width * inch] * 1)
        title_table.setStyle(self.title_style)
        return title_table

    def create_anchored_title(self, title_text, title_width=8.5, element_type=None, anchor=""):

        if element_type == "document":
            title_text_style = self.text_styleD
        elif element_type == "section":
            title_text_style = self.text_styleT
        else:
            title_text_style = self.text_styleH

        title = Paragraph('''<para align=center><b>''' + anchor + title_text + '''</b></para>''', title_text_style)
        title_table = Table([[title]], colWidths=[title_width * inch] * 1)
        title_table.setStyle(self.title_style)
        return title_table

    def create_data_table(self, col_headers, data, table_style=None, table_style_for_ties=None, col_widths=None,
                          tied_metric_bool=False):

        [col_headers.append(item) for item in data]
        table = Table(col_headers, colWidths=col_widths)

        if tied_metric_bool:
            if col_headers[0][-1] == "Bench Points":
                tied_score_col_widths = [0.75 * inch, 1.75 * inch, 1.75 * inch, 1.00 * inch, 1.50 * inch, 1.00 * inch]
                table = Table(col_headers, colWidths=tied_score_col_widths)
            table.setStyle(table_style_for_ties)
        elif table_style:
            table.setStyle(table_style)
        else:
            table.setStyle(self.style)
        return table

    @staticmethod
    def create_line_chart(data, data_length, series_names, chart_title, x_axis_title, y_axis_title, y_step):

        # see https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/ for colors
        series_colors = [
            [0, 100, 66, 0, 100],  # red
            [75, 0, 100, 0, 100],  # green
            [0, 25, 95, 0, 100],  # yellow
            [100, 35, 0, 0, 100],  # blue
            [0, 60, 92, 0, 100],  # orange
            [35, 70, 0, 0, 100],  # purple
            [70, 0, 0, 0, 100],  # cyan
            [0, 100, 0, 0, 100],  # magenta
            [35, 0, 100, 0, 100],  # lime
            [0, 30, 15, 0, 100],  # pink
            [100, 0, 0, 50, 100],  # teal
            [10, 25, 0, 0, 100]  # lavender
        ]

        box_width = 550
        box_height = 240
        chart_width = 490
        chart_height = 150

        # fit y-axis of table
        values = [weeks[1] for teams in data for weeks in teams]
        values_min = min(values)
        values_max = max(values)

        points_line_chart = LineChartGenerator(series_colors, box_width, box_height, chart_width, chart_height)
        points_line_chart.make_title(chart_title)
        points_line_chart.make_data(data)
        points_line_chart.make_x_axis(x_axis_title, 0, data_length + 1, 1)
        points_line_chart.make_y_axis(y_axis_title, values_min, values_max, y_step)
        points_line_chart.make_series_labels(series_names)

        return points_line_chart

    @staticmethod
    def get_image(path, width=1 * inch):
        img = ImageReader(path)
        iw, ih = img.getSize()
        aspect = ih / float(iw)
        return Image(path, width=width, height=(width * aspect))

    def create_team_stats_pages(self, doc_elements, weekly_team_data_by_position, season_average_team_data_by_position):
        team_number = 1
        alphabetical_teams = sorted(weekly_team_data_by_position, key=lambda team_info: team_info[0])
        for team in alphabetical_teams:

            doc_elements.append(self.create_title("<i>" + team[0] + "</i>", element_type="section"))
            labels = []
            weekly_data = []
            season_data = [x[1] for x in season_average_team_data_by_position.get(team[0])]
            for week in team[1]:
                labels.append(week[0])
                weekly_data.append(week[1])
            team_table = Table(
                [[self.create_title("Weekly Points by Position", title_width=2.00),
                  self.create_title("Season Average Points by Position", title_width=2.00)],
                 [BreakdownPieDrawing(labels, weekly_data),
                  BreakdownPieDrawing(labels, season_data)]],
                colWidths=[4.25 * inch, 4.25 * inch],
                style=TableStyle([
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, 0), "MIDDLE")
                ]))
            doc_elements.append(team_table)

            offending_players = []
            starting_players = []
            player_info = self.team_data[team[0]]["players"]
            for player in player_info:
                if player["bad_boy_points"] > 0:
                    offending_players.append(player)
                if player["selected_position"] != "BN":
                    starting_players.append(player)

            doc_elements.append(self.spacer_half_inch)
            doc_elements.append(self.create_title("Whodunnit?", 8.5, "section"))
            doc_elements.append(self.spacer_tenth_inch)
            offending_players = sorted(offending_players, key=lambda x: x["bad_boy_points"], reverse=True)
            offending_players_data = []
            for player in offending_players:
                offending_players_data.append([player["name"], player["bad_boy_points"], player["bad_boy_crime"]])
            # if there are no offending players, add a dummy row to avoid breaking
            if not offending_players_data:
                offending_players_data = [["N/A", "N/A", "N/A"]]
            bad_boys_table = self.create_data_table([["Starting Player", "Bad Boy Points", "Worst Offense"]],
                                                    offending_players_data,
                                                    self.style_red_highlight,
                                                    self.style_tied_bad_boy,
                                                    [2.50 * inch, 2.50 * inch, 2.75 * inch],
                                                    False)

            starting_players = sorted(starting_players, key=lambda x: x["fantasy_points"], reverse=True)
            best_weekly_player = starting_players[0]
            worst_weekly_player = starting_players[-1]
          
            doc_elements.append(bad_boys_table)

            doc_elements.append(self.spacer_tenth_inch)

            best_player_headshot = get_image(best_weekly_player["headshot_url"], self.test_dir, self.week, 1 * inch)
            worst_player_headshot = get_image(worst_weekly_player["headshot_url"], self.test_dir, self.week, 1 * inch)

            data = [["BOOOOOOOOM", "...b... U... s... T"],
                    [best_weekly_player["name"] + " -- " + best_weekly_player["nfl_team"],
                     worst_weekly_player["name"] + " -- " + worst_weekly_player["nfl_team"]],
                    [best_player_headshot, worst_player_headshot],
                    [best_weekly_player["fantasy_points"], worst_weekly_player["fantasy_points"]]]
            table = Table(data, colWidths=4.0 * inch)
            table.setStyle(self.boom_bust_table_style)
            doc_elements.append(self.spacer_half_inch)
            doc_elements.append(self.create_title("Boom... or Bust", 8.5, "section"))
            doc_elements.append(self.spacer_tenth_inch)
            doc_elements.append(table)

            if team_number == len(alphabetical_teams):
                doc_elements.append(Spacer(1, 1.75 * inch), )
            else:
                doc_elements.append(self.page_break)
            # elif team_number % 2 == 1:
            #     doc_elements.append(self.line_separator)
            #     doc_elements.append(self.spacer_inch)
            # elif team_number % 2 == 0:
            #     doc_elements.append(self.page_break)
            team_number += 1

    def generate_pdf(self, filename_with_path, line_chart_data_list):

        elements = []
        # doc = SimpleDocTemplate(filename_with_path, pagesize=LETTER, rightMargin=25, leftMargin=25, topMargin=10,
        #                         bottomMargin=10)
        doc = SimpleDocTemplate(filename_with_path, pagesize=LETTER, rightMargin=25, leftMargin=25, topMargin=10,
                            bottomMargin=10)
        doc.pagesize = portrait(LETTER)

        # document title
        elements.append(self.report_title)
        elements.append(self.spacer_tenth_inch)

        elements.append(Paragraph('<a href = page3.html#0>League Standings</a>', self.text_styleH))  # Linking the anchor to reference 0
        elements.append(Paragraph('<a href = page3.html#1>Power Rankings</a>', self.text_styleH))  # Linking the anchor to reference 1
        elements.append(Paragraph('<a href = page3.html#2>Z-Score Rankings</a>', self.text_styleH))  # Linking the anchor to reference 2

        # elements.append(Paragraph('<a name = page3.html#0></a> 1. First Title', self.text_styleH))  # Creating anchor with reference 0
        # elements.append(Paragraph('<a name = page3.html#1></a><br/> 1.1. First Subtitle', self.text_styleH))  # Creating anchor with reference 1

        elements.append(self.page_break)

        # standings
        # par = Paragraph('<a name = page3.html#0></a><b>League Standings</b>', self.text_style_title)
        # tab = Table([[par]], colWidths=[8.5 * inch] * 1)
        # tab.setStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")])
        # elements.append(tab)  # Creating anchor with reference 0
        # t1 = self.create_anchored_title("League Standings", element_type="section", anchor="<a name = page3.html#0></a>")
        self.create_section(elements, self.standings_title, self.standings_headers, self.current_standings_data,
                            self.style, self.style, self.standings_col_widths, self.spacer_tenth_inch)

        # power ranking
        # elements.append(Paragraph('<a name = page3.html#1></a>', self.text_styleH))  # Creating anchor with reference 1
        self.create_section(elements, self.power_ranking_title, self.power_ranking_headers,
                            self.power_ranking_results_data, self.style, self.style_tied_power_rankings,
                            self.power_ranking_col_widths, self.spacer_twentieth_inch,
                            tied_metric_bool=self.tied_power_rankings_bool, metric_type="power_rank")

        # zscores
        self.create_section(elements, self.zscores_title, self.zscores_headers, self.zscore_results_data,
                            self.style, self.style_tied_power_rankings, self.metrics_4_col_widths, self.page_break,
                            tied_metric_bool=False, metric_type="zscore")

        # scores
        self.create_section(elements, self.scores_title, self.scores_headers, self.score_results_data, self.style,
                            self.style, self.metrics_5_col_widths, self.spacer_twentieth_inch,
                            tied_metric_bool=self.tied_scores_bool, metric_type="scores")

        # coaching efficiency
        self.create_section(elements, self.efficiency_title, self.efficiency_headers,
                            self.coaching_efficiency_results_data, self.style, self.style_tied_efficiencies,
                            self.metrics_5_col_widths, self.spacer_twentieth_inch,
                            tied_metric_bool=self.tied_coaching_efficiencies_bool, metric_type="coaching_efficiency")

        # luck
        self.create_section(elements, self.luck_title, self.luck_headers, self.luck_results_data, self.style,
                            self.style_tied_luck, self.metrics_5_col_widths, self.page_break,
                            tied_metric_bool=self.tied_lucks_bool, metric_type="luck")

        # weekly top scorers
        self.create_section(elements, self.top_scorers_title, self.weekly_top_scorer_headers, self.weekly_top_scorers,
                            self.style_no_highlight, self.style_no_highlight, self.metrics_4_col_widths, self.spacer_twentieth_inch,
                            tied_metric_bool=self.tied_scores_bool, metric_type="top_scorers")

        # bad boy rankings
        self.create_section(elements, self.bad_boy_title, self.bad_boy_headers, self.bad_boy_results_data,
                            self.style, self.style_tied_bad_boy, self.bad_boy_col_widths, self.page_break,
                            tied_metric_bool=self.tied_bad_boy_bool, metric_type="bad_boy")

        series_names = line_chart_data_list[0]
        points_data = line_chart_data_list[2]
        efficiency_data = line_chart_data_list[3]
        luck_data = line_chart_data_list[4]
        zscore_data = line_chart_data_list[5]

        # Remove any zeros from coaching efficiency to make table prettier
        for team in efficiency_data:
            week_index = 0
            for week in team:
                if len(team) > 1:
                    if week[1] == 0.0:
                        del team[week_index]
                week_index += 1

        # create line charts for points, coaching efficiency, and luck
        elements.append(self.create_line_chart(points_data, len(points_data[0]), series_names, "Weekly Points", "Weeks",
                                               "Fantasy Points", 10.00))
        elements.append(self.spacer_twentieth_inch)
        elements.append(
            self.create_line_chart(efficiency_data, len(points_data[0]), series_names, "Weekly Coaching Efficiency",
                                   "Weeks", "Coaching Efficiency (%)", 5.00))
        elements.append(self.spacer_twentieth_inch)
        elements.append(
            self.create_line_chart(luck_data, len(points_data[0]), series_names, "Weekly Luck", "Weeks", "Luck (%)",
                                   20.00))
        elements.append(self.spacer_tenth_inch)
        elements.append(self.page_break)

        # # Exclude z-score time series data unless it is determined to be relevant
        # elements.append(self.create_line_chart(zscore_data, len(points_data[0]), series_names, "Weekly Z-Score",
        #                                        "Weeks", "Z-Score", 5.00))
        # elements.append(self.spacer_tenth_inch)
        # elements.append(self.page_break)

        # dynamically build additional pages for individual team stats
        self.create_team_stats_pages(elements, self.weekly_points_by_position_data,
                                     self.season_average_team_points_by_position)

        elements.append(self.page_break)
        elements.append(self.report_footer)

        # build pdf
        print("generating PDF ({})...".format(filename_with_path.split("/")[-1]))
        doc.build(elements)

        return doc.filename
