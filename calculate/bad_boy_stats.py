__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import itertools
import json
import os
import re
import string
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup

from report.logger import get_logger

logger = get_logger(__name__, propagate=True)


class BadBoyStats(object):

    def __init__(self, data_dir, save_data=False, dev_offline=False, refresh=False):
        """ Initialize class, load data from USA Today NFL Arrest DB. Combine defensive player data
        """
        logger.debug("Initializing bad boy stats.")

        self.save_data = save_data
        self.dev_offline = dev_offline
        self.refresh = refresh

        # nfl team abbreviations
        self.nfl_team_abbreviations = [
            "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
            "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAC", "KC",
            "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
            "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
        ]

        # small reference dict to convert between commonly used alternate team abbreviations
        self.team_abbrev_conversion_dict = {
            "JAX": "JAC",
            "LAR": "LA"
        }

        # position type reference
        self.position_types = {
            "C": "D", "CB": "D", "DB": "D", "DE": "D", "DE/DT": "D", "DT": "D", "LB": "D", "S": "D", "Safety": "D",
            # defense
            "FB": "O", "QB": "O", "RB": "O", "TE": "O", "WR": "O",  # offense
            "K": "S", "P": "S",  # special teams
            "OG": "L", "OL": "L", "OT": "L",  # offensive line
            "OC": "C",  # coaching staff
        }

        # create parent directory if it does not exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Load the scoring based on crime categories
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "files",
                               "crime-categories.json"), mode="r", encoding="utf-8") as crimes:
            self.crime_rankings = json.load(crimes)
            logger.debug("Crime categories loaded.")

        # for outputting all unique crime categories found in the USA Today NFL arrests data
        self.unique_crime_categories_for_output = {}

        # preserve raw retrieved player crime data for reference and later usage
        self.raw_bad_boy_data = {}
        self.raw_bad_boy_data_file_path = os.path.join(data_dir, "bad_boy_raw_data.json")

        # for collecting all retrieved bad boy data
        self.bad_boy_data = {}
        self.bad_boy_data_file_path = os.path.join(data_dir, "bad_boy_data.json")

        # load preexisting (saved) bad boy data (if it exists) if refresh=False
        if not self.refresh:
            self.open_bad_boy_data()

        # fetch crimes of players from the web if not running in offline mode or if refresh=True
        if self.refresh or not self.dev_offline:
            if not self.bad_boy_data:
                logger.debug("Retrieving bad boy data from the web.")

                usa_today_nfl_arrest_url = "https://www.usatoday.com/sports/nfl/arrests/"
                r = requests.get(usa_today_nfl_arrest_url)
                data = r.text
                soup = BeautifulSoup(data, "html.parser")
                cdata = re.search("var sitedata = (.*);", soup.find(text=re.compile("CDATA"))).group(1)
                ajax_nonce = json.loads(cdata)["ajax_nonce"]

                usa_today_nfl_arrest_url = "https://databases.usatoday.com/wp-admin/admin-ajax.php"
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }

                # example ajax query body
                # example_body = (
                #     'action=cspFetchTable&'
                #     'security=61406e4feb&'
                #     'pageID=10&'
                #     'sortBy=Date&'
                #     'sortOrder=desc&'
                #     'searches={"Last_name":"hill","Team":"SEA","First_name":"leroy"}'
                # )
                arrests = []
                for team in self.nfl_team_abbreviations:

                    page_num = 1
                    body = (
                            'action=cspFetchTable&'
                            'security=' + ajax_nonce + '&'
                                                       'pageID=10&'
                                                       'sortBy=Date&'
                                                       'sortOrder=desc&'
                                                       'page=' + str(page_num) + '&'
                                                                                 'searches={"Team":"' + team + '"}'
                    )

                    r = requests.post(usa_today_nfl_arrest_url, data=body, headers=headers)
                    resp_json = r.json()

                    arrests_data = resp_json["data"]["Result"]

                    for arrest in arrests_data:
                        arrests.append({
                            "name": arrest["First_name"] + " " + arrest["Last_name"],
                            "team": "FA" if (arrest["Team"] == "Free agent" or arrest["Team"] == "Free Agent")
                            else arrest["Team"],
                            "date": arrest["Date"],
                            "position": arrest["Position"],
                            "position_type": self.position_types[arrest["Position"]],
                            "case": arrest["Case_1"].upper(),
                            "crime": arrest["Category"].upper(),
                            "description": arrest["Description"],
                            "outcome": arrest["Outcome"]
                        })

                    total_results = resp_json["data"]["totalResults"]

                    # the USA Today NFL arrests database only retrieves 20 entries per request
                    if total_results > 20:
                        if (total_results % 20) > 0:
                            num_pages = (total_results // 20) + 1
                        else:
                            num_pages = total_results // 20

                        for page in range(2, num_pages + 1):
                            page_num += 1
                            body = (
                                'action=cspFetchTable&'
                                'security=' + ajax_nonce + '&'
                                'pageID=10&'
                                'sortBy=Date&'
                                'sortOrder=desc&'
                                'page=' + str(page_num) + '&'
                                'searches={"Team":"' + team + '"}'
                            )

                            r = requests.post(usa_today_nfl_arrest_url, data=body, headers=headers)
                            resp_json = r.json()

                            arrests_data = resp_json["data"]["Result"]

                            for arrest in arrests_data:
                                arrests.append({
                                    "name": arrest["First_name"] + " " + arrest["Last_name"],
                                    "team": "FA" if (arrest["Team"] == "Free agent" or arrest["Team"] == "Free Agent")
                                    else arrest["Team"],
                                    "date": arrest["Date"],
                                    "position": arrest["Position"],
                                    "position_type": self.position_types[arrest["Position"]],
                                    "case": arrest["Case_1"].upper(),
                                    "crime": arrest["Category"].upper(),
                                    "description": arrest["Description"],
                                    "outcome": arrest["Outcome"]
                                })

                arrests_by_team = {
                    key: list(group) for key, group in itertools.groupby(
                        sorted(arrests, key=lambda x: x["team"]),
                        lambda x: x["team"]
                    )
                }

                for team_abbr in self.nfl_team_abbreviations:
                    self.add_entry(team_abbr, arrests_by_team.get(team_abbr))

                self.save_bad_boy_data()

        # if offline mode, load pre-fetched bad boy data (only works if you've previously run application with -s flag)
        else:
            if not self.bad_boy_data:
                raise FileNotFoundError(
                    "FILE {0} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        self.bad_boy_data_file_path))

        if len(self.bad_boy_data) == 0:
            logger.warning(
                "NO bad boy records were loaded, please check your internet connection or the availability of "
                "\"https://www.usatoday.com/sports/nfl/arrests/\" and try generating a new report.")
        else:
            logger.info("{0} bad boy records loaded".format(len(self.bad_boy_data)))

    def open_bad_boy_data(self):
        logger.debug("Loading saved bay boy data.")
        if os.path.exists(self.bad_boy_data_file_path):
            with open(self.bad_boy_data_file_path, "r", encoding="utf-8") as bad_boy_in:
                self.bad_boy_data = dict(json.load(bad_boy_in))

    def save_bad_boy_data(self):
        if self.save_data:
            logger.debug("Saving bad boy data and raw player crime data.")
            # save report bad boy data locally
            with open(self.bad_boy_data_file_path, "w", encoding="utf-8") as bad_boy_out:
                json.dump(self.bad_boy_data, bad_boy_out, ensure_ascii=False, indent=2)

            # save raw player crime data locally
            with open(self.raw_bad_boy_data_file_path, "w", encoding="utf-8") as bad_boy_raw_out:
                json.dump(self.raw_bad_boy_data, bad_boy_raw_out, ensure_ascii=False, indent=2)

    def add_entry(self, team_abbr, arrests):

        if arrests:
            nfl_team = {
                "pos": "DEF",
                "players": {},
                "total_points": 0,
                "offenders": [],
                "num_offenders": 0,
                "worst_offense": None,
                "worst_offense_points": 0
            }

            for player_arrest in arrests:
                player_name = player_arrest.get("name")
                player_pos = player_arrest.get("position")
                player_pos_type = player_arrest.get("position_type")
                offense_category = str.upper(player_arrest.get("crime"))

                # Add each crime to output categories for generation of crime-categories-output.json file, which can
                # be used to replace the existing crime-categories.json file. Each new crime categories will default to
                # a score of 0, and must have its score manually assigned within the json file.
                self.unique_crime_categories_for_output[offense_category] = self.crime_rankings.get(offense_category, 0)

                # add raw player arrest data to raw data collection
                self.raw_bad_boy_data[player_name] = player_arrest

                if offense_category in self.crime_rankings.keys():
                    offense_points = self.crime_rankings.get(offense_category)
                else:
                    offense_points = 0
                    logger.warning("Crime ranking not found: \"%s\". Assigning score of 0." % offense_category)

                nfl_player = {
                    "team": team_abbr,
                    "pos": player_pos,
                    "offenses": [],
                    "total_points": 0,
                    "worst_offense": None,
                    "worst_offense_points": 0
                }

                # update player entry
                nfl_player["offenses"].append({offense_category: offense_points})
                nfl_player["total_points"] += offense_points

                if offense_points > nfl_player["worst_offense_points"]:
                    nfl_player["worst_offense"] = offense_category
                    nfl_player["worst_offense_points"] = offense_points

                self.bad_boy_data[player_name] = nfl_player

                # update team DEF entry
                if player_pos_type == "D":
                    nfl_team["players"][player_name] = self.bad_boy_data[player_name]
                    nfl_team["total_points"] += offense_points
                    nfl_team["offenders"].append(player_name)
                    nfl_team["offenders"] = list(set(nfl_team["offenders"]))
                    nfl_team["num_offenders"] = len(nfl_team["offenders"])

                    if offense_points > nfl_team["worst_offense_points"]:
                        nfl_team["worst_offense"] = offense_category
                        nfl_team["worst_offense_points"] = offense_points

            self.bad_boy_data[team_abbr] = nfl_team

    def get_player_bad_boy_stats(self, player_first_name, player_last_name, player_team_abbr, player_pos, key_str=""):
        """ Looks up given player and returns number of "bad boy" points based on custom crime scoring.

        TODO: maybe limit for years and adjust defensive players rolling up to DEF team as it skews DEF scores high
        :param player_first_name: First name of player to look up
        :param player_last_name: Last name of player to look up
        :param player_team_abbr: Player's team (maybe limit to only crimes while on that team...or for DEF players???)
        :param player_pos: Player's position
        :param key_str: which player information to retrieve (crime: "worst_offense" or bad boy points: "total_points")
        :return: Ether integer number of bad boy points or crime recorded (depending on key_str)
        """
        player_team = str.upper(player_team_abbr) if player_team_abbr else "?"
        if player_team not in self.nfl_team_abbreviations:
            if player_team in self.team_abbrev_conversion_dict.keys():
                player_team = self.team_abbrev_conversion_dict[player_team]

        player_full_name = (
                (string.capwords(player_first_name) if player_first_name else "") +
                (" " if player_first_name and player_last_name else "") +
                (string.capwords(player_last_name) if player_last_name else "")
        ).strip()

        # TODO: figure out how to include only ACTIVE players in team DEF rollups
        if player_pos == "DEF":
            # player_full_name = player_team
            player_full_name = "TEMPORARY DISABLING OF TEAM DEFENSES IN BAD BOY POINTS"
        if player_full_name in self.bad_boy_data:
            return self.bad_boy_data[player_full_name][key_str] if key_str else self.bad_boy_data[player_full_name]
        else:
            logger.debug(
                "Player not found: {0}. Setting crime category and bad boy points to 0. Run report with the -r flag "
                "(--refresh-web-data) to refresh all external web data and try again.".format(player_full_name))

            self.bad_boy_data[player_full_name] = {
                "team": player_team,
                "pos": player_pos,
                "offenses": [],
                "total_points": 0,
                "worst_offense": None,
                "worst_offense_points": 0
            }
            return self.bad_boy_data[player_full_name][key_str] if key_str else self.bad_boy_data[player_full_name]

    def get_player_bad_boy_crime(self, player_first_name, player_last_name, player_team, player_pos):
        return self.get_player_bad_boy_stats(player_first_name, player_last_name, player_team, player_pos,
                                             "worst_offense")

    def get_player_bad_boy_points(self, player_first_name, player_last_name, player_team, player_pos):
        return self.get_player_bad_boy_stats(player_first_name, player_last_name, player_team, player_pos,
                                             "total_points")

    def get_player_bad_boy_num_offenders(self, player_first_name, player_last_name, player_team, player_pos):
        player_bad_boy_stats = self.get_player_bad_boy_stats(player_first_name, player_last_name, player_team,
                                                             player_pos)
        if player_bad_boy_stats.get("pos") == "DEF":
            return player_bad_boy_stats.get("num_offenders")
        else:
            return 0

    def generate_crime_categories_json(self):
        unique_crimes = OrderedDict(sorted(self.unique_crime_categories_for_output.items(), key=lambda k_v: k_v[0]))
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "files",
                               "crime-categories-output.json"), mode="w", encoding="utf-8") as crimes:
            json.dump(unique_crimes, crimes, ensure_ascii=False, indent=2)

    def __str__(self):
        return json.dumps(self.bad_boy_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.bad_boy_data, indent=2, ensure_ascii=False)
