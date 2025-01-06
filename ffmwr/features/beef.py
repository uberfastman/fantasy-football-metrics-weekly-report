__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict

import requests

from ffmwr.features.base.feature import BaseFeature
from ffmwr.utilities.constants import nfl_team_abbreviation_conversions, nfl_team_abbreviations
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file
from ffmwr.utilities.utils import generate_normalized_player_key

logger = get_logger(__name__, propagate=False)


class BeefFeature(BaseFeature):
    def __init__(
        self,
        week_for_report: int,
        data_dir: Path,
        refresh: bool = False,
        save_data: bool = False,
        offline: bool = False,
    ):
        """Initialize class, load data from Sleeper API, and combine defensive player data into team total"""
        self.tabbu_value: float = 500.0

        defense = {
            "CB": "D",
            "DB": "D",
            "DE": "D",
            "DL": "D",
            "DT": "D",
            "FS": "D",
            "ILB": "D",
            "LB": "D",
            "NT": "D",
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
            "K/P": "S",
            "P": "S",
        }
        offensive_line = {
            "C": "L",
            "G": "L",
            "LS": "L",
            "OG": "L",
            "OL": "L",
            "OT": "L",
            "T": "L",
        }
        team_defense = {
            "DEF": "D",
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
            "beef",
            "https://api.sleeper.app/v1/players/nfl",
            week_for_report,
            data_dir,
            False,
            refresh,
            save_data,
            offline,
        )

    def _get_feature_data(self):
        logger.debug("Retrieving beef feature data from the web.")

        nfl_player_data = requests.get(self.feature_web_base_url).json()
        for player_sleeper_key, player_data_json in nfl_player_data.items():
            player_full_name = player_data_json.get("full_name", "")
            player_team_abbr = player_data_json.get("team")
            player_position = player_data_json.get("position")
            player_position_type = self.position_types.get(player_position)

            if player_team_abbr not in nfl_team_abbreviations:
                if player_team_abbr in nfl_team_abbreviation_conversions.keys():
                    player_team_abbr = nfl_team_abbreviation_conversions[player_team_abbr]
                else:
                    player_team_abbr = "?"

            if player_position == "DEF":
                normalized_player_key = player_position
            else:
                normalized_player_key = generate_normalized_player_key(player_full_name, player_team_abbr)

            # add raw player data json to raw_player_data for reference
            self.raw_feature_data[normalized_player_key] = player_data_json

            if player_position != "DEF":
                player_weight = int(player_data_json.get("weight")) if player_data_json.get("weight") else 0.0
                player_tabbu = player_weight / float(self.tabbu_value)
                player_beef_dict = {
                    **self._get_feature_data_template(
                        player_full_name, player_team_abbr, player_position, player_position_type
                    ),
                    "weight": player_weight,
                    "tabbu": player_tabbu,
                }

                if normalized_player_key not in self.feature_data.keys():
                    self.feature_data[normalized_player_key] = player_beef_dict

                position_types = player_data_json.get("fantasy_positions")
                if player_team_abbr != "?" and position_types and ("DL" in position_types or "DB" in position_types):
                    if player_team_abbr not in self.feature_data.keys():
                        self.feature_data[player_team_abbr] = {
                            "position": "D/ST",
                            "players": {normalized_player_key: player_beef_dict},
                            "weight": player_weight,
                            "tabbu": player_tabbu,
                        }
                    else:
                        self.feature_data[player_team_abbr]["players"][normalized_player_key] = player_beef_dict
                        self.feature_data[player_team_abbr]["weight"] += player_weight
                        self.feature_data[player_team_abbr]["tabbu"] += player_tabbu

    def get_player_weight(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> int:
        return self._get_player_feature_stats(
            player_first_name, player_last_name, player_team_abbr, player_position, "weight", int
        )

    def get_player_tabbu(
        self, player_first_name: str, player_last_name: str, player_team_abbr: str, player_position: str
    ) -> float:
        return round(
            self._get_player_feature_stats(
                player_first_name, player_last_name, player_team_abbr, player_position, "tabbu", float
            ),
            3,
        )

    def generate_player_info_json(self):
        ordered_player_data = OrderedDict(sorted(self.raw_feature_data.items(), key=lambda k_v: k_v[0]))
        with open(self.data_dir / f"{self.feature_type_str}_raw.json", mode="w", encoding="utf-8") as player_data:
            # noinspection PyTypeChecker
            json.dump(ordered_player_data, player_data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    local_beef_feature = BeefFeature(
        1,
        local_root_directory / local_settings.data_dir_path / "tests" / "feature_data",
        refresh=True,
        save_data=True,
        offline=False,
    )
