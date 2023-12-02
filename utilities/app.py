__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import os
import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Union, Any

import colorama
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style
from git import Repo, TagReference, cmd
from urllib3 import connectionpool, poolmanager

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.metrics import CalculateMetrics
from dao.base import BaseLeague, BaseTeam, BasePlayer
from dao.platforms.cbs import LeagueData as CbsLeagueData
from dao.platforms.espn import LeagueData as EspnLeagueData
from dao.platforms.fleaflicker import LeagueData as FleaflickerLeagueData
from dao.platforms.sleeper import LeagueData as SleeperLeagueData
from dao.platforms.yahoo import LeagueData as YahooLeagueData
from utilities.logger import get_logger
from utilities.settings import settings
from utilities.utils import format_platform_display

logger = get_logger(__name__, propagate=False)

colorama.init()

NFL_SEASON_LENGTH = 18

current_date = datetime.today()
current_year = current_date.year
current_month = current_date.month


def user_week_input_validation(week: int, retrieved_current_week: int, season: int) -> int:
    # user input validation
    if week:
        week_for_report = week
    else:
        week_for_report = settings.week_for_report

    # only validate user week if report is being run for current season
    if current_year == int(season) or (current_year == (int(season) + 1) and current_month < 9):
        try:
            current_week = retrieved_current_week
            if week_for_report == "default":
                if (int(current_week) - 1) > 0:
                    week_for_report = str(int(current_week) - 1)
                else:
                    first_week_incomplete = input(
                        f"{Fore.YELLOW}The first week of the season is not yet complete. Are you sure you want to "
                        f"generate a report for an incomplete week? "
                        f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
                    )
                    if first_week_incomplete == "y":
                        week_for_report = current_week
                    elif first_week_incomplete == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select \"y\" or \"n\". Try running the report generator again.")

            elif 0 < int(week_for_report) <= NFL_SEASON_LENGTH:
                if 0 < int(week_for_report) <= int(current_week) - 1:
                    week_for_report = week_for_report
                else:
                    incomplete_week = input(
                        f"{Fore.YELLOW}Are you sure you want to generate a report for an incomplete week? "
                        f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
                    )
                    if incomplete_week == "y":
                        week_for_report = week_for_report
                    elif incomplete_week == "n":
                        raise ValueError("It is recommended that you do NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select \"y\" or \"n\". Try running the report generator again.")
            else:
                raise ValueError(
                    f"You must select either \"default\" or an integer from 1 to {NFL_SEASON_LENGTH} "
                    f"for the chosen week.")
        except ValueError:
            raise ValueError(
                f"You must select either \"default\" or an integer from 1 to {NFL_SEASON_LENGTH} for the chosen week.")

    return int(week_for_report)


def get_current_nfl_week(offline: bool) -> int:
    # api_url = "https://bet.rotoworld.com/api/nfl/calendar/game_count"
    api_url = "https://api.sleeper.app/v1/state/nfl"

    current_nfl_week = settings.current_nfl_week

    if not offline:
        logger.debug("Retrieving current NFL week from the Sleeper API.")

        try:
            nfl_weekly_info = requests.get(api_url).json()
            current_nfl_week = nfl_weekly_info.get("week")
        except (KeyError, ValueError) as e:
            logger.warning("Unable to retrieve current NFL week. Defaulting to value set in \".env\" file.")
            logger.debug(e)

    else:
        logger.debug("The Fantasy Football Metrics Weekly Report app is being run in offline mode. "
                     "The current NFL week will default to the value set in \".env\" file.")

    return current_nfl_week


