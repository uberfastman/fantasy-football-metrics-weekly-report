import json
import logging
import os
import sys
import urllib
import urllib.parse as urlparse
from configparser import ConfigParser
from urllib.parse import parse_qs

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

local_config = ConfigParser()
local_config.read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"))


if __name__ == '__main__':

    local_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    nfl_auth_dir = os.path.join(local_base_dir, local_config.get("NFL", "nfl_auth_dir"))
    nfl_access_token_file = os.path.join(nfl_auth_dir, "token.json")

    if not os.path.exists(nfl_access_token_file):
        with open(os.path.join(nfl_auth_dir, "private.json"), "r") as auth:
            nfl_auth_json = json.load(auth)

        with open(os.path.join(nfl_auth_dir, "nfl_ff_client.json"), "r") as nfl_ff_client:
            nfl_ff_client_json = json.load(nfl_ff_client)

        login_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, " +
                          "like Gecko) Version/13.0 Safari/605.1.15",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        gigya_url = "https://fantasy.nfl.com/auth/gigyalogin"
        response = requests.get(
            gigya_url,
            headers=login_headers
        )

        soup = BeautifulSoup(response.content, "html.parser")

        gigya_apikey_url = ""
        for script_tag in soup.findAll("script"):
            if script_tag.get("src") is not None:
                if "apikey" in script_tag.get("src"):
                    gigya_apikey_url = script_tag.get("src")

        parsed = urlparse.urlparse(gigya_apikey_url)
        gigya_apikey = parse_qs(parsed.query)["apikey"][0]

        # noinspection PyUnresolvedReferences
        body = urllib.parse.urlencode({
            "format": "json",
            "apikey": gigya_apikey,
            "loginID": nfl_auth_json.get("username"),
            "password": nfl_auth_json.get("password")
        })

        gigya_login_url = "https://accounts.us1.gigya.com/accounts.login"
        response = requests.post(
            gigya_login_url,
            headers=login_headers,
            data=body
        )

        try:
            response.raise_for_status()
        except HTTPError as e:
            # log error and terminate query if status code is not 200
            logger.error("REQUEST FAILED WITH STATUS CODE: {} - {}".format(response.status_code, e))
            sys.exit("...run aborted.")

        response_json = response.json()
        # print(json.dumps(response.json(), indent=2))

        print(response_json.get("UID"))
        print(response_json.get("UIDSignature"))
        print(response_json.get("signatureTimestamp"))

        print("-" * 100)

        # noinspection PyUnresolvedReferences
        body = urllib.parse.urlencode({
            "username": nfl_auth_json.get("username"),
            "client_id": nfl_ff_client_json.get("nfl_ff_client_id"),
            "client_secret": nfl_ff_client_json.get("nfl_ff_client_secret"),
            "grant_type": "gigya_signature",
            "gigya_UID": response_json.get("UID"),
            "gigya_signature": response_json.get("UIDSignature"),
            "gigya_signature_timestamp": response_json.get("signatureTimestamp")
        })

        oauth_url = "https://api.nfl.com/v1/oauth/token"
        response = requests.post(
            oauth_url,
            headers=login_headers,
            data=body
        )

        response_json = response.json()
        # print(json.dumps(response_json, indent=2))

        print()
        access_token = response_json.get("access_token")
        print(access_token)
        refresh_token = response_json.get("refresh_token")
        print(refresh_token)

        print("/" * 100)

        data_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, " +
                          "like Gecko) Version/13.0 Safari/605.1.15",
            "Content-Type": "application/json",
            "authorization": "Bearer {0}".format(access_token)
        }

        base = "https://api.nfl.com/v1/teams?"

        joiner = "&"

        args = 'fs={nickName,standings{week{seasonType,week},overallWins,overallLosses,overallTies,overallRank}}'

        query = 's={"$query":{"abbr":"SEA","season":2020,"standings":{"$query":{"week.seasonType":"REG"}}}}"'

        response = requests.get(
            "{0}{2}{1}{3}".format(base, joiner, args, query),
            headers=data_headers
        )

        print(response.json())



