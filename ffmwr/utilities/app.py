import os
import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import colorama
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style

from ffmwr.calculate.coaching_efficiency import CoachingEfficiency
from ffmwr.calculate.metrics import CalculateMetrics
from ffmwr.dao.platforms.base.platform import BasePlatform
from ffmwr.dao.platforms.espn import ESPNPlatform
from ffmwr.features.bad_boy import BadBoyFeature
from ffmwr.features.beef import BeefFeature
from ffmwr.features.high_roller import HighRollerFeature
from ffmwr.models.base.model import BaseLeague, BasePlayer, BaseTeam
from ffmwr.utilities.constants import (nfl_team_names_to_abbreviations,
                                       prohibited_statuses)
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import (AppSettings,
                                      get_app_settings_from_env_file)
from ffmwr.utilities.utils import (format_platform_display,
                                   generate_normalized_player_key,
                                   get_data_from_web)

logger = get_logger(__name__, propagate=False)

colorama.init()


def user_week_input_validation(
    settings: AppSettings, week: int, retrieved_current_week: int, season: int
) -> int:
    # user input validation
    if week:
        week_for_report = week
    else:
        week_for_report = settings.week_for_report

    current_date = datetime.today()
    current_year = current_date.year
    current_month = current_date.month
    # only validate user week if report is being run for current season
    if current_year == int(season) or (
        current_year == (int(season) + 1) and current_month < 9
    ):
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
                        raise ValueError(
                            "It is recommended that you NOT generate a report for an incomplete week."
                        )
                    else:
                        raise ValueError(
                            'Please only select "y" or "n". Try running the report generator again.'
                        )

            elif 0 < int(week_for_report) <= settings.nfl_season_length:
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
                        raise ValueError(
                            "It is recommended that you do NOT generate a report for an incomplete week."
                        )
                    else:
                        raise ValueError(
                            'Please only select "y" or "n". Try running the report generator again.'
                        )
            else:
                raise ValueError(
                    f'You must select either "default" or an integer from 1 to {settings.nfl_season_length} '
                    f"for the chosen week."
                )
        except ValueError:
            raise ValueError(
                f'You must select either "default" or an integer from 1 to {settings.nfl_season_length} for the chosen '
                f"week."
            )

    return int(week_for_report)


def get_current_nfl_week(settings: AppSettings, offline: bool) -> int:
    api_url = "https://api.sleeper.app/v1/state/nfl"

    current_nfl_week = settings.current_nfl_week

    if not offline:
        logger.debug("Retrieving current NFL week from the Sleeper API.")

        try:
            nfl_weekly_info = requests.get(api_url).json()
            current_nfl_week = nfl_weekly_info.get("leg")
        except (KeyError, ValueError) as e:
            logger.warning(
                'Unable to retrieve current NFL week. Defaulting to value set in ".env" file.'
            )
            logger.debug(e)

    else:
        logger.debug(
            "The Fantasy Football Metrics Weekly Report app is being run in offline mode. "
            'The current NFL week will default to the value set in ".env" file.'
        )

    return current_nfl_week


def platform_data_factory(
    settings: AppSettings,
    root_dir: Path,
    data_dir: Path,
    platform: str,
    game_id: Union[str, int],
    league_id: str,
    season: int,
    start_week: int,
    week_for_report: int,
    save_data: bool,
    offline: bool,
) -> BasePlatform:
    if platform == "espn":
        return ESPNPlatform(
            settings,
            root_dir,
            data_dir,
            league_id,
            season,
            start_week,
            week_for_report,
            get_current_nfl_week,
            user_week_input_validation,
            save_data,
            offline,
        )
    else:
        logger.error(
            f'Only ESPN platform is supported. Platform "{platform}" is not supported.'
        )
        sys.exit(1)


