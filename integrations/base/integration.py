from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class BaseIntegration(ABC):

    def __init__(self, integration_type: str, week: int):
        self.integration_type_str: str = integration_type.replace(" ", "_").lower()
        self.integration_type_title: str = integration_type.replace("_", " ").title()

        self.week = week

        logger.debug(f"Initializing {self.integration_type_title} integration.")

        self.client: Any = None

        logger.debug(f"Authenticating with {self.integration_type_title}...")
        self._authenticate()
        logger.debug(f"...{self.integration_type_title} authenticated.")

    def _upload_success_message(self, file_name: str, drive_link: Optional[str] = None):
        message = (
            f"\nFantasy Football Metrics Report for Week {self.week}: *{file_name}*\n"
            f"Generated {datetime.now():%Y-%b-%d %H:%M:%S}"
        )

        if drive_link:
            message += (
                f"\n\n_Google Drive Link:_\n"
                f"{drive_link}"
            )

        return message

    @abstractmethod
    def _authenticate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, file_path: Path) -> Any:
        raise NotImplementedError
