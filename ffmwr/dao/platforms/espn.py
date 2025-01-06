__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
import os
import re
import time
from getpass import getpass
from pathlib import Path
from statistics import median
from typing import Callable, List

import colorama
from colorama import Fore, Style
from espn_api.football.box_player import BoxPlayer
from espn_api.football.box_score import BoxScore
from espn_api.football.constant import POSITION_MAP
from espn_api.football.league import League, Team
from espn_api.football.settings import Settings
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from ffmwr.models.base.model import BaseManager, BaseMatchup, BasePlayer, BaseRecord, BaseStat, BaseTeam
from ffmwr.dao.platforms.base.platform import BasePlatform
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file

colorama.init()

logger = get_logger(__name__, propagate=False)

# Suppress ESPN API requests debug logging
logging.getLogger("urllib3.connectionpool").setLevel(level=logging.WARNING)
# Suppress gitpython debug logging
logging.getLogger("git.cmd").setLevel(level=logging.WARNING)
logging.getLogger("git.cmd.cmd.execute").setLevel(level=logging.WARNING)
# Suppress Selenium debug logging
logging.getLogger("selenium.webdriver.common.selenium_manager").setLevel(level=logging.WARNING)
logging.getLogger("selenium.webdriver.common.service").setLevel(level=logging.WARNING)
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(level=logging.WARNING)


