__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Union

import requests
from requests.exceptions import HTTPError

from ffmwr.models.base.model import BaseLeague
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings
from ffmwr.utilities.utils import format_platform_display

logger = get_logger(__name__, propagate=False)

# Suppress platform API debug logging
logger.setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class BasePlatform(ABC):
    def __init__(
        self,
        settings: AppSettings,
        platform: str,
        base_url: Union[str, None],
        root_dir: Path,
        data_dir: Path,
        league_id: str,
        season: int,
        start_week: int,
        week_for_report: int,
        get_current_nfl_week_function: Callable,
        week_validation_function: Callable,
        save_data: bool = True,
        offline: bool = False,
    ):
        self.settings = settings

        self.platform: str = platform.lower()
        self.platform_display: str = format_platform_display(platform)
        self.base_url: str = base_url
        self.root_dir: Path = root_dir
        self.data_dir: Path = data_dir

        self.league_id = league_id

        self.season = season
        # TODO: figure out how to get start week from all platforms
        self.start_week = start_week or 1
        # retrieve current NFL week
        self.current_week: int = get_current_nfl_week_function(self.settings, offline)
        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.settings, week_for_report, self.current_week, self.season)

        self.save_data: bool = save_data
        self.offline: bool = offline

        logger.debug(f"Initializing {self.platform_display} league.")
        self.league: BaseLeague = BaseLeague(
            self.settings,
            self.platform,
            self.league_id,
            self.season,
            self.week_for_report,
            self.root_dir,
            self.data_dir,
            self.save_data,
            self.offline,
        )

        # create full directory path if any directories in it do not already exist
        if not Path(self.league.data_dir).exists():
            os.makedirs(self.league.data_dir)

        self.position_mapping: Dict[str, Dict[str, Any]] = self._get_platform_position_mapping()
        self.league.offensive_positions = [
            pos_attributes.get("base")
            for pos_attributes in self.position_mapping.values()
            if pos_attributes.get("type") == "offensive"
        ]
        self.league.defensive_positions = [
            pos_attributes.get("base")
            for pos_attributes in self.position_mapping.values()
            if pos_attributes.get("type") == "defensive"
        ]
        self.league.bench_positions = [
            pos_attributes.get("base")
            for pos_attributes in self.position_mapping.values()
            if pos_attributes.get("type") == "bench"
        ]

    def query(self, url: str, headers: Dict[str, str] = None):
        logger.debug(f"Retrieving {self.platform_display} web data from endpoint: {url}")
        response = requests.get(url, headers=headers)

        try:
            response.raise_for_status()
        except HTTPError as e:
            # log error and terminate query if status code is not 200
            logger.error(f"REQUEST FAILED WITH STATUS CODE: {response.status_code} - {e}")
            sys.exit(1)

        response_json = response.json()
        logger.debug(f"Response (JSON): {response_json}")

        return response_json

    def _get_platform_position_mapping(self) -> Dict[str, Dict]:
        with open(Path(__file__).parent / "position_mapping.json", "r") as pos_mapping_file:
            pos_mapping_json = json.load(pos_mapping_file)

        base_positions = pos_mapping_json.get("base")
        platform_positions = pos_mapping_json.get(self.platform)

        mapped_platform_positions = {
            platform_pos: {
                **pos_attributes,
                **(
                    base_positions.get(pos_attributes.get("base"))
                    if "base" in pos_attributes
                    else {"base": platform_pos}
                ),
            }
            for platform_pos, pos_attributes in platform_positions.items()
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
                    unmapped_idp_positions[pos] = {"base": pos, "type": "defensive", "is_flex": False}

        return unmapped_base_positions | unmapped_idp_positions | mapped_platform_positions

    def get_mapped_position(self, platform_position: str) -> str:
        return self.position_mapping.get(platform_position).get("base")

    @abstractmethod
    def _authenticate(self, *args, **kwargs) -> None:
        raise NotImplementedError()

    @abstractmethod
    def map_data_to_base(self) -> None:
        raise NotImplementedError()

    def fetch(self) -> None:
        begin = datetime.now()
        logger.info(
            f"Retrieving fantasy football data from "
            f"{self.platform_display} {'API' if not self.league.offline else 'saved data'}..."
        )

        if self.league.offline:
            if not self.league.league_data_file_path.is_file():
                raise FileNotFoundError(
                    f"FILE {self.league.league_data_file_path} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING "
                    f"PREVIOUSLY SAVED DATA!"
                )
            else:
                logger.debug(f"Loading saved {self.platform_display} data from {self.league.league_data_file_path}")

                # load league feature data (must have previously run application with -s flag)
                self.league.load_from_json_file(self.league.league_data_file_path)

                # update values that could be different in the saved data from those provided at runtime
                self.league.save_data = self.save_data
                self.league.offline = self.offline
        else:
            # authenticate with platform as needed
            self._authenticate()
            # fetch league data from the web
            self.map_data_to_base()

        if self.league.save_data:
            logger.debug(f"Saving {self.platform_display} data to {self.league.league_data_file_path}")
            self.league.save_to_json_file(self.league.league_data_file_path)

        delta = datetime.now() - begin
        logger.info(
            f"...retrieved all fantasy football data from "
            f"{self.platform_display + (' API' if not self.league.offline else ' saved data')} in {delta}"
        )
