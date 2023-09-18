__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
from collections import OrderedDict
from pathlib import Path

import requests

from report.logger import get_logger

logger = get_logger(__name__, propagate=False)


class BeefStats(object):

    def __init__(self, data_dir, save_data=False, dev_offline=False, refresh=False):
        """
        Initialize class, load data from Sleeper API, and combine defensive player data into team total
        """
        logger.debug("Initializing beef stats.")

        self.save_data = save_data
        self.dev_offline = dev_offline
        self.refresh = refresh

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

        self.nfl_player_data_url = "https://api.sleeper.app/v1/players/nfl"
        self.tabbu_value = 500.0

        self.raw_player_data = {}
        self.raw_player_data_file_path = Path(data_dir) / "beef_raw_data.json"

        self.beef_data = {}
        self.beef_data_file_path = Path(data_dir) / "beef_data.json"
        if not self.refresh:
            self.open_beef_data()

        # fetch weights of players from the web if not running in offline mode or refresh=True
        if self.refresh or not self.dev_offline:
            if not self.beef_data:
                logger.debug("Retrieving beef data from the web.")

                nfl_player_data = requests.get(self.nfl_player_data_url).json()
                for player_sleeper_key, player_data in nfl_player_data.items():
                    self.add_entry(player_data)

                self.save_beef_data()

        # if offline mode, load pre-fetched weight data (only works if you've previously run application with -s flag)
        else:
            if not self.beef_data:
                raise FileNotFoundError(
                    f"FILE {self.beef_data_file_path} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY "
                    f"SAVED DATA!"
                )

        if len(self.beef_data) == 0:
            logger.warning(
                "NO beef data was loaded, please check your internet connection or the availability of "
                "\"https://api.sleeper.app/v1/players/nfl\" and try generating a new report.")
        else:
            logger.info(f"{len(self.beef_data)} player weights/TABBUs were loaded")

    def open_beef_data(self):
        logger.debug("Loading saved beef data.")
        if Path(self.beef_data_file_path).exists():
            with open(self.beef_data_file_path, "r", encoding="utf-8") as beef_in:
                self.beef_data = dict(json.load(beef_in))

    def save_beef_data(self):
        if self.save_data:
            logger.debug("Saving beef data.")
            with open(self.beef_data_file_path, "w", encoding="utf-8") as beef_out:
                json.dump(self.beef_data, beef_out, ensure_ascii=False, indent=2)

    def add_entry(self, player_json=None):

        player_full_name = player_json.get("full_name", "")
        if player_json and player_json.get("team") is not None and player_json.get(
                "fantasy_positions") is not None and "DEF" not in player_json.get("fantasy_positions"):

            # add raw player data json to raw_player_data for output and later reference
            self.raw_player_data[player_full_name] = player_json

            player_beef_dict = {
                "fullName": player_full_name,
                "firstName": player_json.get("first_name").replace(".", ""),
                "lastName": player_json.get("last_name"),
                "weight": float(player_json.get("weight")) if player_json.get("weight") != "" else 0.0,
                "tabbu": (float(player_json.get("weight")) if player_json.get("weight") != "" else 0.0) / float(
                    self.tabbu_value),
                "position": player_json.get("position"),
                "team": player_json.get("team")
            }

            if player_full_name not in self.beef_data.keys():
                self.beef_data[player_full_name] = player_beef_dict

            positions = set()
            position_types = player_json.get("fantasy_positions")
            if position_types and not positions.intersection(("OL", "RB", "WR", "TE")) and (
                    "DL" in position_types or "DB" in position_types):

                if player_beef_dict.get("team") not in self.beef_data.keys():
                    self.beef_data[player_beef_dict.get("team")] = {
                        "weight": player_beef_dict.get("weight"),
                        "tabbu": player_beef_dict.get("weight") / self.tabbu_value,
                        "players": {player_full_name: player_beef_dict}
                    }
                else:
                    weight = self.beef_data[player_beef_dict.get("team")].get("weight") + player_beef_dict.get("weight")
                    tabbu = self.beef_data[player_beef_dict.get("team")].get("tabbu") + (
                            player_beef_dict.get("weight") / self.tabbu_value)

                    team_def_entry = self.beef_data[player_beef_dict.get("team")]
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

    def get_player_beef_stat(self, player_first_name, player_last_name, player_team_abbr, key_str):

        team_abbr = player_team_abbr.upper() if player_team_abbr else "?"
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
                f"Player not found: {player_full_name}. Setting weight and TABBU to 0. Run report with the -r flag "
                f"(--refresh-web-data) to refresh all external web data and try again."
            )

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
