__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import copy
import logging
import os
import urllib.request
from configparser import ConfigParser
from urllib.error import URLError

from reportlab.graphics.shapes import Line, Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.fonts import tt2ps
from reportlab.lib.pagesizes import LETTER, portrait
from reportlab.lib.pagesizes import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image
from reportlab.platypus import PageBreak
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import Spacer
from reportlab.rl_settings import canvas_basefontname as bfn
from reportlab.platypus.flowables import KeepTogether

from dao.base import BaseLeague, BaseTeam, BasePlayer
from report.data import ReportData
from report.logger import get_logger
from report.pdf.charts.line import LineChartGenerator
from report.pdf.charts.pie import BreakdownPieDrawing

logger = get_logger(__name__, propagate=False)

# suppress verbose PIL debug logging
logging.getLogger("PIL.PngImagePlugin").setLevel(level=logging.INFO)


def get_image(url, data_dir, week, width=1 * inch):
    headshots_dir = os.path.join(data_dir, "week_" + str(week), "player_headshots")

    if not os.path.exists(headshots_dir):
        os.makedirs(headshots_dir)

    if url:
        img_name = url.split("/")[-1]
        local_img_path = os.path.join(headshots_dir, img_name)

        if not os.path.exists(local_img_path):
            try:
                urllib.request.urlretrieve(url, local_img_path)
            except URLError:
                logger.error("Unable to retrieve player headshot at url {}".format(url))
                local_img_path = os.path.join("resources", "images", "photo-not-available.jpeg")
    else:
        logger.error("No available URL for player.")
        local_img_path = os.path.join("resources", "images", "photo-not-available.jpeg")

    img = ImageReader(local_img_path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)

    scaled_img = Image(local_img_path, width=width, height=(width * aspect))

    return scaled_img


