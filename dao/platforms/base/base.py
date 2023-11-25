__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Dict, Callable, Any

import requests
from requests.exceptions import HTTPError

from dao.base import BaseLeague
from utilities.logger import get_logger
from utilities.utils import format_platform_display

logger = get_logger(__name__, propagate=False)

# Suppress platform API debug logging
logger.setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class BaseLeagueData(ABC):

    def __init__(self,
                 platform: str,
                 base_url: Union[str, None],
                 base_dir: Path,
                 data_dir: Path,
                 league_id: str,
                 season: int,
                 start_week: int,
                 week_for_report: int,
                 get_current_nfl_week_function: Callable,
                 week_validation_function: Callable,
                 save_data: bool = True,
                 offline: bool = False):

        self.platform: str = platform.lower()
        self.platform_display: str = format_platform_display(platform)
        self.base_url: str = base_url
        self.base_dir: Path = base_dir

        # TODO: figure out how to get start week from all platforms
        self.start_week = start_week or 1

        # retrieve current NFL week
        self.current_week: int = get_current_nfl_week_function(offline)

        # validate user selection of week for which to generate report
        week_for_report = week_validation_function(week_for_report, self.current_week, season)

        logger.debug(f"Initializing {self.platform_display} league.")
        self.league: BaseLeague = BaseLeague(data_dir, league_id, season, week_for_report, save_data, offline)

        # create full directory path if any directories in it do not already exist
        if not Path(self.league.data_dir).exists():
            os.makedirs(self.league.data_dir)

        self.position_mapping: Dict[str, Dict[str, Any]] = self._get_platform_position_mapping()
        self.league.offensive_positions = [
            pos_attributes.get("base") for pos_attributes in self.position_mapping.values() if
            pos_attributes.get("type") == "offensive"
        ]
        self.league.defensive_positions = [
            pos_attributes.get("base") for pos_attributes in self.position_mapping.values() if
            pos_attributes.get("type") == "defensive"
        ]
        self.league.bench_positions = [
            pos_attributes.get("base") for pos_attributes in self.position_mapping.values() if
            pos_attributes.get("type") == "bench"
        ]

    def query(self, url: str, save_file: Path = None, headers: Dict[str, str] = None):

        if not self.league.offline:
            logger.debug(f"Retrieving {self.platform_display} data from endpoint: {url}")
            response = requests.get(url, headers=headers)

            try:
                response.raise_for_status()
            except HTTPError as e:
                # log error and terminate query if status code is not 200
                logger.error(f"REQUEST FAILED WITH STATUS CODE: {response.status_code} - {e}")
                sys.exit(1)

            response_json = response.json()
            logger.debug(f"Response (JSON): {response_json}")
        else:
            try:
                logger.debug(f"Loading saved {self.platform_display} data for endpoint: {url}")
                with open(save_file, "r", encoding="utf-8") as data_in:
                    response_json = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    f"FILE {save_file} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!"
                )
                sys.exit(1)

        if self.league.save_data:
            logger.debug(f"Saving {self.platform_display} data retrieved from endpoint: {url}")

            if save_file:
                if not Path(save_file.parent).exists():
                    os.makedirs(save_file.parent)

                with open(save_file, "w", encoding="utf-8") as data_out:
                    json.dump(response_json, data_out, ensure_ascii=False, indent=2)
            else:
                logger.debug(f"No save file provided. Response will not be saved.")

        return response_json

    def _get_platform_position_mapping(self) -> Dict[str, Dict]:

        with open(Path(__file__).parent / "position_mapping.json", "r") as pos_mapping_file:
            pos_mapping_json = json.load(pos_mapping_file)

        base_positions = pos_mapping_json.get("base")
        platform_positions = pos_mapping_json.get(self.platform)

        mapped_platform_positions = {
            platform_pos: {
                **pos_attributes,
                **(base_positions.get(pos_attributes.get("base")) if "base" in pos_attributes else {
                    "base": platform_pos})
            } for platform_pos, pos_attributes in platform_positions.items()
        }

        unmapped_base_positions = {
            base_pos: {"base": base_pos, **pos_attributes}
            for base_pos, pos_attributes in base_positions.items()
            if not pos_attributes.get("is_flex")
        }

        mapped_base_and_platform_positions = unmapped_base_positions | mapped_platform_positions

        unmapped_idp_positions = {}
        for pos_attributes in mapped_base_and_platform_positions.values():
            if pos_attributes.get("type") == "defensive" and pos_attributes.get("is_flex"):
                for pos in pos_attributes.get("positions"):
                    unmapped_idp_positions[pos] = {
                        "base": pos,
                        "type": "defensive",
                        "is_flex": False
                    }

        return unmapped_base_positions | unmapped_idp_positions | mapped_platform_positions

    def get_mapped_position(self, platform_position: str) -> str:
        return self.position_mapping.get(platform_position).get("base")

    @abstractmethod
    def map_data_to_base(self) -> BaseLeague:
        raise NotImplementedError()
