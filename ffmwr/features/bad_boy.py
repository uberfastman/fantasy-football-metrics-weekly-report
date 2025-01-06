__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import itertools
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict

import requests
from bs4 import BeautifulSoup

from ffmwr.features.base.feature import BaseFeature
from ffmwr.utilities.constants import nfl_team_abbreviations
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file
from ffmwr.utilities.utils import generate_normalized_player_key

logger = get_logger(__name__, propagate=False)


class BadBoyFeature(BaseFeature):
    def __init__(
        self,
        week_for_report: int,
        root_dir: Path,
        data_dir: Path,
        refresh: bool = False,
        save_data: bool = False,
        offline: bool = False,
    ):
        """Initialize class, load data from USA Today NFL Arrest DB. Combine defensive player data"""

        defense = {
            "C": "D",
            "CB": "D",
            "DB": "D",
            "DE": "D",
            "DE/DT": "D",
            "DT": "D",
            "LB": "D",
            "S": "D",
            "Safety": "D",
        }
        offense = {
            "FB": "O",
            "QB": "O",
            "RB": "O",
            "TE": "O",
            "WR": "O",
        }
        special_teams = {
            "K": "S",
            "P": "S",
        }
        offensive_line = {
            "OG": "L",
            "OL": "L",
            "OT": "L",
        }
        coaching_staff = {
            "OC": "C",
        }
        # position type reference
        self.position_types: Dict[str, str] = {
            **defense,
            **offense,
            **special_teams,
            **offensive_line,
            **coaching_staff,
        }

        self.resource_files_dir = root_dir / "resources" / "files"

        # Load the scoring based on crime categories
        with open(self.resource_files_dir / "crime_categories.json", mode="r", encoding="utf-8") as crimes:
            self.crime_rankings = json.load(crimes)
            logger.debug("Crime categories loaded.")

        # for outputting all unique crime categories found in the USA Today NFL arrests data
        self.unique_crime_categories_for_output = {}

        super().__init__(
            "bad_boy",
            "https://www.usatoday.com/sports/nfl/arrests",
            week_for_report,
            data_dir,
            True,  # TODO: figure out how to include only ACTIVE players in team D/St roll-ups
            refresh,
            save_data,
            offline,
        )

    # noinspection DuplicatedCode
    def _get_feature_data(self) -> None:
        logger.debug("Retrieving bad boy feature data from the web.")

        res = requests.get(self.feature_web_base_url)
        soup = BeautifulSoup(res.text, "html.parser")
        cdata = re.search("var sitedata = (.*);", soup.find(string=re.compile("CDATA"))).group(1)
        ajax_nonce = json.loads(cdata)["ajax_nonce"]

        usa_today_nfl_arrest_url = "https://databases.usatoday.com/wp-admin/admin-ajax.php"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

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
                f'&searches={{"Team":"{team}"}}'
            )

            res_json = requests.post(usa_today_nfl_arrest_url, data=body, headers=headers).json()

            arrests_data = res_json["data"]["Result"]

            for arrest in arrests_data:
                arrests.append(
                    {
                        "full_name": f"{arrest['First_name']} {arrest['Last_name']}",
                        "team_abbr": (
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
                        "outcome": arrest["Outcome"],
                    }
                )

            total_results = res_json["data"]["totalResults"]

            # the USA Today NFL arrests database only retrieves 20 entries per request
            if total_results > 20:
                # add extra page to include last page of results if they exist
                num_pages = (total_results // 20) + (1 if total_results % 20 > 0 else 0)

                for page in range(2, num_pages + 1):
                    page_num += 1
                    body = (
                        f"action=cspFetchTable"
                        f"&security={ajax_nonce}"
                        f"&pageID=10"
                        f"&sortBy=Date"
                        f"&sortOrder=desc"
                        f"&page={page_num}"
                        f'&searches={{"Team":"{team}"}}'
                    )

                    r = requests.post(usa_today_nfl_arrest_url, data=body, headers=headers)
                    resp_json = r.json()

                    arrests_data = resp_json["data"]["Result"]

                    for arrest in arrests_data:
                        arrests.append(
                            {
                                "full_name": f"{arrest['First_name']} {arrest['Last_name']}",
                                "team_abbr": (
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
                                "outcome": arrest["Outcome"],
                            }
                        )

        arrests_by_team = {
            key: list(group)
            for key, group in itertools.groupby(sorted(arrests, key=lambda x: x["team_abbr"]), lambda x: x["team_abbr"])
        }

        for team_abbr in nfl_team_abbreviations:
            if team_arrests := arrests_by_team.get(team_abbr):
                nfl_team: Dict = {
                    "position": "D/ST",
                    "players": {},
                    "offenders": [],
                    "offenders_count": 0,
                    "worst_offense": None,
                    "worst_offense_points": 0,
                    "bad_boy_points_total": 0,
                }

                for player_arrest in team_arrests:
                    player_full_name = player_arrest.get("full_name")
                    player_position = player_arrest.get("position")
                    player_position_type = player_arrest.get("position_type")
                    offense_category = str.upper(player_arrest.get("crime"))

                    normalized_player_key = generate_normalized_player_key(player_full_name, team_abbr)

                    # Add each crime to output categories for generation of crime_categories.new.json file, which can
                    # be used to replace the existing crime_categories.json file. Each new crime categories will default
                    # to a score of 0, and must have its score manually assigned within the json file.
                    self.unique_crime_categories_for_output[offense_category] = self.crime_rankings.get(
                        offense_category, 0
                    )

                    # add raw player data json to raw_player_data for reference
                    self.raw_feature_data[normalized_player_key] = player_arrest

                    if offense_category in self.crime_rankings.keys():
                        offense_points = self.crime_rankings.get(offense_category)
                    else:
                        offense_points = 0
                        logger.warning(f'Crime ranking not found: "{offense_category}". Assigning score of 0.')

                    nfl_player = {
                        **self._get_feature_data_template(
                            player_full_name, team_abbr, player_position, self.position_types[player_position]
                        ),
                        "offenses": [],
                        "worst_offense": None,
                        "worst_offense_points": 0,
                        "bad_boy_points_total": 0,
                    }

                    # update player entry
                    nfl_player["offenses"].append({offense_category: offense_points})
                    nfl_player["bad_boy_points_total"] += offense_points

                    if offense_points > nfl_player["worst_offense_points"]:
                        nfl_player["worst_offense"] = offense_category
                        nfl_player["worst_offense_points"] = offense_points

                    self.feature_data[normalized_player_key] = nfl_player

                    # update team DEF entry
                    if player_position_type == "D":
                        nfl_team["players"][normalized_player_key] = self.feature_data[normalized_player_key]
                        nfl_team["bad_boy_points_total"] += offense_points
                        nfl_team["offenders"].append(player_full_name)
                        nfl_team["offenders"] = list(set(nfl_team["offenders"]))
                        nfl_team["offenders_count"] = len(nfl_team["offenders"])

                        if offense_points > nfl_team["worst_offense_points"]:
                            nfl_team["worst_offense"] = offense_category
                            nfl_team["worst_offense_points"] = offense_points

                self.feature_data[team_abbr] = nfl_team

    def get_player_bad_boy_crime(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> str:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "worst_offense", str
        )

    def get_player_bad_boy_points(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "bad_boy_points_total", int
        )

    def get_player_bad_boy_num_offenders(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "offenders_count", int
        )

    def generate_crime_categories_json(self):
        unique_crimes = OrderedDict(sorted(self.unique_crime_categories_for_output.items(), key=lambda k_v: k_v[0]))
        with open(self.resource_files_dir / "crime_categories.new.json", mode="w", encoding="utf-8") as crimes:
            # noinspection PyTypeChecker
            json.dump(unique_crimes, crimes, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    local_bad_boy_feature = BadBoyFeature(
        1,
        local_root_directory,
        local_root_directory / local_settings.data_dir_path / "tests" / "feature_data",
        refresh=True,
        save_data=True,
        offline=False,
    )
