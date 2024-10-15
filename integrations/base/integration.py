from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class BaseIntegration(ABC):

    def __init__(self, integration_type: str):
        self.integration_type_str: str = integration_type.replace(" ", "_").lower()
        self.integration_type_title: str = integration_type.replace("_", " ").title()

        logger.debug(f"Initializing {self.integration_type_title} integration.")

        self.client: Any = None

        logger.debug(f"Authenticating with {self.integration_type_title}...")
        self._authenticate()
        logger.debug(f"...{self.integration_type_title} authenticated.")

    @abstractmethod
    def _authenticate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, file_path: Path) -> Any:
        raise NotImplementedError