def league_data_factory(base_dir: Path, data_dir: Path, platform: str,
                        game_id: Union[str, int], league_id: str, season: int, start_week: int, week_for_report: int,
                        save_data: bool, offline: bool) -> BaseLeague:
    if platform in settings.supported_platforms_list:
        if platform == "yahoo":
            yahoo_league = YahooLeagueData(
                base_dir,
                data_dir,
                game_id,
                league_id,
                season,
                start_week,
                week_for_report,
                get_current_nfl_week,
                user_week_input_validation,
                save_data,
                offline
            )
            return yahoo_league.map_data_to_base()

        elif platform == "fleaflicker":
            fleaflicker_league = FleaflickerLeagueData(
                None,
                data_dir,
                league_id,
                season,
                start_week,
                week_for_report,
                get_current_nfl_week,
                user_week_input_validation,
                save_data,
                offline
            )
            return fleaflicker_league.map_data_to_base()

        elif platform == "sleeper":
            sleeper_league = SleeperLeagueData(
                None,
                data_dir,
                league_id,
                season,
                start_week,
                week_for_report,
                get_current_nfl_week,
                user_week_input_validation,
                save_data,
                offline
            )
            return sleeper_league.map_data_to_base()

        elif platform == "espn":
            espn_league = EspnLeagueData(
                base_dir,
                data_dir,
                league_id,
                season,
                start_week,
                week_for_report,
                get_current_nfl_week,
                user_week_input_validation,
                save_data,
                offline
            )
            return espn_league.map_data_to_base()

        elif platform == "cbs":
            cbs_league = CbsLeagueData(
                base_dir,
                data_dir,
                league_id,
                season,
                start_week,
                week_for_report,
                get_current_nfl_week,
                user_week_input_validation,
                save_data,
                offline
            )
            return cbs_league.map_data_to_base()

    else:
        logger.error(
            f"Generating fantasy football reports for the \"{format_platform_display(platform)}\" fantasy football "
            f"platform is not currently supported. Please change the settings in your .env file and try again."
        )
        sys.exit(1)


def add_report_player_stats(metrics: Dict[str, Any], player: BasePlayer,
                            bench_positions: List[str]) -> BasePlayer:
    player.bad_boy_crime = str()
    player.bad_boy_points = int()
    player.bad_boy_num_offenders = int()
    player.weight = float()
    player.tabbu = float()

    if player.selected_position not in bench_positions:

        if settings.report_settings.league_bad_boy_rankings_bool:
            bad_boy_stats: BadBoyStats = metrics.get("bad_boy_stats")
            player.bad_boy_crime = bad_boy_stats.get_player_bad_boy_crime(
                player.first_name, player.last_name, player.nfl_team_abbr, player.primary_position
            )
            player.bad_boy_points = bad_boy_stats.get_player_bad_boy_points(
                player.first_name, player.last_name, player.nfl_team_abbr, player.primary_position
            )
            player.bad_boy_num_offenders = bad_boy_stats.get_player_bad_boy_num_offenders(
                player.first_name, player.last_name, player.nfl_team_abbr, player.primary_position
            )

        if settings.report_settings.league_beef_rankings_bool:
            beef_stats: BeefStats = metrics.get("beef_stats")
            player.weight = beef_stats.get_player_weight(player.first_name, player.last_name, player.nfl_team_abbr)
            player.tabbu = beef_stats.get_player_tabbu(player.first_name, player.last_name, player.nfl_team_abbr)

    return player


def add_report_team_stats(team: BaseTeam, league: BaseLeague, week_counter: int, metrics_calculator: CalculateMetrics,
                          metrics: Dict[str, Any], dq_ce: bool, inactive_players: List[str]) -> BaseTeam:
    team.name = metrics_calculator.decode_byte_string(team.name)
    bench_positions = league.bench_positions

    for player in team.roster:
        add_report_player_stats(metrics, player, bench_positions)

    starting_lineup_points = round(
        sum([p.points for p in team.roster if p.selected_position not in bench_positions]), 2)
    # confirm total starting lineup points is the same as team points
    if round(team.points, 2) != (starting_lineup_points + team.home_field_advantage_points):
        logger.warning(
            f"Team {team.name} retrieved points ({round(team.points, 2)}) are not equal to calculated sum of team "
            f"starting lineup points ({starting_lineup_points}). Check data!"
        )

    team.bench_points = round(sum([p.points for p in team.roster if p.selected_position in bench_positions]), 2)

    if settings.report_settings.league_bad_boy_rankings_bool:
        team.bad_boy_points = 0
        team.worst_offense = None
        team.num_offenders = 0
        team.worst_offense_score = 0
        for p in team.roster:
            if p.selected_position not in bench_positions:
                if p.bad_boy_points > 0:
                    team.bad_boy_points += p.bad_boy_points
                    if p.selected_position == "D/ST":
                        team.num_offenders += p.bad_boy_num_offenders
                    else:
                        team.num_offenders += 1
                    if p.bad_boy_points > team.worst_offense_score:
                        team.worst_offense = p.bad_boy_crime
                        team.worst_offense_score = p.bad_boy_points

    if settings.report_settings.league_beef_rankings_bool:
        team.total_weight = sum([p.weight for p in team.roster if p.selected_position not in bench_positions])
        team.tabbu = sum([p.tabbu for p in team.roster if p.selected_position not in bench_positions])

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