def add_report_player_stats(
    settings: AppSettings,
    metrics: Dict[str, Any],
    player: BasePlayer,
    bench_positions: List[str],
) -> BasePlayer:
    player.bad_boy_crime = str()
    player.bad_boy_points = int()
    player.bad_boy_num_offenders = int()
    player.beef_weight = float()
    player.beef_tabbu = float()
    player.high_roller_worst_violation = str()
    player.high_roller_worst_violation_fine = float()
    player.high_roller_fines_total = float()
    player.high_roller_num_violators = int()

    if player.selected_position not in bench_positions:
        if settings.report_settings.league_bad_boy_rankings_bool:
            bad_boy_stats: BadBoyFeature = metrics.get("bad_boy_stats")
            player.bad_boy_crime = bad_boy_stats.get_player_bad_boy_crime(
                player.first_name,
                player.last_name,
                player.nfl_team_abbr,
                player.primary_position,
            )
            player.bad_boy_points = bad_boy_stats.get_player_bad_boy_points(
                player.first_name,
                player.last_name,
                player.nfl_team_abbr,
                player.primary_position,
            )
            player.bad_boy_num_offenders = (
                bad_boy_stats.get_player_bad_boy_num_offenders(
                    player.first_name,
                    player.last_name,
                    player.nfl_team_abbr,
                    player.primary_position,
                )
            )

        if settings.report_settings.league_beef_rankings_bool:
            beef_stats: BeefFeature = metrics.get("beef_stats")
            player.beef_weight = beef_stats.get_player_weight(
                player.first_name,
                player.last_name,
                player.nfl_team_abbr,
                player.primary_position,
            )
            player.beef_tabbu = beef_stats.get_player_tabbu(
                player.first_name,
                player.last_name,
                player.nfl_team_abbr,
                player.primary_position,
            )

        if settings.report_settings.league_high_roller_rankings_bool:
            high_roller_stats: HighRollerFeature = metrics.get("high_roller_stats")
            player.high_roller_worst_violation = (
                high_roller_stats.get_player_worst_violation(
                    player.first_name,
                    player.last_name,
                    player.nfl_team_abbr,
                    player.primary_position,
                )
            )
            player.high_roller_worst_violation_fine = (
                high_roller_stats.get_player_worst_violation_fine(
                    player.first_name,
                    player.last_name,
                    player.nfl_team_abbr,
                    player.primary_position,
                )
            )
            player.high_roller_fines_total = high_roller_stats.get_player_fines_total(
                player.first_name,
                player.last_name,
                player.nfl_team_abbr,
                player.primary_position,
            )
            player.high_roller_num_violators = (
                high_roller_stats.get_player_num_violators(
                    player.first_name,
                    player.last_name,
                    player.nfl_team_abbr,
                    player.primary_position,
                )
            )

    return player


def add_report_team_stats(
    settings: AppSettings,
    team: BaseTeam,
    league: BaseLeague,
    week_counter: int,
    metrics_calculator: CalculateMetrics,
    metrics: Dict[str, Any],
    dq_ce: bool,
    inactive_players: List[str],
) -> BaseTeam:
    team.name = metrics_calculator.decode_byte_string(team.name)
    bench_positions = league.bench_positions

    for player in team.roster:
        add_report_player_stats(settings, metrics, player, bench_positions)

    starting_lineup_points = round(
        sum(
            [
                p.points
                for p in team.roster
                if p.selected_position not in bench_positions
            ]
        ),
        2,
    )
    # confirm total starting lineup points is the same as team points
    if round(team.points, 2) != (
        starting_lineup_points + team.home_field_advantage_points
    ):
        logger.warning(
            f"Team {team.name} retrieved points ({round(team.points, 2)}) are not equal to calculated sum of team "
            f"starting lineup points ({starting_lineup_points}). Check data!"
        )

    team.bench_points = round(
        sum([p.points for p in team.roster if p.selected_position in bench_positions]),
        2,
    )

    if settings.report_settings.league_bad_boy_rankings_bool:
        team.bad_boy_points = 0
        team.worst_offense = None
        team.num_offenders = 0
        team.worst_offense_score = 0
        p: BasePlayer
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
        team.total_weight = sum(
            [
                p.beef_weight
                for p in team.roster
                if p.selected_position not in bench_positions
            ]
        )
        team.tabbu = sum(
            [
                p.beef_tabbu
                for p in team.roster
                if p.selected_position not in bench_positions
            ]
        )

    if settings.report_settings.league_high_roller_rankings_bool:
        p: BasePlayer
        for p in team.roster:
            if p.selected_position not in bench_positions:
                if p.high_roller_fines_total > 0:
                    team.fines_total += p.high_roller_fines_total
                    if p.selected_position == "D/ST":
                        team.num_violators += p.high_roller_num_violators
                    else:
                        team.num_violators += 1
                    if p.high_roller_fines_total > team.worst_violation_fine:
                        team.worst_violation = p.high_roller_worst_violation
                        team.worst_violation_fine = p.high_roller_worst_violation_fine

    team.positions_filled_active = [
        p.selected_position
        for p in team.roster
        if p.selected_position not in bench_positions
    ]

    # calculate coaching efficiency and optimal score
    coaching_efficiency: CoachingEfficiency = metrics.get("coaching_efficiency")
    team.coaching_efficiency, team.optimal_points = (
        coaching_efficiency.execute_coaching_efficiency(
            team.name,
            team.roster,
            team.points,
            team.positions_filled_active,
            int(week_counter),
            inactive_players,
            dq_eligible=dq_ce,
        )
    )

    # # retrieve luck and record
    team.luck = metrics.get("luck").get(team.team_id).get("luck")
    team.weekly_overall_record = (
        metrics.get("luck").get(team.team_id).get("luck_record")
    )
    team.record = metrics.get("records").get(team.team_id)

    return team