class PdfGenerator(object):
    def __init__(self,
                 config,  # type: ConfigParser
                 league,  # type: BaseLeague
                 playoff_prob_sims,
                 report_title_text,
                 report_footer_text,
                 report_data  # type: ReportData
                 ):

        # report configuration
        self.config = config
        self.league_id = league.league_id
        self.playoff_slots = int(league.num_playoff_slots)
        self.num_regular_season_weeks = int(league.num_regular_season_weeks)
        self.week_for_report = league.week_for_report
        self.data_dir = os.path.join(league.data_dir, str(league.season), league.league_id)
        self.break_ties = report_data.break_ties
        self.playoff_prob_sims = playoff_prob_sims
        self.num_coaching_efficiency_dqs = report_data.num_coaching_efficiency_dqs

        # data for report
        self.report_data = report_data
        self.data_for_scores = report_data.data_for_scores
        self.data_for_coaching_efficiency = report_data.data_for_coaching_efficiency
        self.data_for_luck = report_data.data_for_luck
        self.data_for_power_rankings = report_data.data_for_power_rankings
        self.data_for_z_scores = report_data.data_for_z_scores
        self.data_for_bad_boy_rankings = report_data.data_for_bad_boy_rankings
        self.data_for_beef_rankings = report_data.data_for_beef_rankings
        self.data_for_weekly_points_by_position = report_data.data_for_weekly_points_by_position
        self.data_for_season_average_team_points_by_position = report_data.data_for_season_avg_points_by_position
        self.data_for_season_weekly_top_scorers = report_data.data_for_season_weekly_top_scorers
        self.data_for_season_weekly_highest_ce = report_data.data_for_season_weekly_highest_ce

        # table of contents
        self.toc = TableOfContents(self.config, self.break_ties)

        # team data for use on team specific stats pages
        self.teams_results = report_data.teams_results

        # table column widths
        self.widths_4_cols_2 = [1.00 * inch, 2.25 * inch, 2.25 * inch, 2.25 * inch]
        self.widths_4_cols_2 = [1.00 * inch, 2.50 * inch, 2.50 * inch, 1.75 * inch]
        self.widths_4_cols_3 = [1.00 * inch, 2.50 * inch, 2.00 * inch, 2.25 * inch]
        self.widths_4_cols_4 = [0.50 * inch, 2.25 * inch, 1.75 * inch, 3.25 * inch]
        self.widths_5_cols_1 = [0.45 * inch, 1.95 * inch, 1.85 * inch, 1.75 * inch, 1.75 * inch]
        self.widths_6_cols_1 = [0.75 * inch, 1.75 * inch, 1.75 * inch, 1.00 * inch, 1.50 * inch, 1.00 * inch]
        self.widths_6_cols_2 = [0.75 * inch, 1.75 * inch, 1.25 * inch, 1.00 * inch, 2.00 * inch, 1.00 * inch]
        self.widths_7_cols_1 = [0.50 * inch, 1.75 * inch, 1.50 * inch, 0.75 * inch, 1.50 * inch, 0.75 * inch,
                                1.00 * inch]
        self.widths_10_cols_1 = [0.45 * inch, 1.80 * inch, 1.05 * inch, 1.00 * inch, 0.80 * inch, 1.05 * inch,
                                 0.50 * inch, 0.50 * inch, 0.50 * inch, 0.50 * inch]
        self.widths_n_cols_1 = [1.55 * inch, 1.00 * inch, 0.90 * inch, 0.65 * inch, 0.65 * inch] + \
                               [round(3.4 / self.playoff_slots, 2) * inch] * self.playoff_slots

        self.line_separator = Drawing(100, 1)
        self.line_separator.add(Line(0, -65, 550, -65, strokeColor=colors.black, strokeWidth=1))
        self.spacer_twentieth_inch = Spacer(1, 0.05 * inch)
        self.spacer_tenth_inch = Spacer(1, 0.10 * inch)
        self.spacer_quarter_inch = Spacer(1, 0.25 * inch)
        self.spacer_half_inch = Spacer(1, 0.50 * inch)
        self.spacer_five_inch = Spacer(1, 5.00 * inch)

        # configure text styles
        self.stylesheet = getSampleStyleSheet()
        self.stylesheet.add(ParagraphStyle(name="HC",
                                           parent=self.stylesheet["Normal"],
                                           fontSize=14,
                                           alignment=TA_CENTER,
                                           spaceAfter=6),
                            alias="header-centered")
        self.text_style_title = self.stylesheet["HC"]
        self.text_style = self.stylesheet["BodyText"]
        self.text_style_normal = self.stylesheet["Normal"]
        self.text_style_h1 = self.stylesheet["Heading1"]
        self.text_style_h2 = self.stylesheet["Heading2"]
        self.text_style_h3 = self.stylesheet["Heading3"]
        self.text_style_h4 = self.stylesheet["Heading4"]
        self.text_style_h5 = self.stylesheet["Heading5"]
        self.text_style_h6 = self.stylesheet["Heading6"]
        self.text_style_subtitles = ParagraphStyle(name="subtitles",
                                                   parent=self.text_style_normal,
                                                   fontName=tt2ps(bfn, 1, 1),
                                                   fontSize=8,
                                                   leading=10,
                                                   spaceBefore=0,
                                                   spaceAfter=0)
        self.text_style_invisible = ParagraphStyle(name="invisible",
                                                   parent=self.text_style_normal,
                                                   fontName=tt2ps(bfn, 1, 1),
                                                   fontSize=0,
                                                   textColor=colors.white,
                                                   leading=10,
                                                   spaceBefore=0,
                                                   spaceAfter=0)

        # configure word wrap
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
        style_left_alight_right_col_list = copy.deepcopy(table_style_list)
        style_left_alight_right_col_list.append(("ALIGN", (-1, 1), (-1, -1), "LEFT"))
        self.style_left_alighn_right_col = TableStyle(style_left_alight_right_col_list)
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

        ordinal_dict = {
            1: "1st", 2: "2nd", 3: "3rd", 4: "4th",
            5: "5th", 6: "6th", 7: "7th", 8: "8th",
            9: "9th", 10: "10th", 11: "11th", 12: "12th",
            13: "13th", 14: "14th", 15: "15th", 16: "16th",
            17: "17th", 18: "18th", 19: "19th", 20: "20th"
        }
        ordinal_list = []
        playoff_places = 1
        while playoff_places <= self.playoff_slots:
            ordinal_list.append(ordinal_dict[playoff_places])
            playoff_places += 1
        self.playoff_probs_headers = [
            ["Team", "Manager", "Record", "Playoffs", "Needed"] + ordinal_list
        ]
        self.power_ranking_headers = [["Power Rank", "Team", "Manager", "Season Avg. (Place)"]]
        self.scores_headers = [["Place", "Team", "Manager", "Points", "Season Avg. (Place)"]]
        self.weekly_top_scorer_headers = [["Week", "Team", "Manager", "Score"]]
        self.weekly_highest_ce_headers = [["Week", "Team", "Manager", "Coaching Efficiency (%)"]]
        self.efficiency_headers = [["Place", "Team", "Manager", "Coaching Efficiency (%)", "Season Avg. (Place)"]]
        self.luck_headers = [["Place", "Team", "Manager", "Luck (%)", "Season Avg. (Place)"]]
        self.bad_boy_headers = [["Place", "Team", "Manager", "Bad Boy Pts", "Worst Offense", "# Offenders"]]
        self.beef_headers = [["Place", "Team", "Manager", "TABBU(s)"]]
        self.zscores_headers = [["Place", "Team", "Manager", "Z-Score"]]
        self.tie_for_first_footer = "<i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*Tie(s).</i>"

        self.style_efficiency_dqs = None
        self.style_tied_scores = self.set_tied_values_style(self.report_data.ties_for_scores, table_style_list,
                                                            "scores")
        self.style_tied_efficiencies = self.set_tied_values_style(self.report_data.ties_for_coaching_efficiency,
                                                                  table_style_list,
                                                                  "coaching_efficiency")
        self.style_tied_luck = self.set_tied_values_style(self.report_data.ties_for_luck, table_style_list, "luck")
        self.style_tied_power_rankings = self.set_tied_values_style(self.report_data.ties_for_power_rankings,
                                                                    table_style_list,
                                                                    "power_ranking")
        self.style_tied_bad_boy = self.set_tied_values_style(self.report_data.ties_for_power_rankings, table_style_list,
                                                             "bad_boy")
        self.style_tied_beef = self.set_tied_values_style(self.report_data.ties_for_beef_rankings,
                                                          style_left_alight_right_col_list, "beef")

        # options: "document", "section", or None
        self.report_title = self.create_title(report_title_text, element_type="document")

        footer_data = [[self.spacer_five_inch],
                       [Paragraph(report_footer_text, getSampleStyleSheet()["Normal"])]]
        self.report_footer = Table(footer_data, colWidths=7.75 * inch)

    # noinspection PyUnusedLocal
    @staticmethod
    def add_page_number(canvas, doc):
        """
        Add the page number
        """
        page_num = canvas.getPageNumber()
        text = "Page %s" % page_num
        canvas.drawRightString(4.45 * inch, 0.25 * inch, text)

    def add_page_break(self):
        self.toc.add_toc_page()
        return PageBreak()

    def set_tied_values_style(self, num_ties, table_style_list, metric_type):

        num_first_places = num_ties
        if metric_type == "scores":
            if not self.report_data.num_first_place_for_score > 0:
                num_first_places = 0
            else:
                num_first_places = self.report_data.num_first_place_for_score
        elif metric_type == "coaching_efficiency":
            if not self.report_data.num_first_place_for_coaching_efficiency > 0:
                num_first_places = 0
            else:
                num_first_places = self.report_data.num_first_place_for_coaching_efficiency
        elif metric_type == "luck":
            if not self.report_data.num_first_place_for_luck > 0:
                num_first_places = 0
            else:
                num_first_places = self.report_data.num_first_place_for_luck
        elif metric_type == "power_ranking":
            if not self.report_data.ties_for_first_for_power_rankings > 0:
                num_first_places = 0
            else:
                num_first_places = self.report_data.ties_for_first_for_power_rankings
        elif metric_type == "bad_boy":
            if not self.report_data.num_first_place_for_bad_boy_rankings > 0:
                num_first_places = 0
            else:
                num_first_places = self.report_data.num_first_place_for_bad_boy_rankings
        elif metric_type == "beef":
            if not self.report_data.num_first_place_for_beef_rankings > 0:
                num_first_places = 0
            else:
                num_first_places = self.report_data.num_first_place_for_beef_rankings

        tied_values_table_style_list = list(table_style_list)
        if metric_type == "scores" and self.break_ties:
            tied_values_table_style_list.append(("TEXTCOLOR", (0, 1), (-1, 1), colors.green))
            tied_values_table_style_list.append(("FONT", (0, 1), (-1, 1), "Helvetica-Oblique"))
        else:
            iterator = num_first_places
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
            if self.num_coaching_efficiency_dqs > 0:
                dq_index = len(self.data_for_scores) - self.num_coaching_efficiency_dqs + 1

                if self.report_data.ties_for_coaching_efficiency > 0:
                    efficiencies_dq_table_style_list = list(tied_values_table_style_list)
                else:
                    efficiencies_dq_table_style_list = list(table_style_list)

                eff_dq_count = self.num_coaching_efficiency_dqs
                while eff_dq_count > 0:
                    efficiencies_dq_table_style_list.append(("TEXTCOLOR", (0, dq_index), (-1, -1), colors.red))
                    eff_dq_count -= 1
                    dq_index += 1
                self.style_efficiency_dqs = TableStyle(efficiencies_dq_table_style_list)

        return TableStyle(tied_values_table_style_list)

    def create_section(self, elements, title_text, headers, data, table_style, table_style_ties, col_widths,
                       subtitle_text=None, row_heights=None, tied_metric=False, metric_type=None):

        title = self.create_title(title_text, element_type="section",
                                  anchor="<a name = page.html#" + str(self.toc.get_current_anchor()) + "></a>",
                                  subtitle_text=subtitle_text)
        self.toc.add_metric_section(title_text)

        if metric_type == "standings":
            font_reduction = 0
            for x in range(1, (len(data) % 12) + 1, 4):
                font_reduction += 1
            table_style.add("FONTSIZE", (0, 0), (-1, -1), 10 - font_reduction)
            if self.report_data.is_faab:
                headers[0][7] = "FAAB"

        if metric_type == "playoffs":
            font_reduction = 0
            for x in range(1, (len(data[0][5:]) % 6) + 2):
                font_reduction += 1
            table_style.add("FONTSIZE", (0, 0), (-1, -1), 10 - font_reduction)

        if metric_type == "scores":
            if self.break_ties and self.report_data.ties_for_scores > 0:
                self.scores_headers[0].append("Bench Points")
            else:
                for index, team in enumerate(self.data_for_scores):
                    self.data_for_scores[index] = team[:-1]

        if metric_type == "coaching_efficiency":
            if self.break_ties and self.report_data.ties_for_coaching_efficiency > 0:
                self.efficiency_headers[0][3] = "CE (%)"
                self.efficiency_headers[0].extend(["# > Avg.", "Sum % > Avg."])
            else:
                for index, team in enumerate(self.data_for_coaching_efficiency):
                    self.data_for_coaching_efficiency[index] = team

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

        if metric_type == "highest_ce":
            temp_data = []
            for wk in data:
                # noinspection PyTypeChecker
                entry = [
                    wk["week"],
                    wk["team"],
                    wk["manager"],
                    wk["ce"]
                ]
                temp_data.append(entry)
                data = temp_data

        if metric_type == "beef":
            cow_icon = self.get_image(os.path.join("resources", "images", "cow.png"), width=0.20 * inch)
            beef_icon = self.get_image(os.path.join("resources", "images", "beef.png"), width=0.20 * inch)
            half_beef_icon = self.get_image(os.path.join("resources", "images", "beef-half.png"), width=0.10 * inch)
            # lowest_tabbu = float(data[-1][3])
            # mod_5_remainder = lowest_tabbu % 5
            # beef_count_floor = lowest_tabbu - mod_5_remainder

            for team in data:
                num_cows = int(float(team[3]) // 5) - 1  # subtract one to make sure there are always beef icons
                num_beefs = int(float(team[3]) / 0.5) - (num_cows * 10)
                # num_beefs = int((float(team[3]) - beef_count_floor) / 0.5) - (num_cows * 10)

                if num_cows > 0:
                    beefs = [cow_icon] * num_cows
                else:
                    num_beefs = num_beefs - 10
                    beefs = []

                if num_beefs % 2 == 0:
                    beefs += [beef_icon] * int((num_beefs / 2))
                else:
                    beefs += [beef_icon] * int((num_beefs / 2))
                    beefs.append(half_beef_icon)

                beefs.insert(0, team[-1] + " ")
                beefs = [beefs]
                beefs_col_widths = [0.20 * inch] * (num_beefs if num_beefs > 0 else num_cows)
                beefs_col_widths.insert(0, 0.50 * inch)
                beefs_table = Table(beefs, colWidths=beefs_col_widths, rowHeights=0.25 * inch)
                if data.index(team) == 0:
                    beefs_table_style = TableStyle([("TEXTCOLOR", (0, 0), (-1, -1), colors.green),
                                                    ("FONT", (0, 0), (-1, -1), "Helvetica-Oblique")])
                    beefs_table.setStyle(beefs_table_style)
                team[-1] = beefs_table

        data_table = self.create_data_table(headers, data, table_style, table_style_ties, col_widths, row_heights,
                                            tied_metric)

        if metric_type == "coaching_efficiency":
            if self.num_coaching_efficiency_dqs > 0:
                data_table.setStyle(self.style_efficiency_dqs)
        else:
            data_table.setStyle(table_style_ties)

        table_with_title = KeepTogether(Table(
            [[title], [data_table]],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")])
        ))

        elements.append(table_with_title)
        self.add_tied_metric_footer(elements, metric_type)

    def add_tied_metric_footer(self, elements, metric_type):

        if metric_type == "scores":
            if self.report_data.ties_for_scores > 0:
                if not self.break_ties:
                    elements.append(self.spacer_twentieth_inch)
                    elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "coaching_efficiency":
            if self.report_data.ties_for_coaching_efficiency > 0:
                if not self.break_ties:
                    elements.append(self.spacer_twentieth_inch)
                    elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "luck":
            if self.report_data.ties_for_luck > 0:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "power_ranking":
            if self.report_data.ties_for_power_rankings > 0:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "bad_boy":
            if self.report_data.ties_for_bad_boy_rankings > 0:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

        elif metric_type == "beef":
            if self.report_data.ties_for_beef_rankings > 0:
                elements.append(Paragraph(self.tie_for_first_footer, getSampleStyleSheet()["Normal"]))

    def create_title(self, title_text, title_width=8.5, element_type=None, anchor="", subtitle_text=None):

        if element_type == "document":
            title_text_style = self.text_style_h1
        elif element_type == "section":
            title_text_style = self.text_style_h2
        elif element_type == "chart":
            title_text_style = self.text_style_invisible
        else:
            title_text_style = self.text_style_h3

        title = Paragraph('''<para align=center><b>''' + anchor + title_text + '''</b></para>''', title_text_style)

        rows = [[title]]

        if subtitle_text:
            if not isinstance(subtitle_text, list):
                subtitle_text = [subtitle_text]

            text = "<br/>".join(subtitle_text)
            subtitle = Paragraph('''<para align=center>''' + text + '''</para>''', self.text_style_subtitles)
            rows.append([subtitle])

        title_table = Table(rows, colWidths=[title_width * inch] * 1)
        title_table.setStyle(self.title_style)
        return title_table

    def create_anchored_title(self, title_text, title_width=8.5, element_type=None, anchor=""):

        if element_type == "document":
            title_text_style = self.text_style_h1
        elif element_type == "section":
            title_text_style = self.text_style_h2
        else:
            title_text_style = self.text_style_h3

        title = Paragraph('''<para align=center><b>''' + anchor + title_text + '''</b></para>''', title_text_style)
        title_table = Table([[title]], colWidths=[title_width * inch] * 1)
        title_table.setStyle(self.title_style)
        return title_table

    def create_data_table(self, col_headers, data, table_style=None, table_style_for_ties=None, col_widths=None,
                          row_heights=None, tied_metric=False):

        [col_headers.append(item) for item in data]

        if tied_metric:
            if col_headers[0][-1] == "Bench Points":
                table = Table(col_headers, colWidths=self.widths_6_cols_1)
            elif col_headers[0][-1] == "Sum % > Avg.":
                table = Table(col_headers, colWidths=self.widths_7_cols_1)
            else:
                table = Table(col_headers, colWidths=col_widths, rowHeights=row_heights)
            table.setStyle(table_style_for_ties)
        else:
            table = Table(col_headers, colWidths=col_widths, rowHeights=row_heights)

        if table_style:
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
            [10, 25, 0, 0, 100],  # lavender
            [0, 100, 100, 50, 100],  # maroon
            [0, 35, 75, 33, 100],  # brown
            [0, 0, 100, 50, 100],  # olive
            [100, 100, 0, 50, 100],  # navy
            [33, 0, 23, 0, 100],  # mint
            [0, 30, 15, 0, 100],  # pink
            [0, 15, 30, 0, 100],  # apricot
            [5, 10, 30, 0, 100]  # beige
        ]

        box_width = 550
        box_height = 240
        chart_width = 490
        chart_height = 150

        # fit y-axis of table
        values = [weeks[1] for teams in data for weeks in teams]
        values_min = min(values)
        values_max = max(values)

        points_line_chart = LineChartGenerator(
            data,
            chart_title,
            [x_axis_title, 0, data_length + 1, 1],
            [y_axis_title, values_min, values_max, y_step],
            series_names,
            series_colors,
            box_width,
            box_height,
            chart_width,
            chart_height
        )
        # points_line_chart.make_title(chart_title)
        # points_line_chart.make_data(data)
        # points_line_chart.make_x_axis(x_axis_title, 0, data_length + 1, 1)
        # points_line_chart.make_y_axis(y_axis_title, values_min, values_max, y_step)
        # points_line_chart.make_series_labels(series_names)

        return points_line_chart

    @staticmethod
    def get_image(path, width=1 * inch):
        img = ImageReader(path)
        iw, ih = img.getSize()
        aspect = ih / float(iw)
        return Image(path, width=width, height=(width * aspect))

    def create_team_stats_pages(self, doc_elements, weekly_team_data_by_position, season_average_team_data_by_position):

        # reorganize weekly_team_data_by_position to alphabetical order by team name
        alphabetical_teams = []
        for team in sorted(self.teams_results.values(), key=lambda x: x.name):
            for team_data in weekly_team_data_by_position:
                if team.team_id == team_data[0]:
                    alphabetical_teams.append(team_data)

        for team in alphabetical_teams:
            team_id = team[0]
            team_weekly_points_by_position = team[1]
            team_result = self.teams_results[team_id]  # type: BaseTeam
            player_info = team_result.roster

            if self.config.getboolean(
                    "Report", "team_points_by_position_charts") or self.config.getboolean(
                    "Report", "team_bad_boy_stats") or self.config.getboolean(
                    "Report", "team_beef_stats") or self.config.getboolean(
                    "Report", "team_boom_or_bust"):
                title = self.create_title("<i>" + team_result.name + "</i>", element_type="section",
                                          anchor="<a name = page.html#" + str(self.toc.get_current_anchor()) + "></a>")
                self.toc.add_team_section(team_result.name)

                doc_elements.append(title)

            if self.config.getboolean("Report", "team_points_by_position_charts"):
                labels = []
                weekly_data = []
                season_data = [x[1] for x in season_average_team_data_by_position.get(team_id)]
                for week in team_weekly_points_by_position:
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
                doc_elements.append(KeepTogether(team_table))
                doc_elements.append(self.spacer_quarter_inch)

            if self.config.getboolean("Report", "team_bad_boy_stats"):
                offending_players = []
                for player in player_info:
                    if player.bad_boy_points > 0:
                        offending_players.append(player)

                offending_players = sorted(offending_players, key=lambda x: x.bad_boy_points, reverse=True)
                offending_players_data = []
                for player in offending_players:
                    offending_players_data.append([player.full_name, player.bad_boy_points, player.bad_boy_crime])
                # if there are no offending players, skip table
                if offending_players_data:
                    doc_elements.append(self.create_title("Whodunnit?", 8.5, "section"))
                    doc_elements.append(self.spacer_tenth_inch)
                    bad_boys_table = self.create_data_table(
                        [["Starting Player", "Bad Boy Points", "Worst Offense"]],
                        offending_players_data,
                        self.style_red_highlight,
                        self.style_tied_bad_boy,
                        [2.50 * inch, 2.50 * inch, 2.75 * inch])
                    doc_elements.append(KeepTogether(bad_boys_table))
                    doc_elements.append(self.spacer_tenth_inch)

            if self.config.getboolean("Report", "team_beef_stats"):
                doc_elements.append(self.create_title("Beefiest Bois", 8.5, "section"))
                doc_elements.append(self.spacer_tenth_inch)
                beefy_players = sorted(player_info, key=lambda x: x.tabbu, reverse=True)
                beefy_players_data = []
                num_beefy_bois = 3
                ndx = 0
                count = 0
                while count < num_beefy_bois:
                    player = beefy_players[ndx]  # type: BasePlayer
                    if player.last_name:
                        beefy_players_data.append([player.full_name, player.tabbu, player.weight])
                        count += 1
                    ndx += 1
                beefy_boi_table = self.create_data_table([["Starting Player", "TABBU(s)", "Weight (lbs.)"]],
                                                         beefy_players_data,
                                                         self.style_red_highlight,
                                                         self.style_tied_bad_boy,
                                                         [2.50 * inch, 2.50 * inch, 2.75 * inch])
                doc_elements.append(KeepTogether(beefy_boi_table))
                doc_elements.append(self.spacer_tenth_inch)

            if self.config.getboolean("Report", "team_boom_or_bust"):
                starting_players = []
                for player in player_info:  # type: BasePlayer
                    if player.selected_position not in ["BN", "IR"]:
                        starting_players.append(player)

                starting_players = sorted(starting_players, key=lambda x: x.points, reverse=True)
                best_weekly_player = starting_players[0]
                worst_weekly_player = starting_players[-1]

                best_player_headshot = get_image(best_weekly_player.headshot_url, self.data_dir, self.week_for_report,
                                                 1 * inch)
                worst_player_headshot = get_image(worst_weekly_player.headshot_url, self.data_dir, self.week_for_report,
                                                  1 * inch)

                data = [["BOOOOOOOOM", "...b... U... s... T"],
                        [best_weekly_player.full_name + " -- " + best_weekly_player.nfl_team_name,
                         worst_weekly_player.full_name + " -- " + worst_weekly_player.nfl_team_name],
                        [best_player_headshot, worst_player_headshot],
                        [best_weekly_player.points, worst_weekly_player.points]]
                table = Table(data, colWidths=4.0 * inch)
                table.setStyle(self.boom_bust_table_style)
                doc_elements.append(self.spacer_half_inch)
                doc_elements.append(self.create_title("Boom... or Bust", 8.5, "section"))
                doc_elements.append(self.spacer_tenth_inch)
                doc_elements.append(KeepTogether(table))

            if self.config.getboolean(
                    "Report", "team_points_by_position_charts") or self.config.getboolean(
                    "Report", "team_bad_boy_stats") or self.config.getboolean(
                    "Report", "team_beef_stats") or self.config.getboolean(
                    "Report", "team_boom_or_bust"):
                doc_elements.append(self.add_page_break())

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

        elements.append(self.add_page_break())

        # standings
        if self.config.getboolean("Report", "league_standings"):
            # update standings style to vertically justify all rows
            standings_style = copy.deepcopy(self.style)
            standings_style.add("VALIGN", (0, 0), (-1, -1), "MIDDLE")

            self.create_section(
                elements,
                "League Standings",
                self.standings_headers,
                self.report_data.data_for_current_standings,
                standings_style,
                standings_style,
                self.widths_10_cols_1,
                metric_type="standings"
            )
            elements.append(self.spacer_tenth_inch)

        if self.config.getboolean("Report", "league_playoff_probs"):
            # update playoff probabilities style to make playoff teams green
            playoff_probs_style = copy.deepcopy(self.style)
            playoff_probs_style.add("TEXTCOLOR", (0, 1), (-1, self.playoff_slots), colors.green)
            playoff_probs_style.add("FONT", (0, 1), (-1, -1), "Helvetica")

            data_for_playoff_probs = self.report_data.data_for_playoff_probs
            team_num = 1
            if data_for_playoff_probs:
                for team in data_for_playoff_probs:
                    if float(team[3].split("%")[0]) == 100.00 and int(team[4].split(" ")[0]) == 0:
                        playoff_probs_style.add("TEXTCOLOR", (0, team_num), (-1, team_num), colors.darkgreen)
                        playoff_probs_style.add("FONT", (0, team_num), (-1, team_num), "Helvetica-BoldOblique")

                    if (int(team[4].split(" ")[0]) + int(self.week_for_report)) > self.num_regular_season_weeks:
                        playoff_probs_style.add("TEXTCOLOR", (4, team_num), (4, team_num), colors.red)

                        if float(team[3].split("%")[0]) == 0.00:
                            playoff_probs_style.add("TEXTCOLOR", (0, team_num), (-1, team_num), colors.darkred)
                            playoff_probs_style.add("FONT", (0, team_num), (-1, team_num), "Helvetica-BoldOblique")

                    team_num += 1

            # playoff probabilities
            if data_for_playoff_probs:
                self.create_section(
                    elements,
                    "Playoff Probabilities",
                    self.playoff_probs_headers,
                    data_for_playoff_probs,
                    playoff_probs_style,
                    playoff_probs_style,
                    self.widths_n_cols_1,
                    subtitle_text="Playoff probabilities were calculated using %s Monte Carlo simulations to predict "
                                  "team performances through the end of the regular fantasy season." %
                                  "{0:,}".format(
                                      int(self.playoff_prob_sims) if self.playoff_prob_sims is not None else
                                      self.config.getint("Configuration", "num_playoff_simulations")),
                    metric_type="playoffs"
                )

        if self.config.getboolean("Report", "league_standings") or self.config.getboolean("Report",
                                                                                          "league_playoff_probs"):
            elements.append(self.add_page_break())

        if self.config.getboolean("Report", "league_power_rankings"):
            # power ranking
            self.create_section(
                elements,
                "Team Power Rankings",
                self.power_ranking_headers,
                self.data_for_power_rankings,
                self.style,
                self.style_tied_power_rankings,
                self.widths_4_cols_2,
                tied_metric=self.report_data.ties_for_power_rankings > 0,
                metric_type="power_ranking",
                subtitle_text="Average of weekly score, coaching efficiency and luck ranks."
            )
            elements.append(self.spacer_twentieth_inch)

        if self.config.getboolean("Report", "league_z_score_rankings"):
            # z-scores (if week 3 or later, once meaningful z-scores can be calculated)
            if self.data_for_z_scores:
                self.create_section(
                    elements,
                    "Team Z-Score Rankings",
                    self.zscores_headers,
                    self.data_for_z_scores,
                    self.style,
                    None,
                    self.widths_4_cols_2,
                    tied_metric=False,
                    metric_type="z_score",
                    subtitle_text=[
                        "Measure of standard deviations away from mean for a score. Shows teams performing ",
                        "above or below their normal scores for the current week.  See <a href = "
                        "'https://en.wikipedia.org/wiki/Standard_score' color='blue'>Standard Score</a>."
                    ]
                )

        if self.config.getboolean("Report", "league_power_rankings") or self.config.getboolean(
                "Report", "league_z_score_rankings"):
            elements.append(self.add_page_break())

        if self.config.getboolean("Report", "league_score_rankings"):
            # scores
            self.create_section(
                elements,
                "Team Score Rankings",
                self.scores_headers,
                self.data_for_scores,
                self.style,
                self.style_tied_scores,
                self.widths_5_cols_1,
                tied_metric=self.report_data.ties_for_scores > 0,
                metric_type="scores"
            )
            elements.append(self.spacer_twentieth_inch)

        if self.config.getboolean("Report", "league_coaching_efficiency_rankings"):
            # coaching efficiency
            self.create_section(
                elements,
                "Team Coaching Efficiency Rankings",
                self.efficiency_headers,
                self.data_for_coaching_efficiency,
                self.style,
                self.style_tied_efficiencies,
                self.widths_5_cols_1,
                tied_metric=self.report_data.ties_for_coaching_efficiency > 0,
                metric_type="coaching_efficiency"
            )
            elements.append(self.spacer_twentieth_inch)

        if self.config.getboolean("Report", "league_luck_rankings"):
            # luck
            self.create_section(
                elements,
                "Team Luck Rankings",
                self.luck_headers,
                self.data_for_luck,
                self.style,
                self.style_tied_luck,
                self.widths_5_cols_1,
                tied_metric=self.report_data.ties_for_luck > 0,
                metric_type="luck"
            )

        if self.config.getboolean("Report", "league_score_rankings") or self.config.getboolean(
                "Report", "league_coaching_efficiency_rankings") or self.config.getboolean("Report",
                                                                                           "league_luck_rankings"):
            elements.append(self.add_page_break())

        if self.config.getboolean("Report", "league_weekly_top_scorers"):
            # weekly top scorers
            self.create_section(
                elements,
                "Weekly Top Scorers",
                self.weekly_top_scorer_headers,
                self.data_for_season_weekly_top_scorers,
                self.style_no_highlight,
                self.style_no_highlight,
                self.widths_4_cols_2,
                tied_metric=self.report_data.ties_for_scores > 0,
                metric_type="top_scorers"
            )
            elements.append(self.spacer_twentieth_inch)

        if self.config.getboolean("Report", "league_weekly_highest_ce"):
            # weekly highest coaching efficiency
            self.create_section(
                elements,
                "Weekly Highest Coaching Efficiency",
                self.weekly_highest_ce_headers,
                self.data_for_season_weekly_highest_ce,
                self.style_no_highlight,
                self.style_no_highlight,
                self.widths_4_cols_2,
                tied_metric=self.report_data.ties_for_coaching_efficiency > 0,
                metric_type="highest_ce"
            )

        if self.config.getboolean("Report", "league_weekly_top_scorers") or self.config.getboolean(
                "Report", "league_weekly_highest_ce"):
            elements.append(self.add_page_break())

        if self.config.getboolean("Report", "league_bad_boy_rankings"):
            # bad boy rankings
            self.create_section(
                elements,
                "Bad Boy Rankings",
                self.bad_boy_headers,
                self.data_for_bad_boy_rankings,
                self.style,
                self.style_tied_bad_boy,
                self.widths_6_cols_2,
                tied_metric=self.report_data.ties_for_bad_boy_rankings > 0,
                metric_type="bad_boy"
            )
            elements.append(self.spacer_twentieth_inch)

        if self.config.getboolean("Report", "league_beef_rankings"):
            # beef rankings
            self.create_section(
                elements,
                "Beef Rankings",
                self.beef_headers,
                self.data_for_beef_rankings,
                self.style_left_alighn_right_col,
                self.style_tied_beef,
                self.widths_4_cols_4,
                tied_metric=self.report_data.ties_for_beef_rankings > 0,
                metric_type="beef",
                subtitle_text=[
                    "Team Beef Ranking is measured in TABBUs (Trimmed And Boneless Beef Units). "
                    "One TABBU is currently established as 500 lbs.",
                    "TABBU derivation stems from academic research done for the beef industry found <a href = "
                    "'https://extension.tennessee.edu/publications/Documents/PB1822.pdf' color='blue'>here</a>."
                ]
            )

        if self.config.getboolean("Report", "league_bad_boy_rankings") or self.config.getboolean(
                "Report", "league_beef_rankings"):
            elements.append(self.add_page_break())

        if self.config.getboolean("Report", "report_time_series_charts"):
            series_names = line_chart_data_list[0]
            points_data = line_chart_data_list[2]
            efficiency_data = line_chart_data_list[3]
            luck_data = line_chart_data_list[4]

            # Remove any zeros from coaching efficiency to make table prettier
            for team in efficiency_data:
                week_index = 0
                for week in team:
                    if len(team) > 1:
                        if week[1] == 0.0:
                            del team[week_index]
                    week_index += 1

            # create line charts for points, coaching efficiency, and luck
            charts_page_title_str = "Time Series Charts"
            charts_page_title = self.create_title(
                "<i>" + charts_page_title_str + "</i>", element_type="chart",
                anchor="<a name = page.html#" + str(self.toc.get_current_anchor()) + "></a>")
            self.toc.add_chart_section(charts_page_title_str)
            elements.append(charts_page_title)
            elements.append(KeepTogether(
                self.create_line_chart(points_data, len(points_data[0]), series_names, "Weekly Points", "Weeks",
                                       "Fantasy Points", 10.00)))
            elements.append(self.spacer_twentieth_inch)
            elements.append(KeepTogether(
                self.create_line_chart(efficiency_data, len(points_data[0]), series_names, "Weekly Coaching Efficiency",
                                       "Weeks", "Coaching Efficiency (%)", 5.00)))
            elements.append(self.spacer_twentieth_inch)
            elements.append(KeepTogether(
                self.create_line_chart(luck_data, len(points_data[0]), series_names, "Weekly Luck", "Weeks", "Luck (%)",
                                       20.00)))
            elements.append(self.spacer_tenth_inch)
            elements.append(self.add_page_break())

        if self.config.getboolean(
                "Report", "report_team_stats") and (self.config.getboolean(
                "Report", "team_points_by_position_charts") or self.config.getboolean(
                "Report", "team_bad_boy_stats") or self.config.getboolean(
                "Report", "team_beef_stats") or self.config.getboolean(
                "Report", "team_boom_or_bust")):
            # dynamically build additional pages for individual team stats
            self.create_team_stats_pages(elements, self.data_for_weekly_points_by_position,
                                         self.data_for_season_average_team_points_by_position)

        # insert table of contents after report title and spacer
        elements.insert(2, self.toc.get_toc())

        elements.append(self.report_footer)

        # build pdf
        logger.info("generating PDF ({})...".format(filename_with_path.split("/")[-1]))
        doc.build(elements, onFirstPage=self.add_page_number, onLaterPages=self.add_page_number)

        return doc.filename


