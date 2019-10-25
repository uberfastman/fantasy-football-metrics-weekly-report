__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import json
import logging
import os
from collections import OrderedDict

import requests

logger = logging.getLogger(__name__)


class BadBoyStats(object):

    def __init__(self, data_dir, save_data=False, dev_offline=False, refresh=False):
        """ Initialize class, load data from USA Today NFL Arrest DB. Combine defensive player data
        """
        self.save_data = save_data
        self.dev_offline = dev_offline
        self.refresh = refresh

        # nfl team abbreviations
        self.nfl_team_abbreviations = [
            "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
            "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAC", "KC",  # http://nflarrest.com uses JAC for JAX
            "LAC", "LA", "MIA", "MIN", "NE", "NO", "NYG", "NYJ",  # http://nflarrest.com uses LA for LAR
            "OAK", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
        ]

        # small reference dict to convert between commonly used alternate team abbreviations
        self.team_abbrev_conversion_dict = {
            "JAX": "JAC",
            "LAR": "LA"
        }

        nfl_arrest_api_team_base_url = "https://nflarrest.com/api/v1/team/arrests/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Safari/605.1.15"
        }

        # create parent directory if it does not exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # Load the scoring based on crime categories
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "files",
                               "crime-categories.json"), mode="r", encoding="utf-8") as crimes:
            self.crime_rankings = json.load(crimes)

        # for outputting all unique crime categories found by nflarrest api
        self.unique_crime_categories_for_output = {}

        # preserve raw retrieved player crime data for reference and later usage
        self.raw_bad_boy_json = {}
        self.bad_boy_raw_data_file_path = os.path.join(data_dir, "bad_boy_raw_data.json")

        # for collecting all retrieved bad boy data
        self.bad_boy_data = {}
        self.bad_boy_data_file_path = os.path.join(data_dir, "bad_boy_data.json")

        # load preexisting (saved) bad boy data (if it exists) if refresh=False
        if not self.refresh:
            self.open_bad_boy_data()

        # fetch crimes of players from the web if not running in offline mode or if refresh=True
        if self.refresh or not self.dev_offline:
            if not self.bad_boy_data:
                for team_abbr in self.nfl_team_abbreviations:
                    response = requests.get(nfl_arrest_api_team_base_url + team_abbr, headers=headers)
                    logger.debug("Response {} for {} nflarrest query.".format(response.status_code, team_abbr))
                    self.add_entry(team_abbr, response)

                self.save_bad_boy_data()

        # if offline mode, load pre-fetched bad boy data (only works if you've previously run application with -s flag)
        else:
            if not self.bad_boy_data:
                raise FileNotFoundError(
                    "FILE {} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        self.bad_boy_data_file_path))

        if len(self.bad_boy_data) == 0:
            logger.warning(
                "NO bad boy records were loaded, please check your internet connection or the availability of "
                "'https://nflarrest.com/' and 'https://www.usatoday.com/sports/nfl/arrests/' and try generating a new "
                "report.")
        else:
            # print("{} bad boy records loaded".format(len(self.bad_boy_data)))
            logger.info("{} bad boy records loaded".format(len(self.bad_boy_data)))

    def open_bad_boy_data(self):
        if os.path.exists(self.bad_boy_data_file_path):
            with open(self.bad_boy_data_file_path, "r", encoding="utf-8") as bad_boy_in:
                self.bad_boy_data = dict(json.load(bad_boy_in))

    def save_bad_boy_data(self):
        if self.save_data:
            # save report bad boy data locally
            with open(self.bad_boy_data_file_path, "w", encoding="utf-8") as bad_boy_out:
                json.dump(self.bad_boy_data, bad_boy_out, ensure_ascii=False, indent=2)

            # save raw player crime data locally
            with open(self.bad_boy_raw_data_file_path, "w", encoding="utf-8") as bad_boy_raw_out:
                json.dump(self.raw_bad_boy_json, bad_boy_raw_out, ensure_ascii=False, indent=2)

    def add_entry(self, team_abbr, response):

        if response:
            nfl_team = {
                "pos": "DEF",
                "players": {},
                "total_points": 0,
                "offenders": [],
                "num_offenders": 0,
                "worst_offense": None,
                "worst_offense_points": 0
            }

            for player_arrest in response.json():
                player_name = player_arrest.get("Name")
                player_pos = player_arrest.get("Position")
                player_pos_type = player_arrest.get("Position_type")
                offense_category = str.upper(player_arrest.get("Category"))

                # Add each crime to output categories for generation of crime-categories-output.json file, which can
                # be used to replace the existing crime-categories.json file. Each new crime categories will default to
                # a score of 0, and must have its score manually assigned within the json file.
                self.unique_crime_categories_for_output[offense_category] = self.crime_rankings.get(offense_category, 0)

                # add raw player arrest data to raw data collection
                self.raw_bad_boy_json[player_name] = player_arrest

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

    def get_player_bad_boy_stats(self, player_full_name, player_team, player_pos, key_str=""):
        """ Looks up given player and returns number of 'bad boy' points based on custom crime scoring.

        TODO: maybe limit for years and adjust defensive players rolling up to DEF team as it skews DEF scores high
        :param player_full_name: Player name to look up
        :param player_team: Player's team (maybe later limit to only crimes while on that team...or for DEF players)
        :param player_pos: Player's position
        :param key_str: which player information to retrieve (crime: "worst_offense" or bad boy points: "total_points")
        :return: Ether integer number of bad boy points or crime recorded (depending on key_str)
        """
        player_team = str.upper(player_team) if player_team else "?"
        if player_team not in self.nfl_team_abbreviations:
            if player_team in self.team_abbrev_conversion_dict.keys():
                player_team = self.team_abbrev_conversion_dict[player_team]

        # TODO: figure out how to include only ACTIVE players in team DEF rollups
        if player_pos == "DEF":
            # player_full_name = player_team
            player_full_name = "TEMPORARY DISABLING OF TEAM DEFENSES IN BAD BOY POINTS"
        if player_full_name in self.bad_boy_data:
            return self.bad_boy_data[player_full_name][key_str] if key_str else self.bad_boy_data[player_full_name]
        else:
            logger.debug(
                "Player not found: {}. Setting crime category and bad boy points to 0. Run report with the -r flag "
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

    def get_player_bad_boy_crime(self, player_full_name, player_team, player_pos):
        return self.get_player_bad_boy_stats(player_full_name, player_team, player_pos, "worst_offense")

    def get_player_bad_boy_points(self, player_full_name, player_team, player_pos):
        return self.get_player_bad_boy_stats(player_full_name, player_team, player_pos, "total_points")

    def get_player_bad_boy_num_offenders(self, player_full_name, player_team, player_pos):
        player_bad_boy_stats = self.get_player_bad_boy_stats(player_full_name, player_team, player_pos)
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