class InjuryReportPlayer(object):
    def __init__(
        self,
        full_name: str,
        nfl_team_abbr: str,
        href: str,
        game_status: str,
        game_status_date_str: str,
        season: int,
        player_data_dir: Path,
    ):
        self.full_name: str = full_name
        self.nfl_team_abbr: str = nfl_team_abbr
        self.url: str = f"https://www.footballdb.com{href}/gamelogs/{season}"
        self.team_abbr: Optional[str] = None
        self.jersey_number: Optional[int] = None
        self.game_status: str = game_status
        self.game_status_date: datetime = datetime.strptime(
            f"{game_status_date_str}/{season}", "%m/%d/%Y"
        )

        self.player_data_file_path: Path = (
            player_data_dir / f"{href.split('/')[-1]}.html"
        )

    def __str__(self):
        return f"InjuryReportPlayer({', '.join([f'{k}={v}' for k, v in vars(self).items()])})"

    def set_player_team_abbr(self, team_abbr: str) -> None:
        self.team_abbr = team_abbr

    def set_player_jersey_number(self, jersey_number: int) -> None:
        self.jersey_number = jersey_number


def get_inactive_players(week: int, league: BaseLeague) -> List[str]:
    injured_players_url = "https://www.footballdb.com/transactions/injuries.html"

    data_dir = league.data_dir / f"week_{week}" / "players_status_data"
    data_file_path = data_dir / "player_status_data.html"
    player_data_dir = data_dir / "player_statuses"

    headers = {
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/13.0.2 Safari/605.1.15"
        )
    }

    logger.info(
        f"{'Retrieving' if not league.offline else 'Loading'} inactive player data for week {week} from "
        f"{injured_players_url if not league.offline else data_file_path}..."
    )

    start = datetime.now()

    data_retrieved_from_web = False
    if not league.offline:
        params = {"yr": str(league.season), "wk": str(week), "type": "reg"}

        response = requests.get(injured_players_url, headers=headers, params=params)

        html_soup = BeautifulSoup(response.text, "html.parser")
        logger.debug(f"Response URL: {response.url}")
        logger.debug(f"Response (HTML): {html_soup}")
        data_retrieved_from_web = True
    else:
        try:
            with open(data_file_path, "r", encoding="utf-8") as data_in:
                html_soup = BeautifulSoup(data_in.read(), "html.parser")
        except FileNotFoundError:
            logger.error(
                f"FILE {data_file_path} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!"
            )
            sys.exit(1)

    if league.save_data:
        if not Path(data_dir).exists():
            os.makedirs(data_dir)

        with open(data_file_path, "w", encoding="utf-8") as data_out:
            data_out.write(html_soup.prettify())

    injured_players: Dict[str, InjuryReportPlayer] = {}
    injury_report_players_to_check: Dict[str, InjuryReportPlayer] = {}
    injured_players_html = html_soup.find_all("div", {"class": ["teamsectlabel", "tr"]})
    for player in injured_players_html:
        if "teamsectlabel" in player["class"]:
            player_team_abbr = nfl_team_names_to_abbreviations[
                player.find("b").text.strip()
            ]
        else:
            player_info = player.find("a")
            player_game_status = player.find("div", {"class": "td w20 hidden-xs"}).find(
                "b"
            )  # bolded game status

            if player_game_status:
                player_game_status_date_str = re.search(
                    r"(?<=\()(.+/.+)(?=\))",  # match strings with a forward slash between parentheses
                    player.find(
                        "div", {"class": "td w20 hidden-xs"}
                    ).text,  # text with game status, date, and opponent
                ).group(0)

                # noinspection PyUnboundLocalVariable
                injury_report_player = InjuryReportPlayer(
                    full_name=player_info.text.strip(),
                    nfl_team_abbr=player_team_abbr,  # this will always be defined since team titles come before players
                    href=player_info.get("href"),
                    game_status=player_game_status,
                    game_status_date_str=player_game_status_date_str,
                    season=league.season,
                    player_data_dir=player_data_dir,
                )

                injury_report_player.game_status = player_game_status.text.strip()
                if injury_report_player.game_status == "Out":
                    injured_players[injury_report_player.url] = injury_report_player
                else:
                    injury_report_players_to_check[injury_report_player.url] = (
                        injury_report_player
                    )

    if not league.offline:
        player_pages = get_data_from_web(
            [
                player_url
                for player_url, player in injury_report_players_to_check.items()
                if player.game_status == "Questionable"
                or player.game_status == "Doubtful"
            ],
            "GET",
            headers,
            return_responses_as_body_strings=True,
        )
    else:
        player_pages = {}
        for player_url, player in injury_report_players_to_check.items():
            try:
                with open(
                    player.player_data_file_path, "r", encoding="utf-8"
                ) as player_html_in:
                    player_pages[player_url] = player_html_in.read()
            except FileNotFoundError:
                logger.error(
                    f"FILE {player.player_data_file_path} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING "
                    f"PREVIOUSLY SAVED DATA!"
                )
                sys.exit(1)

    for player_url, player_page_html in player_pages.items():
        injury_report_player = injury_report_players_to_check[player_url]

        player_page_html_soup = BeautifulSoup(player_page_html, "html.parser")

        player_banner = player_page_html_soup.find("div", {"id": "playerbanner"}).find(
            "b"
        )
        player_team = player_banner.find("a").text.strip()
        if player_team:
            injury_report_player.set_player_team_abbr(
                nfl_team_names_to_abbreviations[player_team]
            )
        player_number_info = re.search("#[0-9]{1,2}", player_banner.text.strip())
        if player_number_info:
            injury_report_player.set_player_jersey_number(
                int(player_number_info.group()[1:])
            )

        # retrieve data table where data title includes the substring "Game Logs"
        game_logs_table = player_page_html_soup.find(
            "div", {"data-title": re.compile("Game Logs")}
        )
        for row in game_logs_table.find_all("tr"):
            if not {"header", "preseason", "row_playerstats"}.intersection(
                set(row.get("class"))
            ):
                game_date = datetime.strptime(
                    row.find("td", {"class": "center nowrap"}).text, "%m/%d/%y"
                )
                game_no_stat_msg = row.find("div", {"class": "nostatmsg"})

                if (
                    game_date >= injury_report_player.game_status_date
                    and game_no_stat_msg
                ):
                    game_no_stat_msg = game_no_stat_msg.text.strip()
                    if any(
                        game_no_stat_msg in status
                        for status in prohibited_statuses.values()
                    ):
                        injured_players[player_url] = injury_report_player

    if league.save_data:
        if not Path(player_data_dir).exists():
            os.makedirs(player_data_dir)

        for player_url, player_page_html in player_pages.items():
            with open(
                injury_report_players_to_check[player_url].player_data_file_path,
                "w",
                encoding="utf-8",
            ) as player_html_out:
                player_html_out.write(player_page_html)

    logger.info(
        f"...{'retrieved' if data_retrieved_from_web else 'loaded'} {len(injured_players)} injured players from the "
        f"week {week} injury report in {datetime.now() - start}."
    )

    return [
        generate_normalized_player_key(player.full_name, player.nfl_team_abbr)
        for player in sorted(injured_players.values(), key=lambda x: x.full_name)
    ]


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


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(
        local_root_directory / ".env"
    )

    local_current_nfl_week = get_current_nfl_week(
        settings=local_settings, offline=False
    )
    logger.info(f"Local current NFL week: {local_current_nfl_week}")

    local_league: BaseLeague = BaseLeague(
        local_settings,
        local_settings.platform.lower(),
        local_settings.league_id,
        local_settings.season,
        local_settings.current_nfl_week,
        local_root_directory,
        local_root_directory / "output" / "data",
        True,
        False,
    )

    local_inactive_players = get_inactive_players(
        local_settings.current_nfl_week, local_league
    )
    logger.info(f"Local inactive players: {local_inactive_players}")