def get_player_game_time_statuses(week: int, league: BaseLeague):
    file_name = f"week_{week}-player_status_data.html"
    file_dir = Path(league.data_dir) / str(league.season) / str(league.league_id) / f"week_{week}"
    file_path = Path(file_dir) / file_name

    if not league.offline:
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/13.0.2 Safari/605.1.15"
        )
        headers = {
            "user-agent": user_agent
        }
        params = {
            "yr": str(league.season),
            "wk": str(week),
            "type": "reg"
        }

        response = requests.get(
            "https://www.footballdb.com/transactions/injuries.html", headers=headers, params=params
        )

        html_soup = BeautifulSoup(response.text, "html.parser")
        logger.debug(f"Response URL: {response.url}")
        logger.debug(f"Response (HTML): {html_soup}")
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as data_in:
                html_soup = BeautifulSoup(data_in.read(), "html.parser")
        except FileNotFoundError:
            logger.error(
                f"FILE {file_path} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!"
            )
            sys.exit(1)

    if league.save_data:
        if not Path(file_dir).exists():
            os.makedirs(file_dir)

        with open(file_path, "w", encoding="utf-8") as data_out:
            data_out.write(html_soup.prettify())

    return html_soup


# function taken from https://stackoverflow.com/a/33117579 (written by 7h3rAm)
def active_network_connection(host: str = "8.8.8.8", port: int = 53, timeout: int = 3):
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


def patch_http_connection_pool(**constructor_kwargs):
    """This allows you to override the default parameters of the HTTPConnectionPool constructor. For example, to
    increase the pool size to fix problems with "HttpConnectionPool is full, discarding connection" call this function
    with maxsize=16 (or whatever size you want to give to the connection pool).
    """

    class MyHTTPSConnectionPool(connectionpool.HTTPSConnectionPool):
        def __init__(self, *args, **kwargs):
            kwargs.update(constructor_kwargs)
            super(MyHTTPSConnectionPool, self).__init__(*args, **kwargs)

    # noinspection PyUnresolvedReferences
    poolmanager.pool_classes_by_scheme['https'] = MyHTTPSConnectionPool


# function taken from https://stackoverflow.com/a/35585837 (written by morxa)
def git_ls_remote(url: str):
    remote_refs = {}
    git = cmd.Git()
    for ref in git.ls_remote(url).split('\n'):
        hash_ref_list = ref.split('\t')
        remote_refs[hash_ref_list[1]] = hash_ref_list[0]
    return remote_refs


