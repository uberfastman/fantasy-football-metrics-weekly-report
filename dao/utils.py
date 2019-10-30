__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os
import sys

import requests
from bs4 import BeautifulSoup
from urllib3 import connectionpool, poolmanager

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from dao.base import BaseLeague, BaseTeam, BasePlayer
from dao.espn import LeagueData as EspnLeagueData
from dao.fleaflicker import LeagueData as FleaflickerLeagueData
from dao.sleeper import LeagueData as SleeperLeagueData
from dao.yahoo import LeagueData as YahooLeagueData

logger = logging.getLogger(__name__)
logger.propagate = False

# Suppress webscraping debug logging
logger.setLevel(level=logging.INFO)


def user_week_input_validation(config, week, retrieved_current_week):
    # user input validation
    if week:
        week_for_report = week
    else:
        week_for_report = config.get("Configuration", "week_for_report")
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
            fleaflicker_league = SleeperLeagueData(
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
            "Generating fantasy football reports for the \"{}\" fantasy football platform is not currently supported. "
            "Please change your settings in config.ini and try again.".format(platform))
        sys.exit("...run aborted.")


def add_report_player_stats(player,  # type: BasePlayer
                            bench_positions,
                            metrics):
    player.bad_boy_crime = str()
    player.bad_boy_points = int()
    player.bad_boy_num_offenders = int()
    player.weight = float()
    player.tabbu = float()

    if player.selected_position not in bench_positions:
        bad_boy_stats = metrics.get("bad_boy_stats")  # type: BadBoyStats
        player.bad_boy_crime = bad_boy_stats.get_player_bad_boy_crime(
            player.full_name, player.nfl_team_abbr, player.primary_position)
        player.bad_boy_points = bad_boy_stats.get_player_bad_boy_points(
            player.full_name, player.nfl_team_abbr, player.primary_position)
        player.bad_boy_num_offenders = bad_boy_stats.get_player_bad_boy_num_offenders(
            player.full_name, player.nfl_team_abbr, player.primary_position)

        beef_stats = metrics.get("beef_stats")  # type: BeefStats
        player.weight = beef_stats.get_player_weight(player.first_name, player.last_name, player.nfl_team_abbr)
        player.tabbu = beef_stats.get_player_tabbu(player.first_name, player.last_name, player.nfl_team_abbr)

    return player


def add_report_team_stats(team: BaseTeam, league: BaseLeague, week_counter, metrics_calculator, metrics, dq_ce,
                          inactive_players):
    team.name = metrics_calculator.decode_byte_string(team.name)
    bench_positions = league.get_roster_slots_by_type().get("positions_bench")

    for player in team.roster:
        add_report_player_stats(player, bench_positions, metrics)

    starting_lineup_points = round(
        sum([p.points for p in team.roster if p.selected_position not in bench_positions]), 2)
    # confirm total starting lineup points is the same as team points
    if team.points != starting_lineup_points:
        logger.warning(
            "Team {} points ({}) are not equal to sum of team starting lineup points ({}). Check data!".format(
                team.name, team.points, starting_lineup_points))

    team.bench_points = round(sum([p.points for p in team.roster if p.selected_position in bench_positions]), 2)

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

    team.total_weight = sum([p.weight for p in team.roster if p.selected_position not in bench_positions])
    team.tabbu = sum([p.tabbu for p in team.roster if p.selected_position not in bench_positions])
    team.positions_filled_active = [p.selected_position for p in team.roster if
                                    p.selected_position not in bench_positions]

    # calculate coaching efficiency
    team.coaching_efficiency = metrics.get("coaching_efficiency").execute_coaching_efficiency(
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
        logger.debug("Response URL: {}".format(response.url))
        logger.debug("Response (HTML): {}".format(html_soup))
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as data_in:
                html_soup = BeautifulSoup(data_in.read(), "html.parser")
        except FileNotFoundError:
            logger.error(
                "FILE {} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
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
