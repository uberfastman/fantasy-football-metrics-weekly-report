import re
from typing import Any, Dict, List, Optional, Union

import requests
from pyobjson import PythonObjectJson
from requests import Response

from ffmwr.utilities.constants import (player_name_punctuation,
                                       player_name_suffixes)
from ffmwr.utilities.logger import get_logger

logger = get_logger(__name__, propagate=False)


class FFMWRPythonObjectJson(PythonObjectJson):
    """Custom class extension of PythonObjectJson that excludes all sensitive attributes from saved data."""

    def __init__(self):
        super().__init__(
            excluded_attributes=[
                "yahoo_consumer_key",
                "yahoo_consumer_secret",
                "yahoo_access_token_json",
                "espn_username",
                "espn_password",
                "espn_cookie_swid",
                "espn_cookie_espn_s2",
                "cbs_username",
                "cbs_password",
                "cbs_auth_token",
            ]
        )


def normalize_dependency_package_name(package_name: str) -> str:
    # normalize Python package name (see https://packaging.python.org/en/latest/specifications/name-normalization/)
    return re.sub(r"[-_.]+", "-", package_name).lower()


def format_platform_display(platform: str) -> str:
    return platform.capitalize() if len(platform) > 4 else platform.upper()


def truncate_cell_for_display(
    cell_text: str,
    max_chars: int,
    halve_max_chars: bool = False,
    sesqui_max_chars: bool = False,
) -> str:
    if halve_max_chars and sesqui_max_chars:
        logger.warning(
            f"Max characters cannot be both halved and multiplied. Defaulting to configure max characters: {max_chars}"
        )
    elif halve_max_chars:
        max_chars //= 2
    elif sesqui_max_chars:
        max_chars += max_chars // 2

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


def generate_normalized_player_key(
    player_full_name: str, player_nfl_team_abbr: str
) -> str:
    """Remove all punctuation and name suffixes from player names, combine whitespace, covert them to snake case, and
    append player NFL team abbreviation.
    """
    regex_all_whitespace = re.compile(r"\s+")
    normalized_player_name: str = regex_all_whitespace.sub(
        " ", player_full_name
    ).strip()

    if any(punc in player_full_name for punc in player_name_punctuation) or any(
        suffix in player_full_name for suffix in player_name_suffixes
    ):
        for punc in player_name_punctuation:
            normalized_player_name = normalized_player_name.replace(punc, "")

        for suffix in player_name_suffixes:
            normalized_player_name = normalized_player_name.removesuffix(suffix)

    return f"{regex_all_whitespace.sub('_', normalized_player_name.strip().lower())}-{player_nfl_team_abbr.lower()}"


def get_data_from_web(
    urls: List[str],
    method: str,
    headers: Dict[str, str],
    return_responses_as_body_strings: bool = False,
    request_bodies: Optional[Dict[str, str]] = None,
) -> Dict[str, Union[Response, str]]:
    """Download the HTML contents of a list of URLs using requests.

    Args:
        urls (list[str]): list of URLs for each target web page for retrieval
        method (str): the request method (GET, POST, etc.)
        headers (dict[str, str]): dictionary of request headers
        return_responses_as_body_strings (bool, optional): whether to return responses or response body strings
        request_bodies (dict[str, str], optional): dictionary of URL keys and request bodies

    Returns:
        dict[str, Response | str]: dictionary of URL keys for the respective retrieved web page responses or
            response body strings
    """
    results: Dict[str, Union[Response, str]] = {}

    for url in urls:
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                body = request_bodies.get(url) if request_bodies else None
                response = requests.post(url, headers=headers, data=body)
            else:
                response = requests.request(
                    method.upper(),
                    url,
                    headers=headers,
                    data=request_bodies.get(url) if request_bodies else None,
                )

            response.raise_for_status()  # Raise an exception for bad status codes

            results[url] = (
                response.text if return_responses_as_body_strings else response
            )

        except Exception as e:
            logger.warning(f"Error {e} from URL: {url}")
            continue

    return results
