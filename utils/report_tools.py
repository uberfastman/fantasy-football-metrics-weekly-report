__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os
import sys
import time

import requests
from bs4 import BeautifulSoup
from urllib3 import connectionpool, poolmanager
from datetime import datetime

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.covid_risk import CovidRisk
from dao.base import BaseLeague, BaseTeam, BasePlayer
from dao.espn import LeagueData as EspnLeagueData
from dao.fleaflicker import LeagueData as FleaflickerLeagueData
from dao.sleeper import LeagueData as SleeperLeagueData
from dao.yahoo import LeagueData as YahooLeagueData

logger = logging.getLogger(__name__)
logger.propagate = False

# Suppress webscraping debug logging
logger.setLevel(level=logging.INFO)


def user_week_input_validation(config, week, retrieved_current_week, season):

    current_date = datetime.today()
    current_year = current_date.year
    current_month = current_date.month

    # user input validation
    if week:
        week_for_report = week
    else:
        week_for_report = config.get("Configuration", "week_for_report")

    # only validate user week if report is being run for current season
    if current_year == int(season) or (current_year == (int(season) + 1) and current_month < 9):
        try:
            current_week = retrieved_current_week
            if week_for_report == "default":
                if (int(current_week) - 1) > 0:
                    week_for_report = str(int(current_week) - 1)
                else:
                    first_week_incomplete = input(
                        "The first week of the season is not yet complete. "
                        "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                    if first_week_incomplete == "y":
                        week_for_report = current_week
                    elif first_week_incomplete == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")

            elif 0 < int(week_for_report) < 18:
                if 0 < int(week_for_report) <= int(current_week) - 1:
                    week_for_report = week_for_report
                else:
                    incomplete_week = input(
                        "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                    if incomplete_week == "y":
                        week_for_report = week_for_report
                    elif incomplete_week == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")
            else:
                raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")
        except ValueError:
            raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")

    return int(week_for_report)


def league_data_factory(week_for_report, platform, league_id, game_id, season, config, base_dir, data_dir, save_data,
                        dev_offline):
    supported_platforms = [str(platform) for platform in config.get("Configuration", "supported_platforms").split(",")]

    if platform in supported_platforms:
        if platform == "yahoo":
            yahoo_league = YahooLeagueData(
                week_for_report,
                league_id,
                game_id,
                config,
                base_dir,
                data_dir,
                user_week_input_validation,
                save_data,
                dev_offline
            )
            return yahoo_league.map_data_to_base(BaseLeague)

        elif platform == "fleaflicker":
            fleaflicker_league = FleaflickerLeagueData(
                week_for_report,
                league_id,
                season,
                config,
                data_dir,
                user_week_input_validation,
                save_data,
                dev_offline
            )
            return fleaflicker_league.map_data_to_base(BaseLeague)

        elif platform == "sleeper":
            current_nfl_week = config.getint("Configuration", "current_week")
            if not week_for_report:
                input_str = "Sleeper does not provide the current NFL week in the API. Are you trying to generate a " \
                            "report for week {0} (current NFL week {1})? (y/n) -> ".format(
                                current_nfl_week - 1, current_nfl_week)
                time.sleep(1)
                is_current_week_correct = input(input_str)
                if is_current_week_correct == "n":
                    chosen_week = input("For which week would you like to generate a report? (1 - 17) -> ")
                    if 0 < int(chosen_week) < 18:
                        week_for_report = chosen_week
                    else:
                        raise ValueError("Invalid week number (must be 1 through 17). Please try running the report "
                                         "generator again with a valid current NFL week in \"config.ini\".")
                elif is_current_week_correct == "y":
                    pass
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")

            sleeper_league = SleeperLeagueData(
                week_for_report,
                league_id,
                season,
                config,
                data_dir,
                user_week_input_validation,
                save_data,
                dev_offline
            )
            return sleeper_league.map_data_to_base(BaseLeague)

        elif platform == "espn":
            espn_league = EspnLeagueData(
                week_for_report,
                league_id,
                season,
                config,
                base_dir,
                data_dir,
                user_week_input_validation,
                save_data,
                dev_offline
            )
            return espn_league.map_data_to_base(BaseLeague)

    else:
        logger.error(
            "Generating fantasy football reports for the \"{0}\" fantasy football platform is not currently supported. "
            "Please change your settings in config.ini and try again.".format(platform))
        sys.exit("...run aborted.")


def add_report_player_stats(config,
                            season,
                            metrics,
                            player,  # type: BasePlayer
                            bench_positions):
    player.bad_boy_crime = str()
    player.bad_boy_points = int()
    player.bad_boy_num_offenders = int()
    player.weight = float()
    player.tabbu = float()
    player.covid_risk = int()

    if player.selected_position not in bench_positions:

        if config.getboolean("Report", "league_bad_boy_rankings"):
            bad_boy_stats = metrics.get("bad_boy_stats")  # type: BadBoyStats
            player.bad_boy_crime = bad_boy_stats.get_player_bad_boy_crime(
                player.full_name, player.nfl_team_abbr, player.primary_position)
            player.bad_boy_points = bad_boy_stats.get_player_bad_boy_points(
                player.full_name, player.nfl_team_abbr, player.primary_position)
            player.bad_boy_num_offenders = bad_boy_stats.get_player_bad_boy_num_offenders(
                player.full_name, player.nfl_team_abbr, player.primary_position)

        if config.getboolean("Report", "league_beef_rankings"):
            beef_stats = metrics.get("beef_stats")  # type: BeefStats
            player.weight = beef_stats.get_player_weight(player.first_name, player.last_name, player.nfl_team_abbr)
            player.tabbu = beef_stats.get_player_tabbu(player.first_name, player.last_name, player.nfl_team_abbr)

        if config.getboolean("Report", "league_covid_risk_rankings") and int(season) >= 2020:
            covid_risk = metrics.get("covid_risk")  # type: CovidRisk
            player.covid_risk = covid_risk.get_player_covid_risk(
                player.full_name, player.nfl_team_abbr, player.primary_position)

    return player


def add_report_team_stats(config, team: BaseTeam, league: BaseLeague, week_counter, season, metrics_calculator, metrics, dq_ce,
                          inactive_players) -> BaseTeam:
    team.name = metrics_calculator.decode_byte_string(team.name)
    bench_positions = league.bench_positions

    for player in team.roster:
        add_report_player_stats(config, season, metrics, player, bench_positions)

    starting_lineup_points = round(
        sum([p.points for p in team.roster if p.selected_position not in bench_positions]), 2)
    # confirm total starting lineup points is the same as team points
    if round(team.points, 2) != (starting_lineup_points + team.home_field_advantage):
        logger.warning(
            "Team {0} points ({1}) are not equal to sum of team starting lineup points ({2}). Check data!".format(
                team.name, round(team.points, 2), starting_lineup_points))

    team.bench_points = round(sum([p.points for p in team.roster if p.selected_position in bench_positions]), 2)

    if config.getboolean("Report", "league_bad_boy_rankings"):
        team.bad_boy_points = 0
        team.worst_offense = None
        team.num_offenders = 0
        team.worst_offense_score = 0
        for p in team.roster:
            if p.selected_position not in bench_positions:
                if p.bad_boy_points > 0:
                    team.bad_boy_points += p.bad_boy_points
                    if p.selected_position == "DEF":
                        team.num_offenders += p.bad_boy_num_offenders
                    else:
                        team.num_offenders += 1
                    if p.bad_boy_points > team.worst_offense_score:
                        team.worst_offense = p.bad_boy_crime
                        team.worst_offense_score = p.bad_boy_points

    if config.getboolean("Report", "league_beef_rankings"):
        team.total_weight = sum([p.weight for p in team.roster if p.selected_position not in bench_positions])
        team.tabbu = sum([p.tabbu for p in team.roster if p.selected_position not in bench_positions])

    if config.getboolean("Report", "league_covid_risk_rankings") and int(season) >= 2020:
        team.total_covid_risk = sum([p.covid_risk for p in team.roster if p.selected_position not in bench_positions])

    team.positions_filled_active = [p.selected_position for p in team.roster if
                                    p.selected_position not in bench_positions]

    # calculate coaching efficiency and optimal score
    team.coaching_efficiency, team.optimal_points = metrics.get("coaching_efficiency").execute_coaching_efficiency(
        team.name,
        team.roster,
        team.points,
        team.positions_filled_active,
        int(week_counter),
        inactive_players,
        dq_eligible=dq_ce
    )

    # # retrieve luck and record
    team.luck = metrics.get("luck").get(team.team_id).get("luck")
    team.weekly_overall_record = metrics.get("luck").get(team.team_id).get("luck_record")
    team.record = metrics.get("records").get(team.team_id)

    return team


def get_player_game_time_statuses(week, league: BaseLeague):

    file_name = "week_" + str(week) + "-player_status_data.html"
    file_dir = os.path.join(league.data_dir, str(league.season), str(league.league_id), "week_" + str(week))
    file_path = os.path.join(file_dir, file_name)

    if not league.dev_offline:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) " \
                     "Version/13.0.2 Safari/605.1.15"
        headers = {
            "user-agent": user_agent
        }
        params = {
            "yr": str(league.season),
            "wk": str(week),
            "type": "reg"
        }

        response = requests.get("https://www.footballdb.com/transactions/injuries.html", headers=headers, params=params)

        html_soup = BeautifulSoup(response.text, "html.parser")
        logger.debug("Response URL: {0}".format(response.url))
        logger.debug("Response (HTML): {0}".format(html_soup))
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as data_in:
                html_soup = BeautifulSoup(data_in.read(), "html.parser")
        except FileNotFoundError:
            logger.error(
                "FILE {0} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                    file_path))
            sys.exit("...run aborted.")

    if league.save_data:
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        with open(file_path, "w", encoding="utf-8") as data_out:
            data_out.write(html_soup.prettify())

    return html_soup


def patch_http_connection_pool(**constructor_kwargs):
    """This allows you to override the default parameters of the HTTPConnectionPool constructor. For example, to
    increase the pool size to fix problems with "HttpConnectionPool is full, discarding connection" call this function
    with maxsize=16 (or whatever size you want to give to the connection pool).
    """
    class MyHTTPSConnectionPool(connectionpool.HTTPSConnectionPool):
        def __init__(self, *args, **kwargs):
            kwargs.update(constructor_kwargs)
            super(MyHTTPSConnectionPool, self).__init__(*args, **kwargs)

    poolmanager.pool_classes_by_scheme['https'] = MyHTTPSConnectionPool
