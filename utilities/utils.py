__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import re
from typing import List, Dict, Optional, Any, Union

from tornado.gen import coroutine, WaitIterator
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse
from tornado.ioloop import IOLoop

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


def normalize_player_name(player_full_name: str, as_key_format: bool = False) -> str:
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

    normalized_player_name = normalized_player_name.strip()

    if as_key_format:
        return regex_all_whitespace.sub("_", normalized_player_name.lower())
    else:
        return normalized_player_name.title()


def get_data_from_web(urls: List[str], method: str, headers: Dict[str, str],
                      return_responses_as_body_strings: bool = False,
                      request_bodies: Optional[Dict[str, str]] = None) -> Dict[str, Union[HTTPResponse, str]]:
    """Asynchronously download the HTML contents of a list of URLs.

    Args:
        urls (list[str]): list of URLs for each target web page for retrieval
        method (str): the reqeust method (GET, POST, etc.)
        headers (dict[str, str]): dictionary of request headers
        return_responses_as_body_strings (bool, optional): whether to return responses or response body strings
        request_bodies (dict[str, str], optional): dictionary of URL keys and request bodies

    Returns:
        dict[str, HTTPResponse | str]: dictionary of URL keys for the respective retrieved web page HTTP responses or
            response body strings
    """

    # noinspection PyTypeChecker
    @coroutine
    def get_web_page() -> List[Any]:

        # AsyncHTTPClient.configure(None, defaults=dict(user_agent=user_agent))
        async_http_client = AsyncHTTPClient()
        wait_iterator = WaitIterator(
            *[async_http_client.fetch(
                HTTPRequest(
                    url,
                    method=method.upper(),
                    headers=headers,
                    body=request_bodies.get(url) if request_bodies else None
                )
            ) for url in urls]
        )

        results: Dict[str, Union[HTTPResponse, str]] = {}
        while not wait_iterator.done():
            try:
                result: HTTPResponse = yield wait_iterator.next()
            except Exception as e:
                logger.warning(f"Error {e} from {wait_iterator.current_future}")
            else:
                logger.debug(
                    f"Result {result} received from {wait_iterator.current_future} at {wait_iterator.current_index}"
                )
                results[result.effective_url] = (
                    bytes.decode(result.body, "utf-8") if return_responses_as_body_strings else result
                )

        return results

    io_loop = IOLoop.current()
    return io_loop.run_sync(get_web_page)
