__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import json
import os

from ff_espn_api import League

from dao.base import BaseLeague


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

        espn_auth_file = os.path.join(base_dir, config.get("ESPN", "espn_auth_dir"), "private.json")
        with open(espn_auth_file, "r") as auth:
            espn_auth_json = json.load(auth)

        self.league = League(
            league_id=self.league_id,
            year=self.season,
            espn_s2=espn_auth_json.get("espn_s2"),
            swid=espn_auth_json.get("swid")
        )  # type: League

        self.season = self.league.year
        self.current_week = self.league.current_week
        self.num_playoff_slots = int(self.league.settings.playoff_team_count)
        self.num_regular_season_weeks = int(self.league.settings.reg_season_count)
        # self.roster_positions = self.league_info.settings.roster_positions

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week)

    def map_data_to_base(self, base_league_class):
        league = base_league_class(self.week_for_report, self.league_id, self.config, self.data_dir, self.save_data,
                                   self.dev_offline)  # type: BaseLeague
