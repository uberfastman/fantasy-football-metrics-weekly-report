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

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseManager, BasePlayer, BaseStat

logger = logging.getLogger(__name__)

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
                 save_data=True,
                 dev_offline=False):

        self.league_id = league_id
        self.season = season
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        self.offensive_positions = ["QB", "RB", "WR", "TE", "K", "RB/WR/TE"]
        self.defensive_positions = ["D/ST"]

        # create full directory path if any directories in it do not already exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.league_url = "https://www.fleaflicker.com/nfl/leagues/" + str(self.league_id)
        scraped_league_info = self.scrape(self.league_url, os.path.join(
            self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-info.html")

        self.current_season = scraped_league_info.find(
            "ul", attrs={"class": "dropdown-menu pull-right"}).find("li", attrs={"class": "active"}).text.strip()

        scraped_league_scores = self.scrape(self.league_url + "/scores", os.path.join(
            self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-scores.html")

        self.current_week = int(scraped_league_scores.findAll(
            text=re.compile(".*This Week.*"))[-1].parent.findNext("li").text.strip().split(" ")[-1]) - 1

        scraped_league_rules = self.scrape(self.league_url + "/rules", os.path.join(
            self.data_dir, str(self.season), str(self.league_id)), str(self.league_id) + "-league-rules.html")

        elements = scraped_league_rules.findAll(["dt", "dd"])
        for elem in elements:
            if elem.string == "Playoffs":
                self.num_playoff_slots = elements[elements.index(elem) + 1].span.string
                self.num_regular_season_weeks = int(
                    elements[elements.index(elem) + 1].contents[1].split()[-1].split("-")[0]) - 1

            else:
                self.num_playoff_slots = config.get("Configuration", "num_playoff_slots")
                self.num_regular_season_weeks = config.get("Configuration", "num_regular_season_weeks")

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week)

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
        for division in self.league_standings.get("divisions"):
            for team in division.get("teams"):
                self.league_teams[team.get("id")] = team
                self.ranked_league_teams.append(team)

        self.ranked_league_teams = sorted(self.ranked_league_teams, key=lambda x: x.get("recordOverall").get("rank"))

        self.matchups_by_week = {}
        for wk in range(1, int(self.num_regular_season_weeks) + 1):
            self.matchups_by_week[str(wk)] = self.query(
                "https://www.fleaflicker.com/api/FetchLeagueScoreboard?leagueId=" + str(self.league_id) +
                "&scoringPeriod=" + str(wk) +
                ("&season=" + str(self.season) if self.season else ""),
                os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk)),
                "week_" + str(wk) + "-scoreboard.json"
            )

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
                    ("&scoringPeriod=" + str(wk)),
                    os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk), "rosters"),
                    str(team.get("id")) + "-" + str(team.get("name")).replace(" ", "_") + "-roster.json"
                ) for team in self.ranked_league_teams
            }

        self.roster_positions = self.league_rules.get("rosterPositions")

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
            response = requests.get(url)

            try:
                response.raise_for_status()
            except HTTPError as e:
                # log error and terminate query if status code is not 200
                logger.error("REQUEST FAILED WITH STATUS CODE: {} - {}".format(response.status_code, e))
                sys.exit()

            response_json = response.json()
            logger.debug("Response (JSON): {}".format(response_json))
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    response_json = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    "FILE {} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit()

        if self.save_data:
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                json.dump(response_json, data_out, ensure_ascii=False, indent=2)

        return response_json

    def scrape(self, url, file_dir, filename):

        file_path = os.path.join(file_dir, filename)

        if not self.dev_offline:
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 " \
                         "(KHTML, like Gecko) Version/13.0 Safari/605.1.15"
            headers = {"user-agent": user_agent}
            response = requests.get(url, headers)

            html_soup = BeautifulSoup(response.text, "html.parser")
            logger.debug("Response (HTML): {}".format(html_soup))
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    html_soup = BeautifulSoup(data_in.read(), "html.parser")
            except FileNotFoundError:
                logger.error(
                    "FILE {} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit()

        if self.save_data:
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                data_out.write(html_soup.prettify())

        return html_soup

    def map_data_to_base(self, base_league_class):
        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague

        league.name = self.league_info.get("name")
        league.week = int(self.current_week)
        league.season = self.season
        league.num_teams = int(self.league_info.get("size"))
        league.num_playoff_slots = int(self.num_playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.faab_budget = int(self.league_info.get("defaultWaiverBudget", 0))
        if league.faab_budget > 0:
            league.is_faab = True
        league.url = self.league_url

        # league.player_data_by_week_function = None
        # league.player_data_by_week_key = None

        league.bench_positions = [
            str(bench_position) for bench_position in self.config.get("Configuration", "bench_positions").split(",")]

        for position in self.roster_positions:
            pos_name = position.get("label")
            if position.get("start"):
                pos_count = int(position.get("start"))
            else:
                pos_count = int(position.get("max"))

            pos_counter = deepcopy(pos_count)
            while pos_counter > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_counter -= 1

            if pos_name == "RB/WR":
                league.flex_positions = ["WR", "RB"]
            if pos_name == "RB/WR/TE":
                league.flex_positions = ["WR", "RB", "TE"]
            if pos_name == "RB/WR/TE/QB":
                league.flex_positions = ["QB", "WR", "RB", "TE"]

            if pos_name != "D/ST" and "/" in pos_name :
                pos_name = "FLEX"

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = pos_count

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
                    team = matchup.get(key)  # type: dict
                    base_team = BaseTeam()

                    base_team.week = int(matchups_week)
                    base_team.name = team.get("name")

                    for manager in self.league_teams[team.get("id")].get("owners"):
                        base_manager = BaseManager()

                        base_manager.manager_id = str(manager.get("id"))
                        base_manager.email = None
                        base_manager.name = manager.get("displayName")

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name for manager in base_team.managers])

                    base_team.team_id = str(team.get("id"))
                    base_team.points = float(matchup.get(key + "Score", {}).get("score", {}).get("value", 0))
                    base_team.projected_points = None

                    # TODO: currently the fleaflicker API call only returns 1st PAGE of transactions... figure this out!
                    base_team.num_moves = str(
                        self.league_transactions_by_team[str(base_team.team_id)].get("moves", 0)) + "*"
                    base_team.num_trades = str(
                        self.league_transactions_by_team[str(base_team.team_id)].get("trades", 0)) + "*"

                    base_team.waiver_priority = team.get("waiverAcquisitionBudget", {}).get("value")
                    base_team.faab = team.get("waiverAcquisitionBudget", {}).get("value")
                    base_team.url = "https://www.fleaflicker.com/nfl/leagues/" + self.league_id + "/teams/" + \
                                    str(team.get("id"))

                    base_team.wins = int(team.get("recordOverall", {}).get("wins", 0))
                    base_team.losses = int(team.get("recordOverall", {}).get("losses", 0))
                    base_team.ties = int(team.get("recordOverall", {}).get("ties", 0))
                    base_team.percentage = round(float(team.get("recordOverall", {}).get("winPercentage", {}).get(
                        "value", 0)), 3)
                    if team.get("streak").get("value") > 0:
                        base_team.streak_type = "W"
                    elif team.get("streak").get("value") < 0:
                        base_team.streak_type = "L"
                    else:
                        base_team.streak_type = "T"
                    base_team.streak_len = int(abs(team.get("streak", {}).get("value", 0)))
                    base_team.streak_str = str(base_team.streak_type) + "-" + str(base_team.streak_len)
                    base_team.points_against = float(team.get("pointsAgainst", {}).get("value", 0))
                    base_team.points_for = float(team.get("pointsFor", {}).get("value", 0))
                    base_team.rank = int(team.get("recordOverall", {}).get("rank", 0))

                    # add team to matchup teams
                    base_matchup.teams.append(base_team)

                    # add team to league teams by week
                    league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    if matchup.get(key + "Result") == "WIN":
                        base_matchup.winner = base_team
                    elif matchup.get(key + "Result") == "TIE":
                        # TODO: how to set winner/loser with ties?
                        pass
                    else:
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
                        base_player.headshot_url = flea_pro_player.get("headshotUrl")
                        base_player.owner_team_id = flea_league_player.get("owner", {}).get("id")
                        base_player.owner_team_name = flea_league_player.get("owner", {}).get("name")
                        base_player.percent_owned = 0
                        base_player.points = float(flea_league_player.get("viewingActualPoints", {}).get("value", 0))
                        base_player.projected_points = None

                        base_player.position_type = "O" if flea_pro_player.get(
                            "position") in self.offensive_positions else "D"
                        base_player.primary_position = flea_pro_player.get("position")

                        base_player.selected_position = flea_player_position.get("label")
                        base_player.selected_position_is_flex = True if "/" in flea_pro_player.get("position") else False
                        base_player.status = flea_pro_player.get("injury", {}).get("typeAbbreviaition")

                        base_player.eligible_positions = [pos for positions in flea_league_player.get(
                            "rankFantasy", {}).get("positions", {}) for pos in positions.get("position", {}).get(
                            "eligibility")]

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
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.rank)

        return league
