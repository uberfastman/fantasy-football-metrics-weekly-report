__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import re

from utilities.constants import player_name_punctuation, player_name_suffixes
from utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


def format_platform_display(platform: str) -> str:
    return platform.capitalize() if len(platform) > 4 else platform.upper()


def truncate_cell_for_display(cell_text: str, max_chars: int, halve_max_chars: bool = False,
                              sesqui_max_chars: bool = False) -> str:

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


def normalize_player_name(player_full_name: str) -> str:
    """Remove all punctuation and name suffixes from player names, combine whitespace, and covert them to title case.
    """
    regex_all_whitespace = re.compile(r"\s+")
    normalized_player_name: str = regex_all_whitespace.sub(" ", player_full_name).strip()

    if (any(punc in player_full_name for punc in player_name_punctuation)
            or any(suffix in player_full_name for suffix in player_name_suffixes)):

        for punc in player_name_punctuation:
            normalized_player_name = normalized_player_name.replace(punc, "")

        for suffix in player_name_suffixes:
            normalized_player_name = normalized_player_name.removesuffix(suffix)

    return normalized_player_name.strip().title()
