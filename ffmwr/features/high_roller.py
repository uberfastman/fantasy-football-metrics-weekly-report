__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from datetime import datetime
from pathlib import Path
from typing import Dict

import requests
from bs4 import BeautifulSoup

from ffmwr.features.base.feature import BaseFeature
from ffmwr.utilities.constants import nfl_team_abbreviation_conversions, nfl_team_abbreviations
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file
from ffmwr.utilities.utils import generate_normalized_player_key

logger = get_logger(__name__, propagate=False)


class HighRollerFeature(BaseFeature):
    def __init__(
        self,
        season: int,
        week_for_report: int,
        data_dir: Path,
        refresh: bool = False,
        save_data: bool = False,
        offline: bool = False,
    ):
        """Initialize class, load data from Spotrac.com."""
        self.season: int = season

        defense = {
            "CB": "D",
            "DE": "D",
            "DT": "D",
            "FS": "D",
            "ILB": "D",
            "LB": "D",
            "OLB": "D",
            "S": "D",
            "SS": "D",
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
            "C": "L",
            "G": "L",
            "LS": "L",
            "LT": "L",
            "RT": "L",
        }
        team_defense = {
            "D/ST": "D",
        }
        # position type reference
        self.position_types: Dict[str, str] = {
            **defense,
            **offense,
            **special_teams,
            **offensive_line,
            **team_defense,
        }

        super().__init__(
            "high_roller",
            f"https://www.spotrac.com/nfl/fines/_/year/{self.season}",
            week_for_report,
            data_dir,
            True,  # TODO: decide if team D/ST roll-ups should be included in high roller total
            refresh,
            save_data,
            offline,
        )

    def _get_feature_data(self):
        for team in nfl_team_abbreviations:
            self.feature_data[team] = {
                "position": "D/ST",
                "players": {},
                "violators": [],
                "violators_count": 0,
                "fines_count": 0,
                "fines_total": 0.0,
                "worst_violation": None,
                "worst_violation_fine": 0.0,
            }

        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/13.0.2 Safari/605.1.15"
        )
        headers = {"user-agent": user_agent}

        response = requests.get(self.feature_web_base_url, headers=headers)

        html_soup = BeautifulSoup(response.text, "html.parser")
        logger.debug(f"Response URL: {response.url}")
        logger.debug(f"Response (HTML):\n{html_soup.prettify()}")

        fined_players = html_soup.find("tbody").find_all("tr", {"class": ""})

        for player in fined_players:
            player_full_name = player.find("a", {"class": "link"}).getText().strip()
            player_team_abbr = player.find("img", {"class": "me-2"}).getText().strip()
            player_position = player.find("td", {"class": "text-left details-sm"}).getText().strip()
            player_position_type = self.position_types[player_position]

            if not player_team_abbr:
                # attempt to retrieve team abbreviation from parent element if img element is missing closing tag
                player_team_abbr = player.find("td", {"class": "text-left details"}).getText().strip()

            # replace player team abbreviation with universal team abbreviation as needed
            if player_team_abbr not in nfl_team_abbreviations:
                if player_team_abbr in nfl_team_abbreviation_conversions.keys():
                    player_team_abbr = nfl_team_abbreviation_conversions[player_team_abbr]

            try:
                player_violation = player.find("span", {"class": "text-muted"}).getText()[2:].strip()
            except AttributeError as e:
                logger.debug(f"Unable to parse violation for {player_full_name} with error: {repr(e)}")
                player_violation = None

            player_fine_info = {
                "violation": player_violation,
                "violation_fine": int(
                    "".join(
                        [
                            ch
                            for ch in player.find("td", {"class": "text-center details highlight"}).getText().strip()
                            if ch.isdigit()
                        ]
                    )
                ),
                "violation_season": self.season,
                "violation_date": datetime.strptime(
                    player.find("td", {"class": "text-right details"}).getText().strip(), "%m/%d/%y"
                ).isoformat(),
            }

            normalized_player_key = generate_normalized_player_key(player_full_name, player_team_abbr)

            # add raw player data json to raw_player_data for reference
            self.raw_feature_data[normalized_player_key] = player.prettify()

            if normalized_player_key not in self.feature_data.keys():
                self.feature_data[normalized_player_key] = {
                    **self._get_feature_data_template(
                        player_full_name, player_team_abbr, player_position, player_position_type
                    ),
                    "fines": [player_fine_info],
                    "fines_count": 1,
                    "fines_total": player_fine_info["violation_fine"],
                    "worst_violation": player_fine_info["violation"],
                    "worst_violation_fine": player_fine_info["violation_fine"],
                }
            else:
                self.feature_data[normalized_player_key]["fines"].append(player_fine_info)
                self.feature_data[normalized_player_key]["fines"].sort(
                    key=lambda x: (-x["violation_fine"], -datetime.fromisoformat(x["violation_date"]).timestamp())
                )
                self.feature_data[normalized_player_key]["fines_count"] += 1
                self.feature_data[normalized_player_key]["fines_total"] += player_fine_info["violation_fine"]

                worst_violation = self.feature_data[normalized_player_key]["fines"][0]
                self.feature_data[normalized_player_key]["worst_violation"] = worst_violation["violation"]
                self.feature_data[normalized_player_key]["worst_violation_fine"] = worst_violation["violation_fine"]

        for player_key in self.feature_data.keys():
            if self.feature_data[player_key]["position"] != "D/ST":
                player_team_abbr = self.feature_data[player_key]["team_abbr"]

                if player_key not in self.feature_data[player_team_abbr]["players"]:
                    player = self.feature_data[player_key]
                    self.feature_data[player_team_abbr]["players"][player_key] = player
                    self.feature_data[player_team_abbr]["violators"].append(player["full_name"])
                    self.feature_data[player_team_abbr]["violators"] = list(
                        set(self.feature_data[player_team_abbr]["violators"])
                    )
                    self.feature_data[player_team_abbr]["violators_count"] = len(
                        self.feature_data[player_team_abbr]["violators"]
                    )
                    self.feature_data[player_team_abbr]["fines_count"] += player["fines_count"]
                    self.feature_data[player_team_abbr]["fines_total"] += player["fines_total"]
                    if player["worst_violation_fine"] >= self.feature_data[player_team_abbr]["worst_violation_fine"]:
                        self.feature_data[player_team_abbr]["worst_violation"] = player["worst_violation"]
                        self.feature_data[player_team_abbr]["worst_violation_fine"] = player["worst_violation_fine"]

    def get_player_worst_violation(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> str:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "worst_violation", str
        )

    def get_player_worst_violation_fine(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> float:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "worst_violation_fine", float
        )

    def get_player_fines_total(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> float:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "fines_total", float
        )

    def get_player_num_violators(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "violators_count", int
        )


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    local_high_roller_feature = HighRollerFeature(
        local_settings.season,
        1,
        local_root_directory / local_settings.data_dir_path / "tests" / "feature_data",
        refresh=True,
        save_data=True,
        offline=False,
    )
