__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import os
import re
import shutil
import socket
import sys
import time
import colorama
from colorama import Fore, Style
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from git import Repo, TagReference, cmd
from urllib3 import connectionpool, poolmanager

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.covid_risk import CovidRisk
from dao.base import BaseLeague, BaseTeam, BasePlayer
from dao.espn import LeagueData as EspnLeagueData
from dao.fleaflicker import LeagueData as FleaflickerLeagueData
from dao.sleeper import LeagueData as SleeperLeagueData
from dao.yahoo import LeagueData as YahooLeagueData
from report.logger import get_logger
from utils.app_config_parser import AppConfigParser

logger = get_logger(__name__, propagate=False)

colorama.init()

current_date = datetime.today()
current_year = current_date.year
current_month = current_date.month


# function taken from https://stackoverflow.com/a/33117579 (written by 7h3rAm)
def active_network_connection(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as err:
        logger.error(err)
        return False


def get_valid_config():
    config = AppConfigParser()

    root_directory = os.path.dirname(os.path.dirname(__file__))

    config_file_path = os.path.join(root_directory, "config.ini")

    # set local config file (check for existence and access, stop app if does not exist or cannot access)
    if os.path.isfile(config_file_path):
        if os.access(config_file_path, mode=os.R_OK):
            logger.debug(
                "Configuration file \"config.ini\" available. Running Fantasy Football Metrics Weekly Report app...")
            config.read(config_file_path)
            return config
        else:
            logger.error(
                "Unable to access configuration file \"config.ini\". Please check that file permissions are properly set.")
            sys.exit("...run aborted.")
    else:
        logger.debug("Configuration file \"config.ini\" not found.")
        create_config = input(
            "{2}Configuration file \"config.ini\" not found. {1}Do you wish to create one? {0}({1}y{0}/{2}n{0}) -> {3}".format(
                Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
            ))
        if create_config == "y":
            return create_config_from_template(config, root_directory, config_file_path)
        if create_config == "n":
            logger.error(
                "Configuration file \"config.ini\" not found. Please make sure that it exists in project root directory.")
            sys.exit("...run aborted.")
        else:
            logger.warning("Please only select \"y\" or \"n\".")
            time.sleep(0.25)
            get_valid_config()


def create_config_from_template(config: AppConfigParser, root_directory, config_file_path, platform=None,
                                league_id=None, season=None, current_week=None):
    logger.debug("Creating \"config.ini\" file from template.")
    config_template_file = os.path.join(root_directory, "EXAMPLE-config.ini")
    config_file_path = shutil.copyfile(config_template_file, config_file_path)

    config.read(config_file_path)

    if not platform:
        logger.debug("Getting ")
        supported_platforms = config.get("Configuration", "supported_platforms").split(",")
        platform = input("{0}For which fantasy football platform are you generating a report? ({1}) -> {2}".format(
            Fore.GREEN, "/".join(supported_platforms), Style.RESET_ALL
        ))
        if platform not in supported_platforms:
            logger.warning("Please only select one of the following platforms: {0}".format(
                ", or ".join([", ".join(supported_platforms[:-1]), supported_platforms[-1]])))
            time.sleep(0.25)
            config = create_config_from_template(config, root_directory, config_file_path)
        logger.debug("Retrieved fantasy football platform for \"config.ini\": {0}".format(platform))

    config.set("Configuration", "platform", platform)

    if not league_id:
        league_id = input("{0}What is your league ID? -> {1}".format(Fore.GREEN, Style.RESET_ALL))
        logger.debug("Retrieved fantasy football league ID for \"config.ini\": {0}".format(league_id))

    config.set("Configuration", "league_id", league_id)

    if not season:
        season = input("{0}For which NFL season (starting year of season) are you generating reports? -> {1}".format(
            Fore.GREEN, Style.RESET_ALL
        ))
        try:
            if int(season) > current_year:
                logger.warning("This report cannot predict the future. Please only input a current or past NFL season.")
                time.sleep(0.25)
                config = create_config_from_template(config, root_directory, config_file_path, platform=platform,
                                                     league_id=league_id)
            elif int(season) < 2019 and platform == "espn":
                logger.warning("ESPN leagues prior to 2019 are not supported. Please select a later NFL season.")
                time.sleep(0.25)
                config = create_config_from_template(config, root_directory, config_file_path, platform=platform,
                                                     league_id=league_id)

        except ValueError:
            logger.warning("You must input a valid year in the format YYYY.")
            time.sleep(0.25)
            config = create_config_from_template(config, root_directory, config_file_path, platform=platform,
                                                 league_id=league_id)
        logger.debug("Retrieved fantasy football season for \"config.ini\": {0}".format(season))

    config.set("Configuration", "season", season)

    if not current_week:
        current_week = input(
            "{0}What is the current week of the NFL season? (week following the last complete week) -> {1}".format(
                Fore.GREEN, Style.RESET_ALL
            ))
        try:
            if int(current_week) < 0 or int(current_week) > 17:
                logger.warning(
                    "Week {0} is not a valid NFL week. Please select a week from 1 to 17.".format(current_week))
                time.sleep(0.25)
                config = create_config_from_template(config, root_directory, config_file_path, platform=platform,
                                                     league_id=league_id, season=season)
        except ValueError:
            logger.warning("You must input a valid integer to represent the current NFL week.")
            time.sleep(0.25)
            config = create_config_from_template(config, root_directory, config_file_path, platform=platform,
                                                 league_id=league_id, season=season)
        logger.debug("Retrieved current NFL week for \"config.ini\": {0}".format(current_week))

    config.set("Configuration", "current_week", current_week)

    with open(config_file_path, "w") as cf:
        config.write(cf, space_around_delimiters=True)

    return config


# function taken from https://stackoverflow.com/a/35585837 (written by morxa)
def git_ls_remote(url):
    remote_refs = {}
    g = cmd.Git()
    for ref in g.ls_remote(url).split('\n'):
        hash_ref_list = ref.split('\t')
        remote_refs[hash_ref_list[1]] = hash_ref_list[0]
    return remote_refs


def check_for_updates():
    logger.debug("Checking upstream remote for app updates.")
    project_repo = Repo(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if not active_network_connection():
        logger.info("No active network connection found. Unable to check for updates for the Fantasy Football Metrics "
                    "Weekly Report app.")
    else:
        version_tags = sorted(
            [tag_ref for tag_ref in project_repo.tags if hasattr(tag_ref.tag, "tagged_date")],
            key=lambda x: x.tag.tagged_date,
            reverse=True
        )

        last_local_version = None
        tag_ndx = 0
        while not last_local_version:
            next_tag = version_tags[tag_ndx]  # type: TagReference
            for commit in project_repo.iter_commits():
                if next_tag.commit == commit:
                    last_local_version = next_tag
            if not last_local_version:
                tag_ndx += 1

        origin_url = str(project_repo.remotes.origin.url)
        if "https" not in origin_url:
            origin_url = "https://github.com/{0}".format(str(project_repo.remotes.origin.url).split(":")[1])
        ls_remote = git_ls_remote(origin_url)

        regex = re.compile("[^0-9.]")
        remote_tags = sorted(
            set([(regex.sub("", ref), ref.replace("^{}", "").replace("refs/tags/", ""))
                 for ref in ls_remote.keys() if "tags" in ref]),
            key=lambda x: list(map(int, x[0].split("."))),
            reverse=True
        )
        last_remote_version = remote_tags[0][1]

        num_commits_behind_develop = len(list(project_repo.iter_commits("develop..origin/develop")))

        if str(last_local_version) == str(last_remote_version):
            local_version_color = Fore.GREEN
            remote_version_color = Fore.GREEN
        else:
            local_version_color = Fore.RED
            remote_version_color = Fore.YELLOW

        if num_commits_behind_develop > 0:
            num_commits_color = Fore.RED
        else:
            num_commits_color = Fore.GREEN

        if num_commits_behind_develop > 0:
            up_to_date_status_msg = "\n" \
                "{0}The Fantasy Football Metrics Weekly Report app is {1}OUT OF DATE:\n\n" \
                "  {2}Locally installed version: {3}\n" \
                "  {4}Latest version on develop: {5}\n" \
                "     {6}Commits behind develop: {7}\n\n" \
                "{8}Please update the app and re-run to generate a report.{9}".format(
                    Fore.YELLOW, Fore.RED,
                    local_version_color, last_local_version,
                    remote_version_color, last_remote_version,
                    num_commits_color, num_commits_behind_develop,
                    Fore.YELLOW, Style.RESET_ALL
            )
            logger.debug(up_to_date_status_msg)
            confirm_update = input(up_to_date_status_msg + " {1}Do you wish to update the app? {0}({1}y{0}/{2}n{0}) -> {3}".format(
                Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
            ))

            not_up_to_date_status_message = "Running {0} of app. Please update to {1} for the latest features, " \
                                            "improvements, and fixes.".format(
                                                last_local_version, last_remote_version)

            if confirm_update == "y":
                up_to_date = update_app(project_repo)
                if up_to_date:
                    logger.info("The Fantasy Football Metrics Weekly Report app has been successfully updated!")
                else:
                    logger.warning(not_up_to_date_status_message)
                return up_to_date

            if confirm_update == "n":
                logger.warning(not_up_to_date_status_message)
                return False
            else:
                logger.warning("Please only select \"y\" or \"n\".")
                time.sleep(0.25)
                check_for_updates()
        else:
            logger.info(
                "The Fantasy Football Metrics Weekly Report app is {0}up to date{1} and running {0}{2}{1}.".format(
                    Fore.GREEN, Fore.WHITE, last_local_version))
            return True


def update_app(repository: Repo):
    logger.debug("Updating app by pulling latest from develop.")

    diff = repository.index.diff(None)
    if len(diff) > 0:
        logger.error("There are changes to local files that could cause conflicts when updating the app "
                       "automatically.")
        logger.warning("Please update the app manually by running {0}git pull origin develop{1} and resolve any "
                       "conflicts by hand to update.".format(Fore.WHITE, Fore.YELLOW))
        sys.exit(2)

    response = repository.git.pull("origin", "develop")
    logger.debug(response)
    return True


def user_week_input_validation(config, week, retrieved_current_week, season):
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
                        "{0}The first week of the season is not yet complete. Are you sure you want to generate a "
                        "report for an incomplete week? ({1}y{0}/{2}n{0}) -> {3}".format(
                            Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
                        ))
                    if first_week_incomplete == "y":
                        week_for_report = current_week
                    elif first_week_incomplete == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select \"y\" or \"n\". Try running the report generator again.")

            elif 0 < int(week_for_report) < 18:
                if 0 < int(week_for_report) <= int(current_week) - 1:
                    week_for_report = week_for_report
                else:
                    incomplete_week = input(
                        "{0}Are you sure you want to generate a report for an incomplete week? ({1}y{0}/{2}n{0}) -> {3}".format(
                            Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
                        ))
                    if incomplete_week == "y":
                        week_for_report = week_for_report
                    elif incomplete_week == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select \"y\" or \"n\". Try running the report generator again.")
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
                input_str = "{0}Sleeper does not provide the current NFL week in the API. Are you trying to generate a " \
                            "report for week {4} (current NFL week {5})? ({1}y{0}/{2}n{0}) -> {3}".format(
                                Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL,
                                current_nfl_week - 1, current_nfl_week)
                time.sleep(1)
                is_current_week_correct = input(input_str)
                if is_current_week_correct == "n":
                    chosen_week = input("{0}For which week would you like to generate a report? (1 - 17) -> {1}".format(
                        Fore.GREEN, Style.RESET_ALL
                    ))
                    if 0 < int(chosen_week) < 18:
                        week_for_report = chosen_week
                    else:
                        raise ValueError("Invalid week number (must be 1 through 17). Please try running the report "
                                         "generator again with a valid current NFL week in \"config.ini\".")
                elif is_current_week_correct == "y":
                    pass
                else:
                    raise ValueError("Please only select \"y\" or \"n\". Try running the report generator again.")

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


def add_report_team_stats(config, team: BaseTeam, league: BaseLeague, week_counter, season, metrics_calculator, metrics,
                          dq_ce,
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
