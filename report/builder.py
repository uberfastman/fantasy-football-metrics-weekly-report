__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import datetime
import os
from collections import defaultdict

from calculate.coaching_efficiency import CoachingEfficiency
from calculate.metrics import CalculateMetrics
from calculate.points_by_position import PointsByPosition
from calculate.season_averages import SeasonAverageCalculator
from dao.base import BaseLeague
from dao.utils import league_data_factory, patch_http_connection_pool
from report.data import ReportData
from report.logger import get_logger
from report.pdf.generator import PdfGenerator

logger = get_logger(__name__, propagate=False)


class FantasyFootballReport(object):
    def __init__(self,
                 week_for_report=None,
                 platform=None,
                 league_id=None,
                 game_id=None,
                 season=None,
                 config=None,
                 refresh_web_data=False,
                 playoff_prob_sims=None,
                 break_ties=False,
                 dq_ce=False,
                 save_data=False,
                 dev_offline=False,
                 test=False):

        patch_http_connection_pool(maxsize=100)

        # config vars
        self.config = config
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, self.config.get("Configuration", "data_dir"))
        if platform:
            self.platform = platform
            self.platform_str = str.capitalize(platform)
        else:
            self.platform = self.config.get("Configuration", "platform")
            self.platform_str = str.capitalize(self.config.get("Configuration", "platform"))
        if league_id:
            self.league_id = league_id
        else:
            self.league_id = self.config.get("Configuration", "league_id")
        if game_id:
            self.game_id = game_id
        else:
            self.game_id = self.config.get("Configuration", "game_id")
        if season:
            self.season = season
        else:
            self.season = self.config.get("Configuration", "season")

        self.save_data = save_data
        # refresh data pulled from external web sources: bad boy data from USA Today, beef data from Fox Sports
        self.refresh_web_data = refresh_web_data
        self.playoff_prob_sims = playoff_prob_sims
        self.break_ties = break_ties
        self.dq_ce = dq_ce

        self.dev_offline = dev_offline
        self.test = test

        # verification output message
        logger.info(
            "\nGenerating%s %s Fantasy Football report with settings:\n"
            "    league id: %s\n"
            "    game id: %s\n"
            "    week: %s\n"
            "%s"
            "%s"
            "    playoff_prob_sims: %s\n"
            "%s"
            "%s"
            "%s"
            "%s"
            "on %s..." % (
                " TEST" if self.test else "", self.platform_str,
                str(self.league_id),
                str(self.game_id) if self.game_id else "nfl (current season)",
                str(week_for_report) if week_for_report else "selected/default",
                "    save_data: " + str(self.save_data) + "\n",
                "    refresh_web_data: " + str(self.refresh_web_data) + "\n",
                str(self.playoff_prob_sims),
                "    break_ties: " + str(self.break_ties) + "\n",
                "    dq_ce: " + str(self.dq_ce) + "\n",
                "    dev_offline: " + str(self.dev_offline) + "\n",
                "    test: " + str(self.test) + "\n",
                "{:%b %d, %Y}".format(datetime.datetime.now())
            )
        )

        begin = datetime.datetime.now()
        logger.info("Retrieving fantasy football data from {}...".format(
            self.platform_str + (" API" if not self.dev_offline else " saved data")))

        # retrieve all league data from respective platform API
        self.league = league_data_factory(
            week_for_report=week_for_report,
            platform=self.platform,
            league_id=self.league_id,
            game_id=self.game_id,
            season=self.season,
            config=self.config,
            base_dir=base_dir,
            data_dir=self.data_dir,
            save_data=self.save_data,
            dev_offline=self.dev_offline
        )  # type: BaseLeague

        delta = datetime.datetime.now() - begin
        logger.info("...retrieved all fantasy football data from {} in {}\n".format(
            self.platform_str + (" API" if not self.dev_offline else " saved data"), str(delta)))

        self.playoff_probs = self.league.get_playoff_probs(self.save_data, self.playoff_prob_sims,
                                                           self.dev_offline, recalculate=True)

        begin = datetime.datetime.now()
        logger.info("Retrieving bad boy data from http://nflarrest.com {}...".format(
            "website" if not self.dev_offline or self.refresh_web_data else "saved data"))
        self.bad_boy_stats = self.league.get_bad_boy_stats(self.save_data, self.dev_offline, self.refresh_web_data)
        delta = datetime.datetime.now() - begin
        logger.info("...retrieved all bad boy data from http://nflarrest.com {} in {}\n".format(
            "website" if not self.dev_offline else "saved data", str(delta)))

        begin = datetime.datetime.now()
        logger.info("Retrieving beef data from Fox Sports {}...".format(
            "API" if not self.dev_offline or self.refresh_web_data else "saved data"))
        self.beef_stats = self.league.get_beef_stats(self.save_data, self.dev_offline, self.refresh_web_data)
        delta = datetime.datetime.now() - begin
        logger.info("...retrieved all beef data from Fox Sports {} in {}\n".format(
            "API" if not self.dev_offline else "saved data", str(delta)))

        # output league info for verification
        logger.info("...setup complete for \"{}\" ({}) week {} report.\n".format(self.league.name.upper(),
                                                                                 self.league_id,
                                                                                 self.league.week_for_report))

    def create_pdf_report(self):

        report_data = None

        week_for_report_ordered_team_names = []
        week_for_report_ordered_managers = []

        time_series_points_data = []
        time_series_efficiency_data = []
        time_series_luck_data = []
        time_series_power_rank_data = []
        time_series_zscore_data = []

        season_avg_points_by_position = defaultdict(list)
        season_weekly_top_scorers = []
        season_weekly_highest_ce = []
        season_weekly_teams_results = []

        week_counter = 1
        while week_counter <= self.league.week_for_report:

            week_for_report = self.league.week_for_report
            metrics_calculator = CalculateMetrics(self.config, self.league_id, self.league.num_playoff_slots,
                                                  self.playoff_prob_sims)

            report_data = ReportData(
                config=self.config,
                league=self.league,
                season_weekly_teams_results=season_weekly_teams_results,
                week_counter=str(week_counter),
                week_for_report=week_for_report,
                metrics_calculator=metrics_calculator,
                metrics={
                    "coaching_efficiency": CoachingEfficiency(self.config, self.league.get_roster_slots_by_type()),
                    "matchups_results": metrics_calculator.calculate_luck_and_record(
                        self.league.teams_by_week.get(str(week_counter)),
                        self.league.get_custom_weekly_matchups(str(week_counter))
                    ),
                    "playoff_probs": self.playoff_probs,
                    "bad_boy_stats": self.bad_boy_stats,
                    "beef_stats": self.beef_stats
                },
                break_ties=self.break_ties,
                dq_ce=self.dq_ce,
                testing=self.test
            )

            for team_id, team_result in report_data.teams_results.items():
                for weekly_team_points_by_position in report_data.data_for_weekly_points_by_position:
                    if weekly_team_points_by_position[0] == team_id:
                        season_avg_points_by_position[team_id].append(weekly_team_points_by_position[1])

            top_scorer = {
                "week": week_counter,
                "team": report_data.data_for_scores[0][1],
                "manager": report_data.data_for_scores[0][2],
                "score": report_data.data_for_scores[0][3],
            }
            season_weekly_top_scorers.append(top_scorer)

            highest_ce = {
                "week": week_counter,
                "team": report_data.data_for_coaching_efficiency[0][1],
                "manager": report_data.data_for_coaching_efficiency[0][2],
                "ce": report_data.data_for_coaching_efficiency[0][3],
            }
            season_weekly_highest_ce.append(highest_ce)

            season_weekly_teams_results.append(report_data.teams_results)

            ordered_team_names = []
            ordered_team_managers = []
            weekly_points_data = []
            weekly_coaching_efficiency_data = []
            weekly_luck_data = []
            weekly_z_score_data = []
            weekly_power_rank_data = []

            for team in report_data.data_for_teams:
                ordered_team_names.append(team[1])
                ordered_team_managers.append(team[2])
                weekly_points_data.append([int(week_counter), float(team[3])])
                weekly_coaching_efficiency_data.append([int(week_counter), team[4]])
                weekly_luck_data.append([int(week_counter), float(team[5])])
                weekly_z_score_data.append([int(week_counter), team[6]])
                weekly_power_rank_data.append([int(week_counter), team[7]])

            week_for_report_ordered_team_names = ordered_team_names
            week_for_report_ordered_managers = ordered_team_managers

            if week_counter == 1:
                for team_points in weekly_points_data:
                    time_series_points_data.append([team_points])
                for team_efficiency in weekly_coaching_efficiency_data:
                    time_series_efficiency_data.append([team_efficiency])
                for team_luck in weekly_luck_data:
                    time_series_luck_data.append([team_luck])
                for team_zscore in weekly_z_score_data:
                    time_series_zscore_data.append([team_zscore])
                for team_power_rank in weekly_power_rank_data:
                    time_series_power_rank_data.append([team_power_rank])
            else:
                for index, team_points in enumerate(weekly_points_data):
                    time_series_points_data[index].append(team_points)
                for index, team_efficiency in enumerate(weekly_coaching_efficiency_data):
                    if float(team_efficiency[1]) != 0.0:
                        time_series_efficiency_data[index].append(team_efficiency)
                for index, team_luck in enumerate(weekly_luck_data):
                    time_series_luck_data[index].append(team_luck)
                for index, team_zscore in enumerate(weekly_z_score_data):
                    time_series_zscore_data[index].append(team_zscore)
                for index, team_power_rank in enumerate(weekly_power_rank_data):
                    time_series_power_rank_data[index].append(team_power_rank)

            week_counter += 1

        report_data.data_for_season_avg_points_by_position = season_avg_points_by_position
        report_data.data_for_season_weekly_top_scorers = season_weekly_top_scorers
        report_data.data_for_season_weekly_highest_ce = season_weekly_highest_ce

        # calculate season average metrics and then add columns for them to their respective metric table data
        season_average_calculator = SeasonAverageCalculator(week_for_report_ordered_team_names, report_data,
                                                            self.break_ties)

        report_data.data_for_scores = season_average_calculator.get_average(
            time_series_points_data,
            "data_for_scores",
            first_ties=report_data.num_first_place_for_score_before_resolution > 1
        )

        report_data.data_for_coaching_efficiency = season_average_calculator.get_average(
            time_series_efficiency_data,
            "data_for_coaching_efficiency",
            with_percent=True,
            first_ties=report_data.num_first_place_for_coaching_efficiency_before_resolution > 1
        )

        report_data.data_for_luck = season_average_calculator.get_average(
            time_series_luck_data,
            "data_for_luck",
            with_percent=True
        )

        report_data.data_for_power_rankings = season_average_calculator.get_average(
            time_series_power_rank_data,
            "data_for_power_rankings",
            reverse=False
        )

        line_chart_data_list = [week_for_report_ordered_team_names,
                                week_for_report_ordered_managers,
                                time_series_points_data,
                                time_series_efficiency_data,
                                time_series_luck_data,
                                time_series_zscore_data,
                                time_series_power_rank_data]

        # calculate season average points by position and add them to the report_data
        report_data.data_for_season_avg_points_by_position = \
            PointsByPosition.calculate_points_by_position_season_averages(
                report_data.data_for_season_avg_points_by_position)

        filename = self.league.name.replace(" ", "-") + "(" + str(self.league_id) + ")_week-" + str(
            self.league.week_for_report) + "_report.pdf"
        report_save_dir = os.path.join(
            self.config.get("Configuration", "output_dir"),
            str(self.league.season),
            self.league.name.replace(" ", "-") + "(" + self.league_id + ")")
        report_title_text = \
            self.league.name + " (" + str(self.league_id) + ") Week " + \
            str(self.league.week_for_report) + " Report"
        report_footer_text = \
            "<para alignment='center'>Report generated %s for %s Fantasy Football league '%s' (%s).</para>" % \
            ("{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()), self.platform_str, self.league.name,
             self.league_id)

        if not os.path.isdir(report_save_dir):
            os.makedirs(report_save_dir)

        if not self.test:
            filename_with_path = os.path.join(report_save_dir, filename)
        else:
            filename_with_path = os.path.join(self.config.get("Configuration", "output_dir"), "test_report.pdf")

        # instantiate pdf generator
        pdf_generator = PdfGenerator(
            config=self.config,
            league=self.league,
            playoff_prob_sims=self.playoff_prob_sims,
            report_title_text=report_title_text,
            report_footer_text=report_footer_text,
            report_data=report_data
        )

        # generate pdf of report
        file_for_upload = pdf_generator.generate_pdf(filename_with_path, line_chart_data_list)

        logger.info("...SUCCESS! Generated PDF: {}\n".format(file_for_upload))

        return file_for_upload
