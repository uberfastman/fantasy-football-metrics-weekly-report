__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from utilities.logger import get_logger
from utilities.utils import FFMWRPythonObjectJson

logger = get_logger(__name__, propagate=False)


class BaseFeature(ABC, FFMWRPythonObjectJson):

    def __init__(self, feature_type: str, feature_web_base_url: str, week_for_report: int, data_dir: Path,
                 refresh: bool = False, save_data: bool = False, offline: bool = False):
        """Base Feature class for retrieving data from the web, saving, and loading it.
        """
        super().__init__()

        self.feature_type_str: str = feature_type.replace(" ", "_").lower()
        self.feature_type_title: str = feature_type.replace("_", " ").title()

        logger.debug(f"Initializing {self.feature_type_title} feature.")

        self.feature_web_base_url = feature_web_base_url

        self.data_dir: Path = data_dir / f"week_{week_for_report}" / "feature_data"
        self.feature_data_file_path: Path = self.data_dir / f"{self.feature_type_str}.json"

        self.refresh: bool = refresh
        self.save_data: bool = save_data
        self.offline: bool = offline

        self.raw_feature_data: Dict[str, Any] = {}
        self.feature_data: Dict[str, Any] = {}

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
                # load saved feature data (must have previously run application with -j flag)
                self._load_feature_data()
        else:
            # load saved feature data (must have previously run application with -j flag)
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

        try:
            self.load_from_json_file(self.feature_data_file_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"FILE {self.feature_data_file_path} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY "
                f"SAVED DATA!"
            ) from e

    def _save_feature_data(self) -> None:
        logger.debug(f"Saving {self.feature_type_title} data...")

        if self.save_data:
            self.save_to_json_file(self.feature_data_file_path)

    @abstractmethod
    def _get_feature_data(self) -> None:
        raise NotImplementedError