def check_for_updates(use_default: bool = False):
    if not active_network_connection():
        logger.info(
            "No active network connection found. Unable to check for updates for the Fantasy Football Metrics Weekly "
            "Report app."
        )
    else:
        logger.debug("Checking upstream remote for app updates.")
        project_repo = Repo(Path(__file__).parent.parent)

        origin_url = str(project_repo.remotes.origin.url)
        origin_url_with_https = None
        # temporarily convert git remote URL from SSH to HTTPS if necessary
        if "https" not in origin_url:
            origin_url_with_https = f"https://github.com/{str(project_repo.remotes.origin.url).split(':')[1]}"
            project_repo.remote(name="origin").set_url(origin_url_with_https)

        project_repo.remote(name="origin").update()
        project_repo.remote(name="origin").fetch(prune=True)

        version_tags = sorted(
            [tag_ref for tag_ref in project_repo.tags if hasattr(tag_ref.tag, "tagged_date")],
            key=lambda x: x.tag.tagged_date,
            reverse=True
        )

        last_local_version = None
        tag_ndx = 0
        while not last_local_version:
            next_tag: TagReference = version_tags[tag_ndx]
            for commit in project_repo.iter_commits():
                if next_tag.commit == commit:
                    last_local_version = next_tag
            if not last_local_version:
                tag_ndx += 1

        ls_remote = git_ls_remote(origin_url_with_https or origin_url)
        regex = re.compile("[^0-9.]")
        remote_tags = sorted(
            set([(regex.sub("", ref), ref.replace("^{}", "").replace("refs/tags/", ""))
                 for ref in ls_remote.keys() if "tags" in ref]),
            key=lambda x: list(map(int, x[0].split("."))),
            reverse=True
        )
        last_remote_version = remote_tags[0][1]

        target_branch = "main"
        active_branch = project_repo.active_branch.name
        if active_branch != target_branch:
            if not use_default:
                switch_branch = input(
                    f"{Fore.YELLOW}You are {Fore.RED}not{Fore.YELLOW} on the deployment branch "
                    f"({Fore.GREEN}\"{target_branch}\"{Fore.YELLOW}) of the Fantasy Football Metrics Weekly Report "
                    f"app. Do you want to switch to the {Fore.GREEN}\"{target_branch}\"{Fore.YELLOW} branch? "
                    f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
                )

                if switch_branch == "y":
                    project_repo.git.checkout(target_branch)
                elif switch_branch == "n":
                    logger.warning(
                        f"Running the app on a branch that is not \"{target_branch}\" could result in unexpected and "
                        f"potentially incorrect output."
                    )
                else:
                    logger.warning("You must select either \"y\" or \"n\".")
                    project_repo.remote(name="origin").set_url(origin_url)
                    return check_for_updates(use_default)
            else:
                logger.info("Use-default is set to \"true\". Automatically switching to deployment branch \"main\".")
                project_repo.git.checkout(target_branch)

        num_commits_behind = len(list(project_repo.iter_commits(f"{target_branch}..origin/{target_branch}")))

        if str(last_local_version) == str(last_remote_version):
            local_version_color = Fore.GREEN
            remote_version_color = Fore.GREEN
        else:
            local_version_color = Fore.RED
            remote_version_color = Fore.YELLOW

        if num_commits_behind > 0:
            num_commits_color = Fore.RED
        else:
            num_commits_color = Fore.GREEN

        if num_commits_behind > 0:
            up_to_date_status_msg = (
                f"\n"
                f"{Fore.YELLOW}The Fantasy Football Metrics Weekly Report app is {Fore.RED}OUT OF DATE:\n\n"
                f"  {local_version_color}Locally installed version: {last_local_version}\n"
                f"     {remote_version_color}Latest version on {target_branch}: {last_remote_version}\n"
                f"        {num_commits_color}Commits behind {target_branch}: {num_commits_behind}\n\n"
                f"{Fore.YELLOW}Please update the app and re-run to generate a report.{Style.RESET_ALL}"
            )
            logger.debug(up_to_date_status_msg)
            confirm_update = input(
                f"{up_to_date_status_msg} {Fore.GREEN}Do you wish to update the app? "
                f"{Fore.YELLOW}({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
            )

            not_up_to_date_status_message = (
                f"Running {last_local_version} of app. Please update to {last_remote_version} for the latest "
                f"features, improvements, and fixes."
            )

            if confirm_update == "y":
                up_to_date = update_app(project_repo)
                if up_to_date:
                    logger.info("The Fantasy Football Metrics Weekly Report app has been successfully updated!")
                else:
                    logger.warning(not_up_to_date_status_message)
                project_repo.remote(name="origin").set_url(origin_url)
                return up_to_date

            if confirm_update == "n":
                logger.warning(not_up_to_date_status_message)
                project_repo.remote(name="origin").set_url(origin_url)
                return False
            else:
                logger.warning("Please only select \"y\" or \"n\".")
                time.sleep(0.25)
                check_for_updates()
        else:
            logger.info(
                f"The Fantasy Football Metrics Weekly Report app is {Fore.GREEN}up to date{Fore.WHITE} and running "
                f"{Fore.GREEN}{last_local_version}{Fore.WHITE}."
            )
            project_repo.remote(name="origin").set_url(origin_url)
            return True


def update_app(repository: Repo):
    logger.debug("Updating app by pulling latest from main.")

    diff = repository.index.diff(None)
    if len(diff) > 0:
        logger.error(
            "There are changes to local files that could cause conflicts when updating the app automatically."
        )
        logger.warning(
            f"Please update the app manually by running {Fore.WHITE}git pull origin main{Fore.YELLOW} and resolve any "
            f"conflicts by hand to update."
        )
        sys.exit(2)

    response = repository.git.pull("origin", "main")
    logger.debug(response)
    return True


if __name__ == "__main__":
    local_current_nfl_week = get_current_nfl_week(offline=False)
    logger.info(f"Local current NFL week: {local_current_nfl_week}")
