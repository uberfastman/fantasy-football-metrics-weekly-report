__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any

from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class BaseFeature(ABC):

    def __init__(self, feature_type: str, feature_web_base_url: str, data_dir: Path, refresh: bool = False,
                 save_data: bool = False, offline: bool = False):
        """Base Feature class for retrieving data from the web, saving, and loading it.
        """
        self.feature_type_str: str = feature_type.replace(" ", "_").lower()
        self.feature_type_title: str = feature_type.replace("_", " ").title()

        logger.debug(f"Initializing {self.feature_type_title} feature.")

        self.feature_web_base_url = feature_web_base_url

        self.data_dir: Path = data_dir

        self.refresh: bool = refresh
        self.save_data: bool = save_data
        self.offline: bool = offline

        self.raw_feature_data: Dict[str, Any] = {}
        self.feature_data: Dict[str, Any] = {}

        self.raw_feature_data_file_path: Path = self.data_dir / f"{self.feature_type_str}_raw_data.json"
        self.feature_data_file_path: Path = self.data_dir / f"{self.feature_type_str}_data.json"

        self.player_name_punctuation: List[str] = [".", "'"]
        self.player_name_suffixes: List[str] = ["Jr", "Sr", "V", "IV", "III", "II", "I"]  # ordered for str.removesuffix

        # fetch feature data from the web if not running in offline mode or if refresh=True
        if not self.offline and self.refresh:
            if not self.feature_data:
                logger.debug(f"Retrieving {self.feature_type_title} data from the web.")

                self._get_feature_data()

                if self.save_data:
                    self._save_feature_data()
        # if offline=True or refresh=False load saved feature data (must have previously run application with -s flag)
        else:
            self._load_feature_data()

        if len(self.feature_data) == 0:
            logger.warning(
                f"No {self.feature_type_title} data records were loaded, please check your internet connection or the "
                f"availability of {self.feature_web_base_url} and try generating a new report."
            )
        else:
            logger.info(f"{len(self.feature_data)} feature data records loaded")

    def __str__(self):
        return json.dumps(self.feature_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.feature_data, indent=2, ensure_ascii=False)

    def _load_feature_data(self) -> None:
        logger.debug(f"Loading saved {self.feature_type_title} data...")

        if self.feature_data_file_path.is_file():
            with open(self.feature_data_file_path, "r", encoding="utf-8") as feature_data_in:
                self.feature_data = dict(json.load(feature_data_in))
        else:
            raise FileNotFoundError(
                f"FILE {self.feature_data_file_path} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY "
                f"SAVED DATA!"
            )

    def _save_feature_data(self) -> None:
        logger.debug(f"Saving {self.feature_type_title} data and raw {self.feature_type_title} data.")

        # create output data directory if it does not exist
        if not self.data_dir.is_dir():
            os.makedirs(self.data_dir, exist_ok=True)

        # save feature data locally
        if self.feature_data:
            with open(self.feature_data_file_path, "w", encoding="utf-8") as feature_data_out:
                json.dump(self.feature_data, feature_data_out, ensure_ascii=False, indent=2)

        # save raw feature data locally
        if self.raw_feature_data:
            with open(self.raw_feature_data_file_path, "w", encoding="utf-8") as feature_raw_data_out:
                json.dump(self.raw_feature_data, feature_raw_data_out, ensure_ascii=False, indent=2)

    def _normalize_player_name(self, player_name: str) -> str:
        """Remove all punctuation and name suffixes from player names and covert them to title case.
        """
        normalized_player_name: str = player_name.strip()
        if (any(punc in player_name for punc in self.player_name_punctuation)
                or any(suffix in player_name for suffix in self.player_name_suffixes)):

            for punc in self.player_name_punctuation:
                normalized_player_name = normalized_player_name.replace(punc, "")

            for suffix in self.player_name_suffixes:
                normalized_player_name = normalized_player_name.removesuffix(suffix)

        return normalized_player_name.strip().title()

    @abstractmethod
    def _get_feature_data(self) -> None:
        raise NotImplementedError
