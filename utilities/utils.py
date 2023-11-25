__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)


def format_platform_display(platform: str) -> str:
    return platform.capitalize() if len(platform) > 4 else platform.upper()


def truncate_cell_for_display(cell_text: str, halve_max_chars: bool = False) -> str:
    max_chars: int = settings.report_settings.max_data_chars

    if halve_max_chars:
        max_chars //= 2

    return f"{cell_text[:max_chars].strip()}..." if len(cell_text) > max_chars else cell_text