# noinspection DuplicatedCode
class ESPNPlatform(BasePlatform):
    def __init__(
        self,
        settings: AppSettings,
        root_dir: Path,
        data_dir: Path,
        league_id: str,
        season: int,
        start_week: int,
        week_for_report: int,
        get_current_nfl_week_function: Callable,
        week_validation_function: Callable,
        save_data: bool = True,
        offline: bool = False,
    ):
        super().__init__(
            settings,
            "ESPN",
            "https://lm-api-reads.fantasy.espn.com",
            root_dir,
            data_dir,
            league_id,
            season,
            start_week,
            week_for_report,
            get_current_nfl_week_function,
            week_validation_function,
            save_data,
            offline,
        )

    def _authenticate(self) -> None:
        time.sleep(0.25)

        # skip credentials check for public ESPN league access when use-default is set to true
        if os.environ.get("USE_DEFAULT"):
            if (
                not self.settings.platform_settings.espn_cookie_swid
                and not self.settings.platform_settings.espn_cookie_espn_s2
            ):
                logger.info(
                    'Use-default is set to "true". Automatically running the report for the selected ESPN league '
                    "without credentials. This will only work for public ESPN leagues."
                )
            return

        if (
            not self.settings.platform_settings.espn_cookie_swid
            or not self.settings.platform_settings.espn_cookie_espn_s2
        ):
            user_input = input(
                f"{Fore.YELLOW}"
                f"Your .env file is missing the required authentication session cookies for ESPN private leagues.\n"
                f'If generating the report for a PUBLIC league then ignore this message and type "y" to CONTINUE\n'
                f"running the app. However, if generating the report for a PRIVATE league then type any other key to\n"
                f"authenticate with your ESPN credentials. -> {Style.RESET_ALL}"
            )

            if user_input.lower() == "y":
                return

            if not self.settings.platform_settings.espn_username:
                self.settings.platform_settings.espn_username = input(
                    f"{Fore.GREEN}What is your ESPN username? -> {Style.RESET_ALL}"
                )
                self.settings.write_settings_to_env_file(self.root_dir / ".env")

            if not self.settings.platform_settings.espn_password:
                self.settings.platform_settings.espn_password = getpass(
                    f"{Fore.GREEN}What is your ESPN password? -> {Style.RESET_ALL}"
                )
                self.settings.write_settings_to_env_file(self.root_dir / ".env")

            if not self.settings.platform_settings.espn_chrome_user_profile_path:
                self.settings.platform_settings.espn_chrome_user_profile_path = input(
                    f'{Fore.GREEN}What is your Chrome user data profile path? (wrap your response in quotes ("") if '
                    f"there are any spaces in it) -> {Style.RESET_ALL}"
                )
                self.settings.write_settings_to_env_file(self.root_dir / ".env")

            logger.info("Retrieving your ESPN session cookies using your configured ESPN credentials...")

            espn_session_cookies = self._retrieve_session_cookies()
            self.settings.platform_settings.espn_cookie_swid = espn_session_cookies["swid"]
            self.settings.platform_settings.espn_cookie_espn_s2 = espn_session_cookies["espn_s2"]
            self.settings.write_settings_to_env_file(self.root_dir / ".env")

            logger.info("...ESPN session cookies retrieved and written to your .env file.")

    @staticmethod
    def _get_espn_session_cookies(web_driver: WebDriver):
        if web_driver.get_cookie("SWID") and web_driver.get_cookie("espn_s2"):
            return {
                "swid": web_driver.get_cookie("SWID")["value"],
                # "swid": web_driver.get_cookie("SWID")["value"].translate({ord(i): None for i in "{}"}),
                "espn_s2": web_driver.get_cookie("espn_s2")["value"],
            }
        else:
            return {}

    def _retrieve_session_cookies(self):
        # set web driver options
        options = ChromeOptions()
        options.add_argument("--headless=new")  # comment out this line if you wish to see live browser navigation
        options.add_argument(f"--user-data-dir={self.settings.platform_settings.espn_chrome_user_data_dir}")
        options.add_argument(f"--profile-directory={self.settings.platform_settings.espn_chrome_user_profile}")
        driver = Chrome(options=options)
        driver.implicitly_wait(0.5)

        driver.get("https://www.espn.com/fantasy/football/")

        actions = ActionChains(driver)

        wait_for_element_timeout = 10
        try:
            # wait for the profile menu to appear
            block = WebDriverWait(driver, wait_for_element_timeout)
            block.until(expected_conditions.visibility_of_element_located((By.ID, "global-user-trigger")))

            profile_menu = driver.find_element(by=By.ID, value="global-user-trigger")

            # hover over profile menu
            actions.move_to_element(profile_menu).perform()

            # select account management menu
            account_management = driver.find_element(by=By.CLASS_NAME, value="account-management")

            for item in account_management.find_elements(by=By.CSS_SELECTOR, value="a"):
                # click login link from account management
                if item.get_attribute("tref") == "/members/v3_1/login":
                    item.click()

            # wait for the modal iframe to appear
            block = WebDriverWait(driver, wait_for_element_timeout)
            block.until(expected_conditions.visibility_of_element_located((By.ID, "oneid-wrapper")))

            # switch driver to modal iframe
            driver.switch_to.frame("oneid-iframe")

            # switch modal form to accept both username and password at once
            username_login = driver.find_element(by=By.ID, value="LaunchLogin")
            for link in username_login.find_elements(by=By.CSS_SELECTOR, value="a"):
                link.click()

            # fill the username and password fields
            driver.find_element(by=By.ID, value="InputLoginValue").send_keys(
                self.settings.platform_settings.espn_username
            )
            driver.find_element(by=By.ID, value="InputPassword").send_keys(
                self.settings.platform_settings.espn_password
            )

            # submit the login form
            driver.find_element(by=By.ID, value="BtnSubmit").click()

            # switch back to the main page
            driver.switch_to.default_content()

        except TimeoutException:
            logger.debug(
                f"Already logged in to browser with user profile "
                f'"{self.settings.platform_settings.espn_chrome_user_profile}".\n'
            )

        # retrieve and display session cookies needed for ESPN FF API authentication and extract their values
        espn_session_cookies = WebDriverWait(driver, timeout=60).until(lambda d: self._get_espn_session_cookies(d))

        driver.quit()

        return espn_session_cookies

    def map_data_to_base(self) -> None:
        logger.debug(f"Retrieving {self.platform_display} league data and mapping it to base objects.")

        # TODO: GET SAVE/LOAD WORKING FOR ALL ESPN DATA!
        espn_league: LeagueWrapper = LeagueWrapper(
            league_id=int(self.league.league_id),
            year=self.league.season,
            espn_s2=self.settings.platform_settings.espn_cookie_espn_s2,
            swid=self.settings.platform_settings.espn_cookie_swid,
        )

        # not currently needed
        # league_standings = espn_league.standings()

        self.league.name = espn_league.settings.name
        self.league.week = int(espn_league.current_week) or self.current_week
        # TODO: figure out how to get league starting week
        self.league.start_week = self.start_week
        self.league.num_teams = int(espn_league.settings.team_count)
        self.league.num_playoff_slots = int(espn_league.settings.playoff_team_count)
        self.league.num_regular_season_weeks = int(espn_league.settings.reg_season_count)

        self.league.divisions = {
            str(division.get("id")): division.get("name")
            for division in espn_league.settings_json.get("scheduleSettings").get("divisions")
        }
        self.league.num_divisions = len(self.league.divisions) if len(self.league.divisions) > 1 else 0
        self.league.has_divisions = self.league.num_divisions > 0

        # TODO: ESPN does not currently offer a built-in median game
        self.league.has_median_matchup = False
        self.league.median_score = 0

        # use hijacked raw json since acquisition settings are not exposed in the API wrapper
        self.league.is_faab = bool(espn_league.settings_json.get("acquisitionSettings").get("isUsingAcquisitionBudget"))
        if self.league.is_faab:
            self.league.faab_budget = int(
                espn_league.settings_json.get("acquisitionSettings").get("acquisitionBudget", 0)
            )

        # league.url = self.league.ENDPOINT
        self.league.url = f"{self.base_url}/football/league?leagueId={self.league.league_id}"

        # TODO: set up with ESPN player endpoint
        # self.league.player_data_by_week_function = self.league.player_map
        # self.league.player_data_by_week_key = "player_points_value"

        # use hijacked raw json since roster settings are not exposed in the API wrapper
        roster_positions = {
            POSITION_MAP[int(pos_id)]: pos_count
            for pos_id, pos_count in espn_league.settings_json.get("rosterSettings").get("lineupSlotCounts").items()
            if pos_count > 0
        }

        for position, count in roster_positions.items():
            pos_attributes = self.position_mapping.get(position)
            pos_name = pos_attributes.get("base")
            pos_count = int(count)

            if pos_attributes.get("is_flex"):
                self.league.__setattr__(
                    pos_attributes.get("league_positions_attribute"), pos_attributes.get("positions")
                )

            self.league.roster_positions.append(pos_name)
            self.league.roster_position_counts[pos_name] = pos_count
            self.league.roster_active_slots.extend(
                [pos_name] * pos_count if pos_name not in self.league.bench_positions else []
            )

        # only ESPN (ouf of supported platforms) offers home field advantage
        home_field_advantage = (
            espn_league.settings_json.get("scoringSettings").get("homeTeamBonus")
            if espn_league.settings_json.get("scoringSettings").get("homeTeamBonus")
            else 0
        )

        logger.debug("Getting ESPN matchups by week data.")
        matchups_by_week = {}
        matchups_json_by_week = {}
        median_score_by_week = {}
        for week_for_matchups in range(self.start_week, int(espn_league.settings.reg_season_count) + 1):
            matchups_by_week[str(week_for_matchups)] = espn_league.box_scores(week_for_matchups)
            matchups_json_by_week[str(week_for_matchups)] = espn_league.box_data_json

            if int(week_for_matchups) <= self.league.week_for_report:
                scores = []
                matchup: BoxScore
                for matchup in matchups_by_week[str(week_for_matchups)]:
                    team: Team
                    for team in [matchup.home_team, matchup.away_team]:
                        team_score = team.scores[week_for_matchups - 1]
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    median_score_by_week[str(week_for_matchups)] = weekly_median
                else:
                    median_score_by_week[str(week_for_matchups)] = 0

        league_median_records_by_team = {}
        for week, matchups in matchups_by_week.items():
            self.league.teams_by_week[str(week)] = {}
            self.league.matchups_by_week[str(week)] = []
            matchup: BoxScore
            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = int(week)
                base_matchup.complete = int(week) < self.league.week
                base_matchup.tied = matchup.home_score == matchup.away_score

                matchup_teams = {"home": matchup.home_team, "away": matchup.away_team}
                for key, matchup_team in matchup_teams.items():
                    team_json = espn_league.teams_json[str(matchup_team.team_id)]
                    base_team = BaseTeam()

                    opposite_key = "away" if key == "home" else "home"
                    team_division = matchup_team.division_id if self.league.num_divisions > 0 else None
                    opponent_division = (
                        matchup_teams[opposite_key].division_id if self.league.num_divisions > 0 else None
                    )
                    if team_division and opponent_division and team_division == opponent_division:
                        base_matchup.division_matchup = True

                    base_team.week = int(week)
                    base_team.name = matchup_team.team_name
                    base_team.num_moves = team_json["transactionCounter"].get("acquisitions", 0)
                    base_team.num_trades = team_json["transactionCounter"].get("trades", 0)

                    primary_manager = espn_league.managers_json.get(team_json["primaryOwner"])
                    team_managers = [primary_manager]
                    for manager_id in team_json["owners"]:
                        if manager_id != primary_manager["id"]:
                            team_managers.append(espn_league.managers_json.get(manager_id))

                    for manager in team_managers:
                        base_manager = BaseManager()

                        base_manager.manager_id = manager["id"]
                        base_manager.email = None
                        manager_first_name = manager.get("firstName", f"Manager {matchup_team.team_id}")
                        manager_last_name = manager.get("lastName", "")
                        base_manager.name = re.sub(r"\W+", " ", f"{manager_first_name} {manager_last_name}").strip()
                        base_manager.nickname = manager.get("displayName", None)

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name_str for manager in base_team.managers])
                    base_team.team_id = str(matchup_team.team_id)

                    team_is_home = False
                    if int(base_team.team_id) == int(matchup.home_team.team_id):
                        team_is_home = True
                        base_team.home_field_advantage_points = home_field_advantage
                        base_team.points = float(matchup.home_score + base_team.home_field_advantage_points)
                    else:
                        base_team.points = float(matchup.away_score)

                    base_team.projected_points = None
                    base_team.waiver_priority = team_json["waiverRank"]
                    self.league.has_waiver_priorities = base_team.waiver_priority > 0
                    if self.league.is_faab:
                        base_team.faab = self.league.faab_budget - int(
                            team_json["transactionCounter"].get("acquisitionBudgetSpent", 0)
                        )
                    base_team.url = (
                        f"https://lm-api-reads.fantasy.espn.com/football/team"
                        f"?leagueId={self.league.league_id}&teamId={base_team.team_id}"
                    )

                    if matchup_team.streak_type == "WIN":
                        streak_type = "W"
                    elif matchup_team.streak_type == "LOSS":
                        streak_type = "L"
                    else:
                        streak_type = "T"

                    if team_json["record"]["division"].get("streakType") == "WIN":
                        division_streak_type = "W"
                    elif team_json["record"]["division"].get("streakType") == "LOSS":
                        division_streak_type = "L"
                    else:
                        division_streak_type = "T"

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(matchup_team.wins),
                        losses=int(matchup_team.losses),
                        ties=int(team_json["record"]["overall"].get("ties", 0)),
                        percentage=round(float(team_json["record"]["overall"].get("percentage", 0)), 3),
                        points_for=float(matchup_team.points_for),
                        points_against=float(matchup_team.points_against),
                        streak_type=streak_type,
                        streak_len=int(matchup_team.streak_length),
                        team_id=matchup_team.team_id,
                        team_name=matchup_team.team_name,
                        rank=int(matchup_team.standing),
                        division=base_team.division,
                        division_wins=int(team_json["record"]["division"].get("wins", 0)),
                        division_losses=int(team_json["record"]["division"].get("losses", 0)),
                        division_ties=int(team_json["record"]["division"].get("ties", 0)),
                        division_percentage=round(float(team_json["record"]["division"].get("percentage", 0)), 3),
                        division_streak_type=division_streak_type,
                        division_streak_len=int(team_json["record"]["division"].get("streakLength", 0)),
                    )
                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if base_matchup.division_matchup:
                        base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = median_score_by_week.get(str(week))

                    median_record: BaseRecord = league_median_records_by_team.get(str(base_team.team_id))
                    if not median_record:
                        median_record = BaseRecord(team_id=base_team.team_id, team_name=base_team.name)
                        league_median_records_by_team[str(base_team.team_id)] = median_record

                    if week_median:
                        # use this if you want the tie-break to be season total points over/under median score
                        median_record.add_points_for(base_team.points - week_median)
                        # use this if you want the tie-break to be current week points over/under median score
                        # median_record.add_points_for(
                        #     (median_record.get_points_for() * -1) + (base_team.points - week_median))
                        median_record.add_points_against((median_record.get_points_against() * -1) + week_median)
                        if base_team.points > week_median:
                            median_record.add_win()
                        elif base_team.points < week_median:
                            median_record.add_loss()
                        else:
                            median_record.add_tie()

                        base_team.current_median_record = median_record

                    # add team to matchup teams
                    base_matchup.teams.append(base_team)

                    # add team to league teams by week
                    self.league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # no winner/loser if matchup is tied
                    if team_is_home:
                        if (matchup.home_score + home_field_advantage) > matchup.away_score:
                            base_matchup.winner = base_team
                        elif (matchup.home_score + home_field_advantage) < matchup.away_score:
                            base_matchup.loser = base_team
                    else:
                        if (matchup.home_score + home_field_advantage) > matchup.away_score:
                            base_matchup.loser = base_team
                        elif (matchup.home_score + home_field_advantage) < matchup.away_score:
                            base_matchup.winner = base_team

                # add matchup to league matchups by week
                self.league.matchups_by_week[str(week)].append(base_matchup)

        logger.debug("Getting ESPN rosters by week data.")
        rosters_by_week = {}
        rosters_json_by_week = {}
        for week_for_rosters in range(self.start_week, self.league.week_for_report + 1):
            team_rosters = {}
            for matchup in matchups_by_week[str(week_for_rosters)]:
                team_rosters[matchup.home_team.team_id] = matchup.home_lineup
                team_rosters[matchup.away_team.team_id] = matchup.away_lineup
            rosters_by_week[str(week_for_rosters)] = team_rosters

            team_rosters_json = {}
            for matchup_json in matchups_json_by_week[str(week_for_rosters)]:
                team_rosters_json[matchup_json["home"]["teamId"]] = matchup_json["home"][
                    "rosterForCurrentScoringPeriod"
                ]["entries"]
                team_rosters_json[matchup_json["away"]["teamId"]] = matchup_json["away"][
                    "rosterForCurrentScoringPeriod"
                ]["entries"]
            rosters_json_by_week[str(week_for_rosters)] = team_rosters_json

        for week, rosters in rosters_by_week.items():
            self.league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                team_json = rosters_json_by_week[str(week)][int(team_id)]
                league_team: BaseTeam = self.league.teams_by_week.get(str(week)).get(str(team_id))

                player: BoxPlayer
                for player in roster:
                    player_json = {}
                    for league_player_json in team_json:
                        if player.playerId == league_player_json["playerId"]:
                            player_json = league_player_json["playerPoolEntry"]["player"]

                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = str(player.playerId)
                    # TODO: missing bye
                    base_player.bye_week = None
                    base_player.jersey_number = int(player_json.get("jersey")) if player_json.get("jersey") else None
                    base_player.display_position = self.get_mapped_position(player.position)
                    base_player.nfl_team_id = player_json["proTeamId"]
                    base_player.nfl_team_abbr = player.proTeam
                    base_player.nfl_team_name = player.proTeam

                    if base_player.display_position == "D/ST":
                        base_player.first_name = player_json["firstName"]
                        base_player.full_name = base_player.first_name
                        base_player.nfl_team_name = base_player.first_name
                        base_player.headshot_url = (
                            f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{base_player.nfl_team_abbr}.png"
                        )
                    else:
                        base_player.first_name = player_json["firstName"]
                        base_player.last_name = player_json["lastName"]
                        base_player.full_name = player.name
                        base_player.headshot_url = (
                            f"https://a.espncdn.com/i/headshots/nfl/players/full/{player.playerId}.png"
                        )
                    base_player.owner_team_id = None
                    base_player.owner_team_name = league_team.manager_str
                    # TODO: missing percent owned
                    base_player.percent_owned = None
                    base_player.points = float(player.points)
                    base_player.projected_points = float(player.projected_points)

                    for position in player.eligibleSlots:
                        base_player.eligible_positions.add(self.get_mapped_position(position))

                    base_player.primary_position = self.get_mapped_position(player.position)
                    base_player.position_type = (
                        "O" if base_player.display_position in self.league.offensive_positions else "D"
                    )

                    base_player.selected_position = self.get_mapped_position(player.slot_position)
                    base_player.selected_position_is_flex = self.position_mapping.get(player.slot_position).get(
                        "is_flex"
                    )

                    base_player.status = player_json.get("injuryStatus")

                    if player_json["stats"]:
                        for stat_id, stat_value in player_json["stats"][0]["stats"].items():
                            base_stat = BaseStat()

                            base_stat.stat_id = stat_id
                            base_stat.name = None
                            base_stat.value = stat_value

                            base_player.stats.append(base_stat)

                    # add player to team roster
                    league_team.roster.append(base_player)

                    # add player to league players by week
                    self.league.players_by_week[str(week)][base_player.player_id] = base_player

        self.league.current_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: x.current_record.rank,
        )

        self.league.current_median_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: (
                x.current_median_record.get_wins(),
                -x.current_median_record.get_losses(),
                x.current_median_record.get_ties(),
                x.current_median_record.get_points_for(),
            ),
            reverse=True,
        )


