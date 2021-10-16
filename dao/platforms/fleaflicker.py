__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import datetime
import json
import logging
import os
import re
import sys
from collections import defaultdict
from copy import deepcopy
from statistics import median

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from report.logger import get_logger

logger = get_logger(__name__)

# Suppress Fleaflicker API debug logging
logger.setLevel(level=logging.INFO)


class LeagueData(object):

    def __init__(self,
                 week_for_report,
                 league_id,
                 season,
                 config,
                 data_dir,
                 week_validation_function,
                 get_current_nfl_week_function,
                 save_data=True,
                 dev_offline=False):

        logger.debug("Initializing Fleaflicker league.")

        self.league_id = league_id
        self.season = season
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        self.offensive_positions = ["QB", "RB", "WR", "TE", "K", "RB/WR", "WR/TE", "RB/WR/TE", "RB/WR/TE/QB"]
        self.defensive_positions = ["D/ST"]

        # create full directory path if any directories in it do not already exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        logger.debug("Getting Fleaflicker league data.")

        self.league_url = "https://www.fleaflicker.com/nfl/leagues/" + str(self.league_id)
        scraped_league_info = self.scrape(self.league_url, os.path.join(
            self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-info.html")

        # TODO: do NOT need current season here
        # try:
        #     self.current_season = scraped_league_info.find(
        #         "ul", attrs={"class": "dropdown-menu pull-right"}).find("li", attrs={"class": "active"}).text.strip()
        # except AttributeError:
        #     scraped_league_playoffs = self.scrape(self.league_url + "/playoffs", os.path.join(
        #         self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-playoffs.html")
        #     self.current_season = scraped_league_playoffs.find(
        #         "small", attrs={"class": "btn btn-primary disabled"}).text.strip()

        scraped_league_scores = self.scrape(self.league_url + "/scores", os.path.join(
            self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-scores.html")

        try:
            self.current_week = int(scraped_league_scores.findAll(
                text=re.compile(".*This Week.*"))[-1].parent.findNext("li").text.strip().split(" ")[-1]) - 1
        except (IndexError, AttributeError) as e:
            self.current_week = get_current_nfl_week_function(self.config, self.dev_offline)

        scraped_league_rules = self.scrape(self.league_url + "/rules", os.path.join(
            self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-rules.html")

        elements = scraped_league_rules.findAll(["dt", "dd"])
        for elem in elements:
            if elem.text.strip() == "Playoffs":
                self.num_playoff_slots = int(elements[elements.index(elem) + 1].span.text.strip())

                playoff_weeks_elements = elements[elements.index(elem) + 1].findAll(text=True, recursive=False)
                if any((text.strip() and "Weeks" in text) for text in playoff_weeks_elements):
                    for text in playoff_weeks_elements:
                        if text.strip() and "Weeks" in text:
                            for txt in text.split():
                                if "-" in txt:
                                    self.num_regular_season_weeks = int(txt.split("-")[0]) - 1
                else:
                    self.num_regular_season_weeks = config.getint(
                        "Settings", "num_regular_season_weeks", fallback=14)
                break
            else:
                self.num_playoff_slots = config.getint("Settings", "num_playoff_slots", fallback=6)
                self.num_regular_season_weeks = config.getint("Settings", "num_regular_season_weeks", fallback=14)

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week, self.season)

        # TODO: how to get league rules for LAST YEAR from Fleaflicker API
        self.league_rules = self.query(
            "https://www.fleaflicker.com/api/FetchLeagueRules?leagueId=" + str(self.league_id),
            os.path.join(self.data_dir, str(self.season), str(self.league_id)),
            str(self.league_id) + "-league-rules.json"
        )

        self.league_standings = self.query(
            "https://www.fleaflicker.com/api/FetchLeagueStandings?leagueId=" + str(self.league_id) +
            ("&season=" + self.season) if self.season else "",
            os.path.join(self.data_dir, str(self.season), str(self.league_id)),
            str(self.league_id) + "-league-standings.json"
        )

        self.league_info = self.league_standings.get("league")

        self.league_teams = {}
        self.ranked_league_teams = []
        self.num_divisions = 0
        self.divisions = {}
        for division in self.league_standings.get("divisions"):
            self.divisions[str(division.get("id"))] = division.get("name")
            self.num_divisions += 1
            for team in division.get("teams"):
                team["division_id"] = division.get("id")
                team["division_name"] = division.get("name")
                self.league_teams[team.get("id")] = team
                self.ranked_league_teams.append(team)

        self.ranked_league_teams = sorted(
            self.ranked_league_teams,
            key=lambda x: x.get("recordOverall").get("rank") if x.get("recordOverall").get("rank") else 0
        )

        # TODO: FIGURE OUT WHERE FLEAFLICKER EXPOSES THIS! Fleaflicker supports both MEDIAN and MEAN games
        self.has_median_matchup = False
        self.median_score_by_week = {}

        self.matchups_by_week = {}
        for wk in range(1, int(self.num_regular_season_weeks) + 1):
            self.matchups_by_week[str(wk)] = self.query(
                "https://www.fleaflicker.com/api/FetchLeagueScoreboard?leagueId=" + str(self.league_id) +
                "&scoringPeriod=" + str(wk) +
                ("&season=" + str(self.season) if self.season else ""),
                os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk)),
                "week_" + str(wk) + "-scoreboard.json"
            )

            if int(wk) <= int(self.week_for_report):
                scores = []
                for matchup in self.matchups_by_week[str(wk)].get("games"):
                    for key in ["home", "away"]:
                        team_score = matchup.get(key + "Score").get("score").get("value")
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    self.median_score_by_week[str(wk)] = weekly_median
                else:
                    self.median_score_by_week[str(wk)] = 0

        # self.matchups_by_week = {}
        # for wk in range(1, int(self.week_for_report) + 1):
        #     self.matchups_by_week[str(wk)] = [
        #         self.query(
        #             "https://www.fleaflicker.com/api/FetchLeagueBoxscore?leagueId=" + str(self.league_id) +
        #             "&fantasyGameId=" + str(game.get("id")),
        #             os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk), "matchups"),
        #             str(game.get("id")) + "-matchup.json"
        #         ) for game in self.scoreboard_by_week[str(wk)].get("games")
        #     ]

        self.rosters_by_week = {}
        for wk in range(1, int(self.week_for_report) + 1):
            self.rosters_by_week[str(wk)] = {
                str(team.get("id")): self.query(
                    "https://www.fleaflicker.com/api/FetchRoster?leagueId=" + str(self.league_id) +
                    "&teamId=" + str(team.get("id")) +
                    ("&season=" + str(self.season) if self.season else "") +
                    ("&scoringPeriod=" + str(wk)),
                    os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk), "rosters"),
                    str(team.get("id")) + "-" + str(team.get("name")).replace(" ", "_") + "-roster.json"
                ) for team in self.ranked_league_teams
            }

        self.roster_positions = self.league_rules.get("rosterPositions")

        # TODO: how to get transactions for LAST YEAR from Fleaflicker API...?
        self.league_activity = self.query(
            "https://www.fleaflicker.com/api/FetchLeagueActivity?leagueId=" + str(self.league_id),
            os.path.join(self.data_dir, str(self.season), str(self.league_id)),
            str(self.league_id) + "-league-transactions.json"
        )

        self.league_transactions_by_team = defaultdict(dict)
        for activity in self.league_activity.get("items"):

            epoch_milli = float(activity.get("timeEpochMilli"))
            timestamp = datetime.datetime.fromtimestamp(epoch_milli / 1000)

            season_start = datetime.datetime(int(self.season), 9, 1)
            season_end = datetime.datetime(int(self.season) + 1, 3, 1)

            if season_start < timestamp < season_end:
                if activity.get("transaction"):
                    if activity.get("transaction").get("type"):
                        transaction_type = activity.get("transaction").get("type")
                    else:
                        transaction_type = "TRANSACTION_ADD"

                    is_move = False
                    is_trade = False
                    if "TRADE" in transaction_type:
                        is_trade = True
                    elif any(transaction_str in transaction_type for transaction_str in ["CLAIM", "ADD", "DROP"]):
                        is_move = True

                    if not self.league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))]:
                        self.league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))] = {
                            "transactions": [transaction_type],
                            "moves": 1 if is_move else 0,
                            "trades": 1 if is_trade else 0
                        }
                    else:
                        self.league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))][
                            "transactions"].append(transaction_type)
                        self.league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))][
                            "moves"] += 1 if is_move else 0
                        self.league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))][
                            "trades"] += 1 if is_trade else 0

    def query(self, url, file_dir, filename):

        file_path = os.path.join(file_dir, filename)

        if not self.dev_offline:
            logger.debug("Retrieving Fleaflicker data from endpoint: {0}".format(url))
            response = requests.get(url)

            try:
                response.raise_for_status()
            except HTTPError as e:
                # log error and terminate query if status code is not 200
                logger.error("REQUEST FAILED WITH STATUS CODE: {0} - {1}".format(response.status_code, e))
                sys.exit("...run aborted.")

            response_json = response.json()
            logger.debug("Response (JSON): {0}".format(response_json))
        else:
            try:
                logger.debug("Loading saved Fleaflicker data for endpoint: {0}".format(url))
                with open(file_path, "r", encoding="utf-8") as data_in:
                    response_json = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    "FILE {0} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit("...run aborted.")

        if self.save_data:
            logger.debug("Saving Fleaflicker data retrieved from endpoint: {0}".format(url))
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                json.dump(response_json, data_out, ensure_ascii=False, indent=2)

        return response_json

    def scrape(self, url, file_dir, filename):

        file_path = os.path.join(file_dir, filename)

        if not self.dev_offline:
            logger.debug("Scraping Fleaflicker data from endpoint: {0}".format(url))

            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 " \
                         "(KHTML, like Gecko) Version/13.0 Safari/605.1.15"
            headers = {"user-agent": user_agent}
            response = requests.get(url, headers)

            html_soup = BeautifulSoup(response.text, "html.parser")
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

        if self.save_data:
            logger.debug("Saving Fleaflicker data scraped from endpoint: {0}".format(url))
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                data_out.write(html_soup.prettify())

        return html_soup

    def map_data_to_base(self, base_league_class):
        logger.debug("Mapping Fleaflicker data to base objects.")

        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague

        league.name = self.league_info.get("name")
        league.week = int(self.current_week)
        league.season = self.season
        league.num_teams = int(self.league_info.get("size"))
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.num_divisions = self.num_divisions
        league.divisions = self.divisions
        if league.num_divisions > 0:
            league.has_divisions = True
        league.has_median_matchup = self.has_median_matchup
        league.median_score = 0
        league.faab_budget = int(self.league_info.get("defaultWaiverBudget", 0))
        if league.faab_budget > 0:
            league.is_faab = True
        league.url = self.league_url

        # league.player_data_by_week_function = None
        # league.player_data_by_week_key = None

        league.bench_positions = ["BN", "IR"]

        for position in self.roster_positions:
            pos_name = position.get("label")
            if position.get("start"):
                pos_count = int(position.get("start"))
            elif position.get("label") == "BN":
                pos_count = int(position.get("max")) if position.get("max") else 0
            else:
                pos_count = 0

            if pos_name == "RB/WR":
                league.flex_positions_rb_wr = ["RB", "WR"]
                pos_name = "FLEX_RB_WR"
            if pos_name == "WR/TE":
                league.flex_positions_te_wr = ["TE", "WR"]
                pos_name = "FLEX_TE_WR"
            if pos_name == "RB/WR/TE":
                league.flex_positions_rb_te_wr = ["RB", "TE", "WR"]
                pos_name = "FLEX_RB_TE_WR"
            if pos_name == "RB/WR/TE/QB":
                league.flex_positions_qb_rb_te_wr = ["QB", "RB", "TE", "WR"]
                pos_name = "FLEX_QB_RB_TE_WR"

            pos_counter = deepcopy(pos_count)
            while pos_counter > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_counter -= 1

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = pos_count

        league_median_records_by_team = {}
        for week, matchups in self.matchups_by_week.items():
            matchups_week = matchups.get("schedulePeriod").get("value")
            matchups = matchups.get("games")

            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []

            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = int(matchups_week)
                base_matchup.complete = True if bool(matchup.get("isFinalScore")) else False
                base_matchup.tied = True if matchup.get("homeResult") == "TIE" else False

                for key in ["home", "away"]:
                    team_data = matchup.get(key)  # type: dict
                    base_team = BaseTeam()

                    opposite_key = "away" if key == "home" else "home"
                    team_division = self.league_teams[team_data.get("id")].get("division_id")
                    opponent_division = self.league_teams[matchup.get(opposite_key).get("id")].get("division_id")
                    if team_division and opponent_division and team_division == opponent_division:
                        base_matchup.division_matchup = True

                    base_team.week = int(matchups_week)
                    base_team.name = team_data.get("name")

                    managers = self.league_teams[team_data.get("id")].get("owners")
                    if managers:
                        for manager in managers:
                            base_manager = BaseManager()

                            base_manager.manager_id = str(manager.get("id"))
                            base_manager.email = None
                            base_manager.name = manager.get("displayName")

                            base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name_str for manager in base_team.managers])

                    base_team.team_id = str(team_data.get("id"))
                    base_team.points = float(matchup.get(key + "Score", {}).get("score", {}).get("value", 0))
                    base_team.projected_points = None

                    # TODO: currently the fleaflicker API call only returns 1st PAGE of transactions... figure this out!
                    base_team.num_moves = str(
                        self.league_transactions_by_team[str(base_team.team_id)].get("moves", 0)) + "*"
                    base_team.num_trades = str(
                        self.league_transactions_by_team[str(base_team.team_id)].get("trades", 0)) + "*"

                    base_team.waiver_priority = team_data.get("waiverPosition", 0)
                    league.has_waiver_priorities = base_team.waiver_priority > 0
                    base_team.faab = team_data.get("waiverAcquisitionBudget", {}).get("value", 0)
                    base_team.url = "https://www.fleaflicker.com/nfl/leagues/" + self.league_id + "/teams/" + \
                                    str(team_data.get("id"))

                    if team_data.get("streak").get("value"):
                        if team_data.get("streak").get("value") > 0:
                            streak_type = "W"
                        elif team_data.get("streak").get("value") < 0:
                            streak_type = "L"
                        else:
                            streak_type = "T"
                    else:
                        streak_type = "T"

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(team_data.get("recordOverall", {}).get("wins", 0)),
                        losses=int(team_data.get("recordOverall", {}).get("losses", 0)),
                        ties=int(team_data.get("recordOverall", {}).get("ties", 0)),
                        percentage=round(float(team_data.get("recordOverall", {}).get("winPercentage", {}).get(
                            "value", 0)), 3),
                        points_for=float(team_data.get("pointsFor", {}).get("value", 0)),
                        points_against=float(team_data.get("pointsAgainst", {}).get("value", 0)),
                        streak_type=streak_type,
                        streak_len=int(abs(team_data.get("streak", {}).get("value", 0))),
                        team_id=base_team.team_id,
                        team_name=base_team.name,
                        rank=int(team_data.get("recordOverall", {}).get("rank", 0)),
                        division=base_team.division,
                        division_wins=int(team_data.get("recordDivision", {}).get("wins", 0)),
                        division_losses=int(team_data.get("recordDivision", {}).get("losses", 0)),
                        division_ties=int(team_data.get("recordDivision", {}).get("ties", 0)),
                        division_percentage=round(float(team_data.get("recordDivision", {}).get(
                            "winPercentage", {}).get("value", 0)), 3),
                        division_rank=int(team_data.get("recordDivision", {}).get("rank", 0))
                    )
                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if base_matchup.division_matchup:
                        base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = self.median_score_by_week.get(str(week))

                    median_record = league_median_records_by_team.get(str(base_team.team_id))  # type: BaseRecord
                    if not median_record:
                        median_record = BaseRecord(
                            team_id=base_team.team_id,
                            team_name=base_team.name,
                            points_for=(base_team.points - week_median),
                            points_against=week_median
                        )
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
                    league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # no winner/loser if matchup is tied
                    if matchup.get(key + "Result") == "WIN":
                        base_matchup.winner = base_team
                    elif matchup.get(key + "Result") == "LOSE":
                        base_matchup.loser = base_team

                # add matchup to league matchups by week
                league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                league_team = league.teams_by_week.get(str(week)).get(str(team_id))  # type: BaseTeam

                for player in [slot for group in roster.get("groups") for slot in group.get("slots")]:
                    flea_player_position = player.get("position")
                    flea_league_player = player.get("leaguePlayer")

                    if flea_league_player:
                        flea_pro_player = flea_league_player.get("proPlayer")

                        base_player = BasePlayer()

                        base_player.week_for_report = int(week)
                        base_player.player_id = flea_pro_player.get("id")
                        base_player.bye_week = int(flea_pro_player.get("nflByeWeek", 0))
                        base_player.display_position = flea_pro_player.get("position")
                        base_player.nfl_team_id = None
                        base_player.nfl_team_abbr = flea_pro_player.get("proTeam", {}).get("abbreviation").upper()
                        base_player.nfl_team_name = flea_pro_player.get("proTeam", {}).get("location") + " " + \
                            flea_pro_player.get("proTeam", {}).get("name")
                        if flea_player_position.get("label") == "D/ST":
                            base_player.first_name = flea_pro_player.get("nameFull")
                        else:
                            base_player.first_name = flea_pro_player.get("nameFirst")
                            base_player.last_name = flea_pro_player.get("nameLast")
                        base_player.full_name = flea_pro_player.get("nameFull")
                        if flea_player_position.get("label") == "D/ST":
                            # use ESPN D/ST team logo (higher resolution) because Fleaflicker does not provide them
                            base_player.headshot_url = \
                                "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{0}.png".format(
                                    base_player.nfl_team_abbr)
                        else:
                            base_player.headshot_url = flea_pro_player.get("headshotUrl")
                        base_player.owner_team_id = flea_league_player.get("owner", {}).get("id")
                        base_player.owner_team_name = flea_league_player.get("owner", {}).get("name")
                        base_player.percent_owned = 0
                        base_player.points = float(flea_league_player.get("viewingActualPoints", {}).get("value", 0))
                        # TODO: get season total points via summation, since this gives the end of season total, not
                        #  the total as of the selected week
                        # base_player.season_points = float(flea_league_player.get("seasonTotal", {}).get("value", 0))
                        # base_player.season_average_points = round(float(
                        #     flea_league_player.get("seasonAverage", {}).get("value", 0)), 2)
                        base_player.projected_points = None

                        base_player.position_type = "O" if flea_pro_player.get(
                            "position") in self.offensive_positions else "D"
                        base_player.primary_position = flea_pro_player.get("position")

                        eligible_positions = [pos for positions in flea_league_player.get(
                            "rankFantasy", {}).get("positions", {}) for pos in positions.get("position", {}).get(
                            "eligibility")]
                        for position in eligible_positions:
                            base_player.eligible_positions.append(position)
                            if position in league.flex_positions_rb_wr:
                                base_player.eligible_positions.append("FLEX_RB_WR")
                            if position in league.flex_positions_te_wr:
                                base_player.eligible_positions.append("FLEX_TE_WR")
                            if position in league.flex_positions_rb_te_wr:
                                base_player.eligible_positions.append("FLEX_RB_TE_WR")
                            if position in league.flex_positions_qb_rb_te_wr:
                                base_player.eligible_positions.append("FLEX_QB_RB_TE_WR")
                        base_player.eligible_positions = list(set(base_player.eligible_positions))

                        selected_position = flea_player_position.get("label")
                        if selected_position == "RB/WR":
                            base_player.selected_position = "FLEX_RB_WR"
                        elif selected_position == "WR/TE":
                            base_player.selected_position = "FLEX_TE_WR"
                        elif selected_position == "RB/WR/TE":
                            base_player.selected_position = "FLEX_RB_TE_WR"
                        elif selected_position == "RB/WR/TE/QB":
                            base_player.selected_position = "FLEX_QB_RB_TE_WR"
                        else:
                            base_player.selected_position = selected_position
                        base_player.selected_position_is_flex = True if "/" in flea_pro_player.get(
                            "position") else False

                        base_player.status = flea_pro_player.get("injury", {}).get("typeAbbreviaition")

                        for stat in flea_league_player.get("viewingActualStats"):
                            base_stat = BaseStat()

                            base_stat.stat_id = stat.get("category", {}).get("id")
                            base_stat.name = stat.get("category", {}).get("abbreviation")
                            base_stat.value = stat.get("value", {}).get("value", 0)

                            base_player.stats.append(base_stat)

                        # add player to team roster
                        league_team.roster.append(base_player)

                        # add player to league players by week
                        league.players_by_week[str(week)][base_player.player_id] = base_player

        league.current_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.current_record.rank)

        league.current_median_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(),
            key=lambda x: (
                x.current_median_record.get_wins(),
                -x.current_median_record.get_losses(),
                x.current_median_record.get_ties(),
                x.current_median_record.get_points_for()
            ),
            reverse=True
        )

        return league
