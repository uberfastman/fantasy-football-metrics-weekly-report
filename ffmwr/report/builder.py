__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List

from ffmwr.calculate.coaching_efficiency import CoachingEfficiency
from ffmwr.calculate.metrics import CalculateMetrics
from ffmwr.calculate.points_by_position import PointsByPosition
from ffmwr.calculate.season_averages import SeasonAverageCalculator
from ffmwr.models.base.model import BaseLeague, BaseTeam
from ffmwr.dao.platforms.base.platform import BasePlatform
from ffmwr.report.data import ReportData
from ffmwr.report.pdf.generator import PdfGenerator
from ffmwr.utilities.app import platform_data_factory, patch_http_connection_pool
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings
from ffmwr.utilities.utils import format_platform_display

logger = get_logger(__name__, propagate=False)


class FantasyFootballReport(object):
    def __init__(
        self,
        settings: AppSettings,
        week_for_report=None,
        platform=None,
        league_id=None,
        game_id=None,
        season=None,
        start_week=None,
        playoff_prob_sims=None,
        break_ties=False,
        dq_ce=False,
        save_data=False,
        refresh_feature_web_data=False,
        offline=False,
        test=False,
    ):
        logger.debug("Instantiating fantasy football report.")

        patch_http_connection_pool(maxsize=100)

        self.settings = settings

        self.root_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.settings.data_dir_path
        if platform:
            self.platform: str = platform
            self.platform_display: str = format_platform_display(self.platform)
        else:
            self.platform: str = self.settings.platform
            self.platform_display: str = format_platform_display(self.platform)
        if league_id:
            self.league_id: str = str(league_id)
        else:
            self.league_id: str = self.settings.league_id
        # TODO: game_id for Yahoo Fantasy Football can be int or str (YFPY expects int, with str for game_code)
        if game_id:
            self.game_id = game_id
        else:
            self.game_id = self.settings.platform_settings.yahoo_game_id
        if season:
            self.season: int = int(season)
        else:
            self.season: int = self.settings.season

        self.playoff_prob_sims = playoff_prob_sims
        self.break_ties = break_ties
        self.dq_ce = dq_ce

        self.save_data = save_data
        # refresh feature data pulled from external web sources
        self.refresh_feature_web_data = refresh_feature_web_data

        self.offline = offline
        self.test = test

        platform_data: BasePlatform = platform_data_factory(
            settings=self.settings,
            root_dir=self.root_dir,
            data_dir=self.data_dir,
            platform=self.platform,
            game_id=self.game_id,
            league_id=self.league_id,
            season=self.season,
            start_week=start_week,
            week_for_report=week_for_report,
            save_data=self.save_data,
            offline=self.offline,
        )

        # retrieve all data from respective platform API
        platform_data.fetch()

        self.league: BaseLeague = platform_data.league

        if self.league.num_playoff_slots > 0:
            self.playoff_probs = self.league.get_playoff_probs(
                self.playoff_prob_sims, self.save_data, self.offline, recalculate=True
            )

        else:
            self.playoff_probs = None

        if self.settings.report_settings.league_bad_boy_rankings_bool:
            self.bad_boy_stats = self.league.get_bad_boy_stats(
                self.refresh_feature_web_data, self.save_data, self.offline
            )
        else:
            self.bad_boy_stats = None

        if self.settings.report_settings.league_beef_rankings_bool:
            self.beef_stats = self.league.get_beef_stats(self.refresh_feature_web_data, self.save_data, self.offline)
        else:
            self.beef_stats = None

        if self.settings.report_settings.league_high_roller_rankings_bool:
            self.high_roller_stats = self.league.get_high_roller_stats(
                self.refresh_feature_web_data, self.save_data, self.offline
            )
        else:
            self.high_roller_stats = None

        # output league info for verification
        logger.info(
            f"...setup complete for "
            f'"{self.league.name.upper()}" ({self.league_id}) week {self.league.week_for_report} report.'
        )

    def create_pdf_report(self) -> Path:
        logger.debug("Creating fantasy football report PDF.")

        report_data = None

        week_for_report_ordered_team_names = []
        week_for_report_ordered_managers = []

        time_series_points_data = []
        time_series_efficiency_data = []
        time_series_luck_data = []
        time_series_power_rank_data = []
        time_series_zscore_data = []

        season_total_optimal_points_data = {}

        season_avg_points_by_position = defaultdict(list)
        season_weekly_top_scorers = []
        season_weekly_low_scorers = []
        season_weekly_highest_ce = []
        season_weekly_teams_results = []

        week_counter = self.league.start_week
        while week_counter <= self.league.week_for_report:
            week_for_report = self.league.week_for_report
            metrics_calculator = CalculateMetrics(self.league_id, self.league.num_playoff_slots, self.playoff_prob_sims)

            custom_weekly_matchups = self.league.get_custom_weekly_matchups(week_counter)

            report_data = ReportData(
                settings=self.settings,
                league=self.league,
                season_weekly_teams_results=season_weekly_teams_results,
                week_counter=week_counter,
                week_for_report=week_for_report,
                season=self.season,
                metrics_calculator=metrics_calculator,
                metrics={
                    "coaching_efficiency": CoachingEfficiency(self.league),
                    "luck": metrics_calculator.calculate_luck(week_counter, self.league, custom_weekly_matchups),
                    "records": metrics_calculator.calculate_records(week_counter, self.league, custom_weekly_matchups),
                    "playoff_probs": self.playoff_probs,
                    "bad_boy_stats": self.bad_boy_stats,
                    "beef_stats": self.beef_stats,
                    "high_roller_stats": self.high_roller_stats,
                },
                break_ties=self.break_ties,
                dq_ce=self.dq_ce,
                testing=self.test,
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

            low_scorer = {
                "week": week_counter,
                "team": report_data.data_for_scores[-1][1],
                "manager": report_data.data_for_scores[-1][2],
                "score": report_data.data_for_scores[-1][3],
            }
            season_weekly_low_scorers.append(low_scorer)

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
            weekly_optimal_points_data = []
            weekly_z_score_data = []
            weekly_power_rank_data = []

            team: List
            for team in report_data.data_for_teams:
                ordered_team_names.append(team[1])
                ordered_team_managers.append(team[2])
                weekly_points_data.append([week_counter, float(team[3])])
                weekly_coaching_efficiency_data.append([week_counter, team[4]])
                weekly_luck_data.append([week_counter, float(team[5])])
                weekly_optimal_points_data.append([week_counter, team[1], float(team[6])])
                weekly_z_score_data.append([week_counter, team[7]])
                weekly_power_rank_data.append([week_counter, team[8]])

            week_for_report_ordered_team_names = ordered_team_names
            week_for_report_ordered_managers = ordered_team_managers

            if week_counter == self.league.start_week:
                for team_points in weekly_points_data:
                    time_series_points_data.append([team_points])
                for team_efficiency in weekly_coaching_efficiency_data:
                    time_series_efficiency_data.append([team_efficiency])
                for team_luck in weekly_luck_data:
                    time_series_luck_data.append([team_luck])
                for team_optimal_points in weekly_optimal_points_data:
                    season_total_optimal_points_data[team_optimal_points[1]] = team_optimal_points[2]
                for team_zscore in weekly_z_score_data:
                    time_series_zscore_data.append([team_zscore])
                for team_power_rank in weekly_power_rank_data:
                    time_series_power_rank_data.append([team_power_rank])
            else:
                for index, team_points in enumerate(weekly_points_data):
                    time_series_points_data[index].append(team_points)
                for index, team_efficiency in enumerate(weekly_coaching_efficiency_data):
                    if team_efficiency[1] != "DQ":
                        time_series_efficiency_data[index].append(team_efficiency)
                for index, team_luck in enumerate(weekly_luck_data):
                    time_series_luck_data[index].append(team_luck)
                for index, team_optimal_points in enumerate(weekly_optimal_points_data):
                    season_total_optimal_points_data[team_optimal_points[1]] += team_optimal_points[2]
                for index, team_zscore in enumerate(weekly_z_score_data):
                    time_series_zscore_data[index].append(team_zscore)
                for index, team_power_rank in enumerate(weekly_power_rank_data):
                    time_series_power_rank_data[index].append(team_power_rank)

            week_counter += 1

        report_data.data_for_season_avg_points_by_position = season_avg_points_by_position
        report_data.data_for_season_weekly_top_scorers = season_weekly_top_scorers
        report_data.data_for_season_weekly_low_scorers = season_weekly_low_scorers
        report_data.data_for_season_weekly_highest_ce = season_weekly_highest_ce

        # calculate season average metrics and then add columns for them to their respective metric table data
        season_average_calculator = SeasonAverageCalculator(
            week_for_report_ordered_team_names, report_data, self.break_ties
        )

        report_data.data_for_scores = season_average_calculator.get_average(
            time_series_points_data,
            "data_for_scores",
            first_ties=report_data.num_first_place_for_score_before_resolution > 1,
        )

        report_data.data_for_coaching_efficiency = season_average_calculator.get_average(
            time_series_efficiency_data,
            "data_for_coaching_efficiency",
            with_percent=True,
            # TODO: find better pattern for player points retrieval instead of passing around a class method object
            # first_ties=((report_data.num_first_place_for_coaching_efficiency_before_resolution > 1) and
            #             (report_data.league.player_data_by_week_function is not None))
            first_ties=report_data.num_first_place_for_coaching_efficiency_before_resolution > 1,
        )

        report_data.data_for_luck = season_average_calculator.get_average(
            time_series_luck_data, "data_for_luck", with_percent=True
        )

        # add weekly record to luck data
        for team_luck_data_entry in report_data.data_for_luck:
            for team in self.league.teams_by_week[str(self.league.week_for_report)].values():
                team: BaseTeam
                if team_luck_data_entry[1] == team.name:
                    team_luck_data_entry.append(team.weekly_overall_record.get_record_str())

        # add season total optimal points to optimal points data
        sorted_season_total_optimal_points_data = dict(
            sorted(season_total_optimal_points_data.items(), key=lambda x: x[1], reverse=True)
        )
        list_sorted_season_total_optimal_points_data = [
            (i, k, v) for i, (k, v) in enumerate(sorted_season_total_optimal_points_data.items())
        ]
        for team_optimal_points_data_entry in report_data.data_for_optimal_scores:
            for team_index, team_name, season_total_optimal_points in list_sorted_season_total_optimal_points_data:
                if team_optimal_points_data_entry[1] == team_name:
                    place = team_index + 1
                    total_optimal_points_ranked = f"{round(season_total_optimal_points, 2):.2f} ({place})"
                    team_optimal_points_data_entry.append(total_optimal_points_ranked)

        report_data.data_for_power_rankings = season_average_calculator.get_average(
            time_series_power_rank_data, "data_for_power_rankings", reverse=False
        )

        line_chart_data_list = [
            week_for_report_ordered_team_names,
            week_for_report_ordered_managers,
            time_series_points_data,
            time_series_efficiency_data,
            time_series_luck_data,
            time_series_zscore_data,
            time_series_power_rank_data,
        ]

        # calculate season average points by position and add them to the report_data
        report_data.data_for_season_avg_points_by_position = (
            PointsByPosition.calculate_points_by_position_season_averages(
                report_data.data_for_season_avg_points_by_position
            )
        )

        filename = (
            self.league.name.replace(" ", "-")
            + "("
            + str(self.league_id)
            + ")_week-"
            + str(self.league.week_for_report)
            + "_report.pdf"
        )
        report_save_dir = (
            self.settings.output_dir_path
            / str(self.league.season)
            / f"{self.league.name.replace(' ', '-')}({self.league_id})"
        )
        report_title_text = f"{self.league.name} ({self.league_id}) Week {self.league.week_for_report} Report"
        report_footer_text = (
            f"<para alignment='center'>"
            f"Report generated {datetime.now():%Y-%b-%d %H:%M:%S} for {self.platform_display} "
            f'Fantasy Football league "{self.league.name}" with id {self.league_id} '
            f'(<a href="{self.league.url}" color=blue><u>{self.league.url}</u></a>).'
            f"<br></br><br></br><br></br>"
            f"If you enjoy using the Fantasy Football Metrics Weekly Report app, please feel free help support its "
            f"development below:"
            f"</para>"
        )

        if not Path(report_save_dir).is_dir():
            os.makedirs(report_save_dir)

        if not self.test:
            filename_with_path = Path(report_save_dir) / filename
        else:
            filename_with_path = self.settings.output_dir_path / "test_report.pdf"

        # instantiate pdf generator
        pdf_generator = PdfGenerator(
            settings=self.settings,
            season=self.season,
            league=self.league,
            playoff_prob_sims=self.playoff_prob_sims,
            report_title_text=report_title_text,
            report_footer_text=report_footer_text,
            report_data=report_data,
        )

        # generate pdf of report
        file_for_upload: Path = pdf_generator.generate_pdf(filename_with_path, line_chart_data_list)

        logger.info(f"...SUCCESS! Generated PDF: {file_for_upload}\n")
        logger.debug(
            "\n\n\n"
            "\n~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * "
            "\n~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * END RUN ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * "
            "\n~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * ~ * "
            "\n\n\n"
        )

        return file_for_upload
