__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import json
import logging
import os
from collections import OrderedDict

import requests

logger = logging.getLogger(__name__)


class BeefStats(object):

    def __init__(self, data_dir, save_data=False, dev_offline=False, refresh=False):
        """
        Initialize class, load data from FOX Sports, and combine defensive player data
        """
        self.save_data = save_data
        self.dev_offline = dev_offline
        self.refresh = refresh

        # nfl team abbreviations
        self.nfl_team_abbreviations = [
            "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
            "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
            "LAC", "LAR", "MIA", "MIN", "NE", "NO", "NYG", "NYJ",
            "OAK", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
        ]

        # small reference dict to convert between commonly used alternate team abbreviations
        self.team_abbrev_conversion_dict = {
            "JAC": "JAX",
            "LA": "LAR"
        }

        self.fox_sports_public_api_key = {"apikey": "jE7yBJVRNAwdDesMgTzTXUUSx1It41Fq"}
        self.teams_url = "https://api.foxsports.com/sportsdata/v1/football/nfl/teams.json"
        self.tabbu_value = 500.0

        self.raw_player_data = {}
        self.raw_player_data_file_path = os.path.join(data_dir, "beef_raw_data.json")

        self.beef_data = {}
        self.beef_data_file_path = os.path.join(data_dir, "beef_data.json")
        if not self.refresh:
            self.open_beef_data()

        # fetch weights of players from the web if not running in offline mode or refresh=True
        if self.refresh or not self.dev_offline:
            if not self.beef_data:
                fox_sports_nfl_teams_data = requests.get(self.teams_url, params=self.fox_sports_public_api_key).json()

                for team in fox_sports_nfl_teams_data.get("page"):
                    team_url = team.get("links").get("api").get("athletes")
                    team_roster = requests.get(team_url, self.fox_sports_public_api_key).json()
                    for player_json in team_roster.get("page"):
                        player_full_name = player_json.get("firstName") + " " + player_json.get("lastName")
                        self.add_entry(player_full_name, player_json, team)

                self.save_beef_data()

        # if offline mode, load pre-fetched weight data (only works if you've previously run application with -s flag)
        else:
            if not self.beef_data:
                raise FileNotFoundError(
                    "FILE {} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        self.beef_data_file_path))

        if len(self.beef_data) == 0:
            logger.warning(
                "NO beef data was loaded, please check your internet connection or the availability of "
                "'https://api.foxsports.com/sportsdata/v1/football/nfl.json?apikey=jE7yBJVRNAwdDesMgTzTXUUSx1It41Fq' "
                "and try generating a new report.")
        else:
            logger.info("{} player weights/TABBUs were loaded".format(len(self.beef_data)))

    def open_beef_data(self):
        if os.path.exists(self.beef_data_file_path):
            with open(self.beef_data_file_path, "r", encoding="utf-8") as beef_in:
                self.beef_data = dict(json.load(beef_in))

    def save_beef_data(self):
        if self.save_data:
            with open(self.beef_data_file_path, "w", encoding="utf-8") as beef_out:
                json.dump(self.beef_data, beef_out, ensure_ascii=False, indent=2)

    def add_entry(self, player_full_name, player_json=None, team_json=None):

        if player_json:
            # add raw player data json to raw_player_data for output and later reference
            self.raw_player_data[player_full_name] = player_json

            player_team = team_json.get("abbreviation")
            player_beef_dict = {
                "fullName": player_full_name,
                "firstName": player_json.get("firstName").replace(".", ""),
                "lastName": player_json.get("lastName"),
                "weight": player_json.get("weight"),
                "tabbu": float(player_json.get("weight")) / float(self.tabbu_value),
                "position": player_json.get("position").get("abbreviation"),
                "team": player_team
            }

            if player_full_name not in self.beef_data.keys():
                self.beef_data[player_full_name] = player_beef_dict

            if player_json.get("position").get("abbreviation") in ["CB", "LB", "DE", "DT", "S"]:
                if team_json.get("abbreviation") not in self.beef_data.keys():
                    self.beef_data[team_json.get("abbreviation")] = {
                        "weight": player_json.get("weight"),
                        "tabbu": float(player_json.get("weight")) / self.tabbu_value,
                        "players": {player_full_name: player_beef_dict}
                    }
                else:
                    weight = self.beef_data[team_json.get("abbreviation")].get("weight") + float(
                        player_json.get("weight"))
                    tabbu = self.beef_data[team_json.get("abbreviation")].get("tabbu") + (
                            float(player_json.get("weight")) / self.tabbu_value)

                    team_def_entry = self.beef_data[team_json.get("abbreviation")]
                    team_def_entry["weight"] = weight
                    team_def_entry["tabbu"] = tabbu
                    team_def_entry["players"][player_full_name] = player_beef_dict
        else:
            player_beef_dict = {
                "fullName": player_full_name,
                "weight": 0,
                "tabbu": 0,
            }

        self.beef_data[player_full_name] = player_beef_dict
        return player_beef_dict

    def get_player_beef_stat(self, player_first_name, player_last_name, team_abbr, key_str):
        team_abbr = team_abbr.upper() if team_abbr else "?"

        if player_last_name:
            player_full_name = player_first_name + " " + player_last_name
        else:
            if team_abbr not in self.nfl_team_abbreviations:
                if team_abbr in self.team_abbrev_conversion_dict.keys():
                    team_abbr = self.team_abbrev_conversion_dict[team_abbr]
            player_full_name = team_abbr

        if player_full_name in self.beef_data.keys():
            return self.beef_data[player_full_name][key_str]
        else:
            logger.debug(
                "Player not found: {}. Setting weight and TABBU to 0. Run report with the -r flag "
                "(--refresh-web-data) to refresh all external web data and try again.".format(player_full_name))

            self.beef_data[player_full_name] = {
                "fullName": player_full_name,
                "weight": 0,
                "tabbu": 0,
            }
            return self.beef_data[player_full_name][key_str]

    def get_player_weight(self, player_first_name, player_last_name, team_abbr):
        return self.get_player_beef_stat(player_first_name, player_last_name, team_abbr, "weight")

    def get_player_tabbu(self, player_first_name, player_last_name, team_abbr):
        return self.get_player_beef_stat(player_first_name, player_last_name, team_abbr, "tabbu")

    def generate_player_info_json(self):
        ordered_player_data = OrderedDict(sorted(self.raw_player_data.items(), key=lambda k_v: k_v[0]))
        with open(self.raw_player_data_file_path, mode="w", encoding="utf-8") as player_data:
            json.dump(ordered_player_data, player_data, ensure_ascii=False, indent=2)

    def __str__(self):
        return json.dumps(self.beef_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.beef_data, indent=2, ensure_ascii=False)
