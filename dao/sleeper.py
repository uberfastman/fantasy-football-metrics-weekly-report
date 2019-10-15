__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import datetime
import json
import logging
import os
import re
import sys
from collections import defaultdict
from copy import deepcopy

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from sleeper_wrapper import League

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseManager, BasePlayer, BaseStat

logger = logging.getLogger(__name__)

# Suppress Fleaflicker API debug logging
logger.setLevel(level=logging.INFO)


class LeagueData(object):

    def __init__(self,
                 week_for_report,
                 league_id,
                 season,
                 config,
                 base_dir,
                 data_dir,
                 week_validation_function,
                 save_data=True,
                 dev_offline=False):

        self.league_id = league_id
        self.season = season
        self.config = config
        self.data_dir = data_dir
        self.save_data = save_data
        self.dev_offline = dev_offline

        self.league = League(self.league_id)

    def query(self, url, file_dir, filename):

        file_path = os.path.join(file_dir, filename)

        if not self.dev_offline:
            response = requests.get(url)

            try:
                response.raise_for_status()
            except HTTPError as e:
                # log error and terminate query if status code is not 200
                logger.error("REQUEST FAILED WITH STATUS CODE: {} - {}".format(response.status_code, e))
                sys.exit()

            response_json = response.json()
            logger.debug("Response (JSON): {}".format(response_json))
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    response_json = json.load(data_in)
            except FileNotFoundError:
                logger.error(
                    "FILE {} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!".format(
                        file_path))
                sys.exit()

        if self.save_data:
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                json.dump(response_json, data_out, ensure_ascii=False, indent=2)

        return response_json

    def map_data_to_base(self, base_league_class):
        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague



