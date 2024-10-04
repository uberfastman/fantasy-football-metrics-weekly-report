__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)


def format_platform_display(platform: str) -> str:
    return platform.capitalize() if len(platform) > 4 else platform.upper()


def truncate_cell_for_display(cell_text: str, halve_max_chars: bool = False, sesqui_max_chars: bool = False) -> str:
    max_chars: int = settings.report_settings.max_data_chars

    if halve_max_chars and sesqui_max_chars:
        logger.warning(
            f"Max characters cannot be both halved and multiplied. Defaulting to configure max characters: {max_chars}"
        )
    elif halve_max_chars:
        max_chars //= 2
    elif sesqui_max_chars:
        max_chars += (max_chars // 2)

    if len(cell_text) > max_chars:
        # preserve footnote character on strings that need to be truncated
        footnote_char = None
        if cell_text.endswith("†") or cell_text.endswith("‡"):
            footnote_char = cell_text[-1]
            cell_text = cell_text[:-1]
            max_chars -= 1

        return f"{cell_text[:max_chars].strip()}...{footnote_char if footnote_char else ''}"

    else:
        return cell_text
