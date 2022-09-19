__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import itertools
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from report.logger import get_logger
from utils.app_config_parser import AppConfigParser

logger = get_logger(__name__, propagate=False)


class CovidRisk(object):

    def __init__(self, config, data_dir, season, week, save_data=False, dev_offline=False, refresh=False):
        logger.debug("Initializing COVID-19 risk.")

        self.config = config  # type: AppConfigParser

        self.season = int(season)
        self.week = int(week)
        self.selected_nfl_season_week = datetime.strptime(
            "{0} {1} 1".format(str(self.season), str(self.week + 36)), "%G %V %u")

        self.save_data = save_data
        self.dev_offline = dev_offline
        self.refresh = refresh

        nfl_team_abbrev_ref = {
            "Arizona Cardinals": "ARI",
            "Atlanta Falcons": "ATL",
            "Baltimore Ravens": "BAL",
            "Buffalo Bills": "BUF",
            "Carolina Panthers": "CAR",
            "Chicago Bears": "CHI",
            "Cincinnati Bengals": "CIN",
            "Cleveland Browns": "CLE",
            "Dallas Cowboys": "DAL",
            "Denver Broncos": "DEN",
            "Detroit Lions": "DET",
            "Green Bay Packers": "GB",
            "Houston Texans": "HOU",
            "Indianapolis Colts": "IND",
            "Jacksonville Jaguars": "JAX",
            "Kansas City Chiefs": "KC",
            "Las Vegas Raiders": "LV",
            "Los Angeles Chargers": "LAC",
            "Los Angeles Rams": "LAR",
            "Miami Dolphins": "MIA",
            "Minnesota Vikings": "MIN",
            "New England Patriots": "NE",
            "New Orleans Saints": "NO",
            "New York Giants": "NYG",
            "New York Jets": "NYJ",
            "Philadelphia Eagles": "PHI",
            "Pittsburgh Steelers": "PIT",
            "San Francisco 49ers": "SF",
            "Seattle Seahawks": "SEA",
            "Tampa Bay Buccaneers": "TB",
            "Tennessee Titans": "TEN",
            "Washington Football Team": "WAS"
        }

        # nfl team abbreviations
        self.nfl_team_abbreviations = [
            "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
            "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
            "LAR", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
            "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
        ]

        # small reference dict to convert between commonly used alternate team abbreviations
        self.team_abbrev_conversion_dict = {
            "JAC": "JAX",
            "LA": "LAR"
        }

        self.raw_covid_data = {}
        self.raw_covid_data_file_path = Path(data_dir) / "covid_raw_data.json"

        self.covid_data = {}
        self.covid_data_file_path = Path(data_dir) / "covid_data.json"

        # load preexisting (saved) covid data (if it exists) if refresh=False
        if not self.refresh:
            self.open_covid_data()

        # fetch NFL player transactions from the web if not running in offline mode or refresh=True
        if self.refresh or not self.dev_offline:
            if not self.covid_data and self.season >= 2020:
                logger.debug("Retrieving COVID-19 data from the web.")

                football_db_endpoint = "https://www.footballdb.com/transactions/index.html?period={0}&period={1}".format(
                    str(self.season + 1),
                    str(self.season)
                )
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, " +
                                  "like Gecko) Version/13.0 Safari/605.1.15"
                }
                r = requests.get(football_db_endpoint, headers=headers)
                data = r.text
                soup = BeautifulSoup(data, "html.parser")
                self.covid_data = {}

                covid_transactions = []
                for row in soup.findAll(attrs={"class": "td w25 rowtitle"}):

                    transactions_html = row.findNext(attrs={"class": "td w75 td-clear"})

                    if "covid" in str(transactions_html.text).lower():
                        transaction_date = row.findPrevious(attrs={"class": "stacktable-title"}).text
                        transaction_team = nfl_team_abbrev_ref.get(row.b.text)

                        if datetime.strptime(transaction_date, "%B %d, %Y") <= self.selected_nfl_season_week:
                            for transaction in str(transactions_html).split("."):
                                if "covid" in transaction.lower():
                                    for player in BeautifulSoup(transaction, "html.parser").findAll("a"):
                                        transaction_action = ""
                                        if "placed" in transaction.lower():
                                            transaction_action = "add"
                                        elif "activated" in transaction.lower():
                                            transaction_action = "remove"

                                        player_transaction = {
                                            "date": transaction_date,
                                            "team": transaction_team,
                                            "action": transaction_action,
                                            "list": "Reserve/COVID-19",
                                            "player": player.text
                                        }

                                        covid_transactions.append(player_transaction)
                                        self.add_entry(player.text, player_transaction)

                self.raw_covid_data = {
                    key: {
                        "transactions": sorted(
                            list(group),
                            key=lambda x: datetime.strptime(x["date"], "%B %d, %Y"),
                            reverse=True
                        )
                    } for key, group in itertools.groupby(
                        sorted(covid_transactions, key=lambda x: x["team"]),
                        lambda x: x["team"]
                    )
                }

                for team, data in self.raw_covid_data.items():
                    data["last_date"] = data["transactions"][0].get("date")
                    data["count"] = len(data["transactions"])
                    data["transactions"] = {
                        key: [
                            {
                                k: item[k] for k in item if k != "timestamp"
                            } for item in sorted(
                                list(group),
                                key=lambda x: datetime.strptime(x["date"], "%B %d, %Y")
                            )
                        ] for key, group in itertools.groupby(
                            sorted(data["transactions"], key=lambda x: x["action"]),
                            lambda x: x["action"]
                        )
                    }

                self.save_covid_data()

        # if offline mode, load pre-fetched covid data (only works if you've previously run application with -s flag)
        else:
            if not self.covid_data and self.season >= 2020:
                raise FileNotFoundError(
                    "FILE {0} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        self.covid_data_file_path))

        if len(self.covid_data) == 0 and self.season >= 2020:
            logger.warning(
                "NO COVID-19 data was loaded, please check your internet connection or the availability of "
                "\"https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/transactions?region=us&lang=en"
                "&contentorigin=espn\" and try generating a new report.")
        elif self.season < 2020:
            logger.warning("COVID-19 was not a factor during NFL seasons prior to 2020, so metric is being ignored.")
        else:
            logger.info("{0} players at risk of COVID-19 were loaded".format(len(self.covid_data)))

    def open_covid_data(self):
        logger.debug("Loading saved COVID-19 risk data.")
        if Path(self.covid_data_file_path).exists():
            with open(self.covid_data_file_path, "r", encoding="utf-8") as covid_in:
                self.covid_data = dict(json.load(covid_in))

        if Path(self.raw_covid_data_file_path).exists():
            with open(self.raw_covid_data_file_path, "r", encoding="utf-8") as covid_raw_in:
                self.raw_covid_data = dict(json.load(covid_raw_in))

    def save_covid_data(self):
        if self.save_data:
            logger.debug("Saving COVID-19 risk data.")
            # save report covid data locally
            with open(self.covid_data_file_path, "w", encoding="utf-8") as covid_out:
                json.dump(self.covid_data, covid_out, ensure_ascii=False, indent=2)

            # save raw player covid data locally
            with open(self.raw_covid_data_file_path, "w", encoding="utf-8") as covid_raw_out:
                json.dump(self.raw_covid_data, covid_raw_out, ensure_ascii=False, indent=2)

    def add_entry(self, player_full_name, player_transaction):

        if player_transaction:
            if player_full_name not in self.covid_data:
                self.covid_data[player_full_name] = {
                    "team": player_transaction.get("team"),
                    "transactions": [player_transaction],
                    "last_date": player_transaction.get("date")
                }
            else:
                self.covid_data.get(player_full_name).get("transactions").append(player_transaction)

                if datetime.strptime(self.covid_data.get(player_full_name).get("last_date"), "%B %d, %Y") < \
                        datetime.strptime(player_transaction.get("date"), "%B %d, %Y"):
                    self.covid_data.get(player_full_name)["last_date"] = player_transaction.get("date")

            # TODO: incorporate team defenses into COVID-19 risk factor metric
            # player_team_abbr = player_transaction.get("team")
            # if player_team_abbr not in self.covid_data:
            #     self.covid_data[player_team_abbr] = {
            #         "transactions": [player_transaction],
            #         "count": self.raw_covid_data.get(player_team_abbr).get("count"),
            #         "last_date": self.raw_covid_data.get(player_team_abbr).get("last_date")
            #     }
            # else:
            #     self.covid_data.get(player_team_abbr).get("transactions").append(player_transaction)

    # noinspection PyUnusedLocal
    def get_player_covid_risk(self, player_full_name, player_team_abbr, player_pos):

        team_abbr = player_team_abbr.upper() if player_team_abbr else "?"
        if team_abbr not in self.nfl_team_abbreviations:
            if team_abbr in self.team_abbrev_conversion_dict.keys():
                team_abbr = self.team_abbrev_conversion_dict[team_abbr]

        covid_risk_score = 0
        player_on_covid_list_past = False
        player_on_covid_list_present = False

        if team_abbr in self.raw_covid_data.keys():

            for transaction in self.raw_covid_data.get(team_abbr).get("transactions").get("add"):
                if player_full_name == transaction.get("player"):
                    player_on_covid_list_past = True
                    player_on_covid_list_present = True

            if self.raw_covid_data.get(team_abbr).get("transactions").get("remove"):
                for transaction in self.raw_covid_data.get(team_abbr).get("transactions").get("remove"):
                    if player_full_name == transaction.get("player"):
                        player_on_covid_list_past = True
                        player_on_covid_list_present = False

            if player_on_covid_list_present:
                # add 10 if the player is currently on the Reserve/COVID-19 list
                covid_risk_score += 10
            elif player_on_covid_list_past:
                # add 5 if the player is no longer on the Reserve/COVID-19 list but was previously
                covid_risk_score += 5

            # add 1 for every other player on the same team who has been on the Reserve/COVID-19 list
            covid_risk_score += (self.raw_covid_data.get(team_abbr).get("count") - 1)

            selected_nfl_season_week = datetime.strptime(
                "{0} {1} 1".format(str(self.season), str(self.week + 36)), "%G %V %u")

            covid_recency = selected_nfl_season_week - datetime.strptime(
                self.raw_covid_data.get(team_abbr).get("last_date"), "%B %d, %Y")
            if covid_recency < timedelta(days=14) and not player_on_covid_list_present:
                # add 10 if a teammate was on the Reserve/COVID-19 list within the past 14 days (COVID-19 risk window)
                covid_risk_score += 10
            else:
                # add 10 then subtract 1 for every day beyond 14 days a teammate was last on the Reserve/COVID-19 list
                recency_risk = 10 - (timedelta(days=14) - covid_recency).days
                covid_risk_score += ((10 - recency_risk) if 10 >= recency_risk >= 0 else 0)

        else:
            logger.debug(
                "Team {0} has no Reserve/COVID-19 transactions. Setting player COVID-19 risk to 0. Run report with the "
                "-r flag (--refresh-web-data) to refresh all external web data and try again.".format(
                    team_abbr, player_full_name))

        return covid_risk_score

    def generate_covid_risk_json(self):
        ordered_covid_risk_data = OrderedDict(sorted(self.raw_covid_data.items(), key=lambda k_v: k_v[0]))
        with open(self.raw_covid_data_file_path, mode="w", encoding="utf-8") as covid_data:
            json.dump(ordered_covid_risk_data, covid_data, ensure_ascii=False, indent=2)

    def __str__(self):
        return json.dumps(self.covid_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.covid_data, indent=2, ensure_ascii=False)
