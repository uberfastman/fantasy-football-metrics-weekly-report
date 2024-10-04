__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import itertools
import json
import re
from collections import OrderedDict
from pathlib import Path
from string import capwords
from typing import Dict, Any, Union, Optional

import requests
from bs4 import BeautifulSoup

from features.base.feature import BaseFeature
from utilities.constants import nfl_team_abbreviations, nfl_team_abbreviation_conversions
from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class BadBoyFeature(BaseFeature):

    def __init__(self, data_dir: Path, root_dir: Path, refresh: bool = False, save_data: bool = False,
                 offline: bool = False):
        """Initialize class, load data from USA Today NFL Arrest DB. Combine defensive player data
        """
        # position type reference
        self.position_types: Dict[str, str] = {
            "C": "D", "CB": "D", "DB": "D", "DE": "D", "DE/DT": "D", "DT": "D", "LB": "D", "S": "D", "Safety": "D",
            # defense
            "FB": "O", "QB": "O", "RB": "O", "TE": "O", "WR": "O",  # offense
            "K": "S", "P": "S",  # special teams
            "OG": "L", "OL": "L", "OT": "L",  # offensive line
            "OC": "C",  # coaching staff
        }

        self.resource_files_dir = root_dir / "resources" / "files"

        # Load the scoring based on crime categories
        with open(self.resource_files_dir / "crime_categories.json", mode="r",
                  encoding="utf-8") as crimes:
            self.crime_rankings = json.load(crimes)
            logger.debug("Crime categories loaded.")

        # for outputting all unique crime categories found in the USA Today NFL arrests data
        self.unique_crime_categories_for_output = {}

        super().__init__(
            "bad_boy",
            "https://www.usatoday.com/sports/nfl/arrests",
            data_dir,
            refresh,
            save_data,
            offline
        )

    def _get_feature_data(self) -> None:
        logger.debug("Retrieving bad boy feature data from the web.")

        res = requests.get(self.feature_web_base_url)
        soup = BeautifulSoup(res.text, "html.parser")
        cdata = re.search("var sitedata = (.*);", soup.find(string=re.compile("CDATA"))).group(1)
        ajax_nonce = json.loads(cdata)["ajax_nonce"]

        usa_today_nfl_arrest_url = "https://databases.usatoday.com/wp-admin/admin-ajax.php"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        """
        Example ajax query body:
        
        example_body = (
            'action=cspFetchTable&'
            'security=61406e4feb&'
            'pageID=10&'
            'sortBy=Date&'
            'sortOrder=desc&'
            'searches={"Last_name":"hill","Team":"SEA","First_name":"leroy"}'
        )
        """
        arrests = []
        for team in nfl_team_abbreviations:

            page_num = 1
            body = (
                f"action=cspFetchTable"
                f"&security={ajax_nonce}"
                f"&pageID=10"
                f"&sortBy=Date"
                f"&sortOrder=desc"
                f"&page={page_num}"
                f"&searches={{\"Team\":\"{team}\"}}"
            )

            res_json = requests.post(usa_today_nfl_arrest_url, data=body, headers=headers).json()

            arrests_data = res_json["data"]["Result"]

            for arrest in arrests_data:
                arrests.append({
                    "name": f"{arrest['First_name']} {arrest['Last_name']}",
                    "team": (
                        "FA"
                        if (arrest["Team"] == "Free agent" or arrest["Team"] == "Free Agent")
                        else arrest["Team"]
                    ),
                    "date": arrest["Date"],
                    "position": arrest["Position"],
                    "position_type": self.position_types[arrest["Position"]],
                    "case": arrest["Case_1"].upper(),
                    "crime": arrest["Category"].upper(),
                    "description": arrest["Description"],
                    "outcome": arrest["Outcome"]
                })

            total_results = res_json["data"]["totalResults"]

            # the USA Today NFL arrests database only retrieves 20 entries per request
            if total_results > 20:
                if (total_results % 20) > 0:
                    num_pages = (total_results // 20) + 1
                else:
                    num_pages = total_results // 20

                for page in range(2, num_pages + 1):
                    page_num += 1
                    body = (
                        f"action=cspFetchTable"
                        f"&security={ajax_nonce}"
                        f"&pageID=10"
                        f"&sortBy=Date"
                        f"&sortOrder=desc"
                        f"&page={page_num}"
                        f"&searches={{\"Team\":\"{team}\"}}"
                    )

                    r = requests.post(usa_today_nfl_arrest_url, data=body, headers=headers)
                    resp_json = r.json()

                    arrests_data = resp_json["data"]["Result"]

                    for arrest in arrests_data:
                        arrests.append({
                            "name": f"{arrest['First_name']} {arrest['Last_name']}",
                            "team": (
                                "FA"
                                if (arrest["Team"] == "Free agent" or arrest["Team"] == "Free Agent")
                                else arrest["Team"]
                            ),
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

        for team_abbr in nfl_team_abbreviations:

            if team_arrests := arrests_by_team.get(team_abbr):
                nfl_team: Dict = {
                    "pos": "D/ST",
                    "players": {},
                    "total_points": 0,
                    "offenders": [],
                    "num_offenders": 0,
                    "worst_offense": None,
                    "worst_offense_points": 0
                }

                for player_arrest in team_arrests:
                    player_name = player_arrest.get("name")
                    player_pos = player_arrest.get("position")
                    player_pos_type = player_arrest.get("position_type")
                    offense_category = str.upper(player_arrest.get("crime"))

                    # Add each crime to output categories for generation of crime_categories.new.json file, which can
                    # be used to replace the existing crime_categories.json file. Each new crime categories will default
                    # to a score of 0, and must have its score manually assigned within the json file.
                    self.unique_crime_categories_for_output[offense_category] = self.crime_rankings.get(
                        offense_category, 0
                    )

                    # add raw player arrest data to raw data collection
                    self.raw_feature_data[player_name] = player_arrest

                    if offense_category in self.crime_rankings.keys():
                        offense_points = self.crime_rankings.get(offense_category)
                    else:
                        offense_points = 0
                        logger.warning(f"Crime ranking not found: \"{offense_category}\". Assigning score of 0.")

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

                    self.feature_data[player_name] = nfl_player

                    # update team DEF entry
                    if player_pos_type == "D":
                        nfl_team["players"][player_name] = self.feature_data[player_name]
                        nfl_team["total_points"] += offense_points
                        nfl_team["offenders"].append(player_name)
                        nfl_team["offenders"] = list(set(nfl_team["offenders"]))
                        nfl_team["num_offenders"] = len(nfl_team["offenders"])

                        if offense_points > nfl_team["worst_offense_points"]:
                            nfl_team["worst_offense"] = offense_category
                            nfl_team["worst_offense_points"] = offense_points

                self.feature_data[team_abbr] = nfl_team

    def _get_player_bad_boy_stats(self, player_first_name: str, player_last_name: str, player_team_abbr: str,
                                  player_pos: str, key_str: Optional[str] = None) -> Union[int, str, Dict[str, Any]]:
        """Looks up given player and returns number of "bad boy" points based on custom crime scoring.

        TODO: maybe limit for years and adjust defensive players rolling up to DEF team as it skews DEF scores high
        :param player_first_name: First name of player to look up
        :param player_last_name: Last name of player to look up
        :param player_team_abbr: Player's team (maybe limit to only crimes while on that team...or for DEF players???)
        :param player_pos: Player's position
        :param key_str: which player information to retrieve (crime: "worst_offense" or bad boy points: "total_points")
        :return: Ether integer number of bad boy points or crime recorded (depending on key_str)
        """
        player_team = str.upper(player_team_abbr) if player_team_abbr else "?"
        if player_team not in nfl_team_abbreviations:
            if player_team in nfl_team_abbreviation_conversions.keys():
                player_team = nfl_team_abbreviation_conversions[player_team]

        player_full_name = (
            f"{capwords(player_first_name) if player_first_name else ''}"
            f"{' ' if player_first_name and player_last_name else ''}"
            f"{capwords(player_last_name) if player_last_name else ''}"
        ).strip()

        # TODO: figure out how to include only ACTIVE players in team DEF roll-ups
        if player_pos == "D/ST":
            # player_full_name = player_team
            player_full_name = "TEMPORARY DISABLING OF TEAM DEFENSES IN BAD BOY POINTS"
        if player_full_name in self.feature_data:
            return self.feature_data[player_full_name][key_str] if key_str else self.feature_data[player_full_name]
        else:
            logger.debug(
                f"Player not found: {player_full_name}. Setting crime category and bad boy points to 0. Run report "
                f"with the -r flag (--refresh-web-data) to refresh all external web data and try again."
            )

            self.feature_data[player_full_name] = {
                "team": player_team,
                "pos": player_pos,
                "offenses": [],
                "total_points": 0,
                "worst_offense": None,
                "worst_offense_points": 0
            }
            return self.feature_data[player_full_name][key_str] if key_str else self.feature_data[player_full_name]

    def get_player_bad_boy_crime(self, player_first_name: str, player_last_name: str, player_team: str,
                                 player_pos: str) -> str:
        return self._get_player_bad_boy_stats(
            player_first_name, player_last_name, player_team, player_pos, "worst_offense"
        )

    def get_player_bad_boy_points(self, player_first_name: str, player_last_name: str, player_team: str,
                                  player_pos: str) -> int:
        return self._get_player_bad_boy_stats(
            player_first_name, player_last_name, player_team, player_pos, "total_points"
        )

    def get_player_bad_boy_num_offenders(self, player_first_name: str, player_last_name: str, player_team: str,
                                         player_pos: str) -> int:
        player_bad_boy_stats = self._get_player_bad_boy_stats(
            player_first_name, player_last_name, player_team, player_pos
        )
        if player_bad_boy_stats.get("pos") == "D/ST":
            return player_bad_boy_stats.get("num_offenders")
        else:
            return 0

    def generate_crime_categories_json(self):
        unique_crimes = OrderedDict(sorted(self.unique_crime_categories_for_output.items(), key=lambda k_v: k_v[0]))
        with open(self.resource_files_dir / "crime_categories.new.json", mode="w",
                  encoding="utf-8") as crimes:
            json.dump(unique_crimes, crimes, ensure_ascii=False, indent=2)