class TableOfContents(object):

    def __init__(self, config, break_ties):

        self.config = config  # type: ConfigParser
        self.break_ties = break_ties

        self.toc_style_right = ParagraphStyle(name="tocr", alignment=TA_RIGHT, fontSize=12)
        self.toc_style_center = ParagraphStyle(name="tocc", alignment=TA_CENTER, fontSize=12)
        self.toc_style_left = ParagraphStyle(name="tocl", alignment=TA_LEFT, fontSize=12)
        self.toc_style_title_right = ParagraphStyle(name="tocr", alignment=TA_RIGHT, fontSize=14)
        self.toc_style_title_left = ParagraphStyle(name="tocl", alignment=TA_LEFT, fontSize=14)

        self.toc_anchor = 0

        # start on page 1 since table of contents is on first page
        self.toc_page = 1

        self.toc_metric_section_data = None
        self.toc_chart_section_data = None
        self.toc_team_section_data = None
        if self.config.getboolean(
                "Report", "league_standings") or self.config.getboolean(
                "Report", "league_playoff_probs") or self.config.getboolean(
                "Report", "league_power_rankings") or self.config.getboolean(
                "Report", "league_z_score_rankings") or self.config.getboolean(
                "Report", "league_score_rankings") or self.config.getboolean(
                "Report", "league_coaching_efficiency_rankings") or self.config.getboolean(
                "Report", "league_luck_rankings") or self.config.getboolean(
                "Report", "league_weekly_top_scorers") or self.config.getboolean(
                "Report", "league_weekly_highest_ce") or self.config.getboolean(
                "Report", "league_bad_boy_rankings") or self.config.getboolean(
                "Report", "league_beef_rankings"):
            self.toc_metric_section_data = [
                [Paragraph("<b><i>Metrics</i></b>", self.toc_style_title_right),
                 "",
                 Paragraph("<b><i>Page</i></b>", self.toc_style_title_left)]
            ]

        if self.config.getboolean("Report", "report_time_series_charts"):
            self.toc_chart_section_data = [
                [Paragraph("<b><i>Charts</i></b>", self.toc_style_title_right),
                 "",
                 Paragraph("<b><i>Page</i></b>", self.toc_style_title_left)]
            ]

        if self.config.getboolean(
                "Report", "report_team_stats") and (self.config.getboolean(
                "Report", "team_points_by_position_charts") or self.config.getboolean(
                "Report", "team_bad_boy_stats") or self.config.getboolean(
                "Report", "team_beef_stats") or self.config.getboolean(
                "Report", "team_boom_or_bust")):
            self.toc_team_section_data = [
                [Paragraph("<b><i>Teams</i></b>", self.toc_style_title_right),
                 "",
                 Paragraph("<b><i>Page</i></b>", self.toc_style_title_left)]
            ]

    def add_toc_page(self, pages_to_add=1):
        self.toc_page += pages_to_add

    def format_toc_section(self, title, color="blue"):
        return [
            Paragraph(
                "<a href = page.html#" + str(self.toc_anchor) + " color=" + color + "><b><u>" + title + "</u></b></a>",
                self.toc_style_right),
            Paragraph(". . . . . . . . . . . . . . . . . . . .", self.toc_style_center),
            Paragraph(str(self.toc_page), self.toc_style_left)
        ]

    def add_metric_section(self, title):
        if self.break_ties:
            if title == "Team Score Rankings" or title == "Team Coaching Efficiency Rankings":
                color = "green"
            else:
                color = "blue"
        else:
            color = "blue"
        metric_section = self.format_toc_section(title, color)
        self.toc_metric_section_data.append(metric_section)
        self.toc_anchor += 1

    def add_team_section(self, team_name):
        team_section = self.format_toc_section(team_name)
        self.toc_team_section_data.append(team_section)
        self.toc_anchor += 1

    def add_chart_section(self, title):
        chart_section = self.format_toc_section(title)
        self.toc_chart_section_data.append(chart_section)
        self.toc_anchor += 1

    def get_current_anchor(self):
        return self.toc_anchor

    def get_toc(self):
        return Table(
            (self.toc_metric_section_data + [["", "", ""]] if self.toc_metric_section_data else []) +
            (self.toc_chart_section_data + [["", "", ""]] if self.toc_chart_section_data else []) +
            (self.toc_team_section_data if self.toc_team_section_data else []),
            colWidths=[3.25 * inch, 2 * inch, 2.50 * inch],
            rowHeights=[0.30 * inch] * len(self.toc_metric_section_data) + [0.10 * inch] +
                       [0.30 * inch] * len(self.toc_chart_section_data) + [0.10 * inch] +
                       [0.30 * inch] * len(self.toc_team_section_data)
        )
