__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from datetime import datetime
from pathlib import Path
from typing import Dict, Union, Type

import requests
from bs4 import BeautifulSoup

from features.base.feature import BaseFeature
from utilities.constants import nfl_team_abbreviations, nfl_team_abbreviation_conversions
from utilities.logger import get_logger
from utilities.utils import normalize_player_name

logger = get_logger(__name__, propagate=False)


class HighRollerFeature(BaseFeature):

    def __init__(self, data_dir: Path, season: int, refresh: bool = False, save_data: bool = False,
                 offline: bool = False):
        """Initialize class, load data from Spotrac.com.
        """
        self.season: int = season

        # position type reference
        self.position_types: Dict[str, str] = {
            "CB": "D", "DE": "D", "DT": "D", "FS": "D", "ILB": "D", "LB": "D", "OLB": "D", "S": "D", "SS": "D",
            # defense
            "FB": "O", "QB": "O", "RB": "O", "TE": "O", "WR": "O",  # offense
            "K": "S", "P": "S",  # special teams
            "C": "L", "G": "L", "LS": "L", "LT": "L", "RT": "L",  # offensive line
            "D/ST": "D"  # team defense
        }

        super().__init__(
            "high_roller",
            f"https://www.spotrac.com/nfl/fines/_/year/{self.season}",
            data_dir,
            refresh,
            save_data,
            offline
        )

    def _get_feature_data(self):

        for team in nfl_team_abbreviations:
            self.feature_data[team] = {
                "position": "D/ST",
                "players": {},
                "violators": [],
                "num_violators": 0,
                "fines_count": 0,
                "fines_total": 0.0,
                "worst_violation": None,
                "worst_violation_fine": 0.0
            }

        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/13.0.2 Safari/605.1.15"
        )
        headers = {
            "user-agent": user_agent
        }

        response = requests.get(self.feature_web_base_url, headers=headers)

        html_soup = BeautifulSoup(response.text, "html.parser")
        logger.debug(f"Response URL: {response.url}")
        logger.debug(f"Response (HTML): {html_soup}")

        fined_players = html_soup.find("tbody").findAll("tr", {"class": ""})

        for player in fined_players:

            player_name = player.find("a", {"class": "link"}).getText().strip()
            player_team = player.find("img", {"class": "me-2"}).getText().strip()
            if not player_team:
                # attempt to retrieve team from parent element if img element is missing closing tag
                player_team = player.find("td", {"class": "text-left details"}).getText().strip()

            # TODO: move this cleaning to base feature.py
            # replace player team abbreviation with universal team abbreviation as needed
            if player_team not in nfl_team_abbreviations:
                player_team = nfl_team_abbreviation_conversions[player_team]
            player_position = player.find("td", {"class": "text-left details-sm"}).getText().strip()

            player_fine_info = {
                "violation": player.find("span", {"class": "text-muted"}).getText()[2:].strip(),
                "violation_fine": int("".join([
                    ch for ch in player.find("td", {"class": "text-center details highlight"}).getText().strip()
                    if ch.isdigit()
                ])),
                "violation_season": self.season,
                "violation_date": datetime.strptime(
                    player.find("td", {"class": "text-right details"}).getText().strip(), "%m/%d/%y"
                ).isoformat()
            }

            if player_name not in self.feature_data.keys():
                self.feature_data[player_name] = {
                    "normalized_name": normalize_player_name(player_name),
                    "team": player_team,
                    "position": player_position,
                    "position_type": self.position_types[player_position],
                    "fines": [player_fine_info],
                    "fines_count": 1,
                    "fines_total": player_fine_info["violation_fine"],
                    "worst_violation": player_fine_info["violation"],
                    "worst_violation_fine": player_fine_info["violation_fine"]
                }
            else:
                self.feature_data[player_name]["fines"].append(player_fine_info)
                self.feature_data[player_name]["fines"].sort(
                    key=lambda x: (-x["violation_fine"], -datetime.fromisoformat(x["violation_date"]).timestamp())
                )
                self.feature_data[player_name]["fines_count"] += 1
                self.feature_data[player_name]["fines_total"] += player_fine_info["violation_fine"]

                worst_violation = self.feature_data[player_name]["fines"][0]
                self.feature_data[player_name]["worst_violation"] = worst_violation["violation"]
                self.feature_data[player_name]["worst_violation_fine"] = worst_violation["violation_fine"]

        for player_name in self.feature_data.keys():

            if self.feature_data[player_name]["position"] != "D/ST":
                player_team = self.feature_data[player_name]["team"]

                if player_name not in self.feature_data[player_team]["players"]:
                    player = self.feature_data[player_name]
                    self.feature_data[player_team]["players"][player_name] = player
                    self.feature_data[player_team]["violators"].append(player_name)
                    self.feature_data[player_team]["violators"] = list(set(self.feature_data[player_team]["violators"]))
                    self.feature_data[player_team]["num_violators"] = len(self.feature_data[player_team]["violators"])
                    self.feature_data[player_team]["fines_count"] += player["fines_count"]
                    self.feature_data[player_team]["fines_total"] += player["fines_total"]
                    if player["worst_violation_fine"] >= self.feature_data[player_team]["worst_violation_fine"]:
                        self.feature_data[player_team]["worst_violation"] = player["worst_violation"]
                        self.feature_data[player_team]["worst_violation_fine"] = player["worst_violation_fine"]

    def _get_player_high_roller_stats(self, player_first_name: str, player_last_name: str, player_team_abbr: str,
                                      player_pos: str, key_str: str, key_type: Type) -> Union[str, float, int]:

        player_full_name = (
            f"{player_first_name.title() if player_first_name else ''}"
            f"{' ' if player_first_name and player_last_name else ''}"
            f"{player_last_name.title() if player_last_name else ''}"
        ).strip()

        if player_full_name in self.feature_data.keys():
            return self.feature_data[player_full_name].get(key_str, key_type())
        else:
            logger.debug(
                f"No {self.feature_type_title} data found for player \"{player_full_name}\". "
                f"Run report with the -r flag (--refresh-web-data) to refresh all external web data and try again."
            )

            player = {
                "position": player_pos,
                "fines_count": 0,
                "fines_total": 0.0,
                "worst_violation": None,
                "worst_violation_fine": 0.0
            }
            if player_pos == "D/ST":
                player.update({
                    "players": {},
                    "violators": [],
                    "num_violators": 0,
                })
            else:
                player.update({
                    "normalized_name": normalize_player_name(player_full_name),
                    "team": player_team_abbr,
                    "fines": [],
                })

            self.feature_data[player_full_name] = player

            return self.feature_data[player_full_name][key_str]

    def get_player_worst_violation(self, player_first_name: str, player_last_name: str, player_team: str,
                                   player_pos: str) -> str:
        return self._get_player_high_roller_stats(
            player_first_name, player_last_name, player_team, player_pos, "worst_violation", str
        )

    def get_player_worst_violation_fine(self, player_first_name: str, player_last_name: str, player_team: str,
                                        player_pos: str) -> float:
        return self._get_player_high_roller_stats(
            player_first_name, player_last_name, player_team, player_pos, "worst_violation_fine", float
        )

    def get_player_fines_total(self, player_first_name: str, player_last_name: str, player_team: str,
                               player_pos: str) -> float:
        return self._get_player_high_roller_stats(
            player_first_name, player_last_name, player_team, player_pos, "fines_total", float
        )

    def get_player_num_violators(self, player_first_name: str, player_last_name: str, player_team: str,
                                 player_pos: str) -> int:
        return self._get_player_high_roller_stats(
            player_first_name, player_last_name, player_team, player_pos, "num_violators", int
        )
