__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import requests
from bs4 import BeautifulSoup

from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class HighRollerStats(object):

    def __init__(self, season: int, data_dir: Path, save_data: bool = False, offline: bool = False,
                 refresh: bool = False):
        """ Initialize class, load data from Spotrac.com.
        """
        logger.debug("Initializing high roller stats.")

        self.data_dir: Path = Path(data_dir)

        self.save_data: bool = save_data
        self.offline: bool = offline
        self.refresh: bool = refresh

        # position type reference
        self.position_types: Dict[str, str] = {
            "CB": "D", "DE": "D", "DT": "D", "FS": "D", "ILB": "D", "LB": "D", "OLB": "D", "S": "D", "SS": "D",
            # defense
            "FB": "O", "QB": "O", "RB": "O", "TE": "O", "WR": "O",  # offense
            "K": "S", "P": "S",  # special teams
            "C": "L", "G": "L", "LS": "L", "LT": "L", "RT": "L"  # offensive line
        }

        self.high_roller_data: Dict[str, Dict[str, Union[str, List[Dict]]]] = {}
        self.high_roller_data_file_path: Path = self.data_dir / "high_roller_data.json"

        if not self.refresh:
            self.open_high_roller_data()

        # fetch fines of players from the web if not running in offline mode or refresh=True
        if self.refresh or not self.offline:
            if not self.high_roller_data:
                logger.debug("Retrieving high roller data from the web.")

                self.get_player_fines_data(season)

                self.save_high_roller_data()

        # if offline mode, load pre-fetched fines data (only works if you've previously run application with -s flag)
        else:
            if not self.high_roller_data:
                raise FileNotFoundError(
                    f"FILE {str(self.high_roller_data_file_path)} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING "
                    f"PREVIOUSLY SAVED DATA!"
                )

        if len(self.high_roller_data) == 0:
            logger.warning(
                f"NO high roller data was loaded, please check your internet connection or the availability of "
                f"\"https://www.spotrac.com/nfl/fines/_/year/{season}\" and try generating a new report.")
        else:
            logger.info(f"{len(self.high_roller_data)} players with fines were loaded")

    def open_high_roller_data(self):
        logger.debug("Loading saved high roller data.")
        if self.high_roller_data_file_path.exists():
            with open(self.high_roller_data_file_path, "r", encoding="utf-8") as high_roller_in:
                self.high_roller_data = dict(json.load(high_roller_in))

    def save_high_roller_data(self):
        if self.save_data:
            logger.debug("Saving high roller data.")
            with open(self.high_roller_data_file_path, "w", encoding="utf-8") as high_roller_out:
                json.dump(self.high_roller_data, high_roller_out, ensure_ascii=False, indent=2)

    def get_player_fines_data(self, season: int) -> None:

        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/13.0.2 Safari/605.1.15"
        )
        headers = {
            "user-agent": user_agent
        }

        response = requests.get(
            f"https://www.spotrac.com/nfl/fines/_/year/{season}",
            headers=headers
        )

        html_soup = BeautifulSoup(response.text, "html.parser")
        logger.debug(f"Response URL: {response.url}")
        logger.debug(f"Response (HTML): {html_soup}")

        fined_players = html_soup.find("tbody").findAll("tr", {"class": ""})

        positions = set()
        for player in fined_players:

            player_name = player.find("a", {"class": "link"}).getText().strip()

            player_fine_info = {
                "player_name": player_name,
                "player_pos": player.find("td", {"class": "text-left details-sm"}).getText().strip(),
                "player_team": player.find("img", {"class": "me-2"}).getText().strip(),
                "player_violation": player.find("span", {"class": "text-muted"}).getText()[2:].strip(),
                "player_fine": int("".join([
                    ch for ch in player.find("td", {"class": "text-center details highlight"}).getText().strip()
                    if ch.isdigit()
                ])),
                "player_fine_date": datetime.strptime(
                    player.find("td", {"class": "text-right details"}).getText().strip(), "%m/%d/%y"
                ).isoformat()
            }

            positions.add(player_fine_info["player_pos"])

            if player_name not in self.high_roller_data.keys():
                self.high_roller_data[player_name] = {
                    "total_fines": player_fine_info["player_fine"],
                    "fines": [player_fine_info]
                }
            else:
                self.high_roller_data[player_name]["total_fines"] += player_fine_info["player_fine"]
                self.high_roller_data[player_name]["fines"].append(player_fine_info)

    def __str__(self):
        return json.dumps(self.high_roller_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.high_roller_data, indent=2, ensure_ascii=False)
