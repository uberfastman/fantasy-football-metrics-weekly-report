__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

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

        start = datetime.now()

        data_retrieved_from_web = False
        if not self.offline:
            if not self.feature_data_file_path.is_file() or self.refresh:
                logger.info(f"Retrieving {self.feature_type_title} data from {self.feature_web_base_url}...")
                # fetch feature data from the web
                self._get_feature_data()
                data_retrieved_from_web = True

                if self.save_data:
                    self._save_feature_data()
            else:
                # load saved feature data (must have previously run application with -s flag)
                self._load_feature_data()
        else:
            # load saved feature data (must have previously run application with -s flag)
            self._load_feature_data()

        if len(self.feature_data) == 0:
            logger.warning(
                f"...{'retrieved' if data_retrieved_from_web else 'loaded'} 0 {self.feature_type_title} data records. "
                f"Please check your internet connection or the availability of {self.feature_web_base_url} and try "
                f"generating a new report."
            )
        else:
            logger.info(
                f"...{'retrieved' if data_retrieved_from_web else 'loaded'} {len(self.feature_data)} "
                f"{self.feature_type_title} data records in {datetime.now() - start}."
            )

    def __str__(self):
        return json.dumps(self.feature_data, indent=2, ensure_ascii=False)

    def __repr__(self):
        return json.dumps(self.feature_data, indent=2, ensure_ascii=False)

    def _load_feature_data(self) -> None:
        logger.info(f"Loading saved {self.feature_type_title} data...")

        if self.feature_data_file_path.is_file():
            with open(self.feature_data_file_path, "r", encoding="utf-8") as feature_data_in:
                self.feature_data = dict(json.load(feature_data_in))
        else:
            raise FileNotFoundError(
                f"FILE {self.feature_data_file_path} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY "
                f"SAVED DATA!"
            )

    def _save_feature_data(self) -> None:
        logger.debug(f"Saving {self.feature_type_title} data...")

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

    @abstractmethod
    def _get_feature_data(self) -> None:
        raise NotImplementedError