# noinspection DuplicatedCode
class LeagueWrapper(League):
    def __init__(self, league_id: int, year: int, espn_s2=None, swid=None):
        super().__init__(league_id, year, espn_s2, swid)
        self.box_data_json = None

    def _fetch_league(self):
        data = super(League, self)._fetch_league(SettingsClass=Settings)
        import json

        json.dumps(data, indent=2)

        self.nfl_week = data["status"]["latestScoringPeriod"]
        self._fetch_players()
        self._fetch_teams(data)
        self._fetch_draft()

        # # # # # # # # # # # # # # # # # # #
        # # # # # # RAW JSON ACCESS # # # # #
        # # # # # # # # # # # # # # # # # # #
        self.league_json = data
        self.settings_json = data["settings"]
        self.managers_json = {}
        for manager in data["members"]:
            self.managers_json[manager["id"]] = manager
        self.teams_json = {}
        for team in data["teams"]:
            self.teams_json[str(team["id"])] = team
        # # # # # # # # # # # # # # # # # # #
        # # # # # # # # # # # # # # # # # # #
        # # # # # # # # # # # # # # # # # # #

    def box_scores(self, week: int = None) -> List[BoxScore]:
        """Returns list of box score for a given week\n
        Should only be used with most recent season"""
        if self.year < 2019:
            raise Exception("Cant use box score before 2019")
        matchup_period = self.currentMatchupPeriod
        scoring_period = self.current_week
        if week and week <= self.current_week:
            scoring_period = week
            for matchup_id in self.settings.matchup_periods:
                if week in self.settings.matchup_periods[matchup_id]:
                    matchup_period = matchup_id
                    break

        params = {
            "view": ["mMatchupScore", "mScoreboard"],
            "scoringPeriodId": scoring_period,
        }

        filters = {"schedule": {"filterMatchupPeriodIds": {"value": [matchup_period]}}}
        headers = {"x-fantasy-filter": json.dumps(filters)}
        data = self.espn_request.league_get(params=params, headers=headers)

        schedule = data["schedule"]
        pro_schedule = self._get_pro_schedule(scoring_period)
        positional_rankings = self._get_positional_ratings(scoring_period)

        # # # # # # # # # # # # # # # # # # #
        # # # # # # RAW JSON ACCESS # # # # #
        # # # # # # # # # # # # # # # # # # #
        self.box_data_json = [matchup for matchup in schedule]
        # # # # # # # # # # # # # # # # # # #
        # # # # # # # # # # # # # # # # # # #
        # # # # # # # # # # # # # # # # # # #

        box_data = [
            BoxScore(matchup, pro_schedule, positional_rankings, scoring_period, self.year) for matchup in schedule
        ]

        for team in self.teams:
            for matchup in box_data:
                if matchup.home_team == team.team_id:
                    matchup.home_team = team
                elif matchup.away_team == team.team_id:
                    matchup.away_team = team
        return box_data


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    espn_platform = ESPNPlatform(
        local_settings,
        local_root_directory,
        local_root_directory / "output" / "data",
        local_settings.league_id,
        local_settings.season,
        1,
        local_settings.week_for_report,
        lambda *args: None,
        lambda *args: None,
    )
    # noinspection PyProtectedMember
    logger.info(espn_platform._authenticate())
