__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import json
import logging
import os
import subprocess
import sys
from configparser import ConfigParser

import requests
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

config = ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"))


def query(url, file_dir, filename):

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    cbs_auth_dir = os.path.join(base_dir, config.get("CBS", "cbs_auth_dir"))

    if not os.path.exists(cbs_auth_dir):
        os.makedirs(cbs_auth_dir)

    token_file = os.path.join(cbs_auth_dir, "token.json")

    if not os.path.exists(token_file):
        with open(os.path.join(cbs_auth_dir, "private.json"), "r") as auth:
            cbs_auth_json = json.load(auth)

        get_cbs_api_key_ruby_script_path = os.path.join(base_dir, "resources", "get_cbs_api_key.rb")

        # login_url = "https://www.cbssports.com/login"
        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, " +
        #                   "like Gecko) Version/13.0 Safari/605.1.15",
        #     "Content-Type": "application/json"
        # }
        # body = {
        #     "userid": cbs_auth_json.get("user_id"),
        #     "password": cbs_auth_json.get("password"),
        #     "xurl": "https://{}.football.cbssports.com/".format(cbs_auth_json.get("league_id"))
        # }
        #
        # session = HTMLSession()
        #
        # r = session.post(
        #     login_url,
        #     json=json.dumps(body),
        #     headers=headers
        # )
        #
        # r.html.render(timeout=60)
        #
        # from pprint import pprint
        # print("result:")
        # pprint(r.html.html, indent=2)

        cbs_access_token = subprocess.check_output([
            "ruby", "{}".format(get_cbs_api_key_ruby_script_path),
            cbs_auth_json.get("league_id"),
            cbs_auth_json.get("user_id"),
            cbs_auth_json.get("password")
        ]).decode("utf-8")

        with open(token_file, "w") as token:
            token.write(json.dumps(
                {
                    "access_token": cbs_access_token
                },
                indent=2
            ))
    else:
        with open(token_file) as token:
            cbs_access_token = json.load(token).get("access_token")

    file_path = os.path.join(file_dir, filename)

    response = requests.get(url + "&response_format=json&access_token={}".format(cbs_access_token))

    try:
        response.raise_for_status()
    except HTTPError as e:
        # log error and terminate query if status code is not 200
        logger.error("REQUEST FAILED WITH STATUS CODE: {} - {}".format(response.status_code, e))
        sys.exit("...run aborted.")

    response_json = response.json()
    logger.debug("Response (JSON): {}".format(response_json))

    return response_json


if __name__ == '__main__':

    # league details/info
    query_response = query(
        "http://api.cbssports.com/fantasy/league/details?version=3.0",
        "",
        ""
    )

    # # league stats
    # query_response = query(
    #     "http://api.cbssports.com/fantasy/league/stats?version=3.1",
    #     "",
    #     ""
    # )
    #
    # # league rules
    # query_response = query(
    #     "http://api.cbssports.com/fantasy/league/rules?version=3.0",
    #     "",
    #     ""
    # )
    #
    # # NFL pro teams
    # query_response = query(
    #     "http://api.cbssports.com/fantasy/pro-teams?version=3.0",
    #     "",
    #     ""
    # )
    #
    # # league managers
    # query_response = query(
    #     "http://api.cbssports.com/fantasy/league/owners?version=3.0",
    #     "",
    #     ""
    # )

    print(json.dumps(query_response, indent=2))
    print()
    print("~" * 100)
    print("~" * 100)
    print()
