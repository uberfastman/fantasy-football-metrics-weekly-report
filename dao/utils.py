__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os
import sys

from dao import yahoo

from dao.base import League

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def league_data_class_factory(config, game_id, league_id, base_dir, data_dir, week_for_report, save_data, dev_offline):
    platform = config.get("Configuration", "platform")

    if platform == "yahoo":
        yahoo_auth_dir = os.path.join(base_dir, config.get("Yahoo", "yahoo_auth_dir"))
        yahoo_league = yahoo.LeagueData(
            config=config,
            yahoo_game_id=game_id,
            yahoo_league_id=league_id,
            yahoo_auth_dir=yahoo_auth_dir,
            data_dir=data_dir,
            week_for_report=week_for_report,
            save_data=save_data,
            dev_offline=dev_offline
        )

        # --------------------------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------
        # --------------------------------------------------------------------------------------------------------------

        league = League(config, league_id, data_dir, week_for_report, yahoo_auth_dir, save_data, dev_offline)

        league.name = yahoo_league.league_metadata.name
        league.roster_positions = yahoo_league.roster_positions
        league.bench_positions = ["BN", "IR"]
        league.current_week = yahoo_league.current_week
        league.season = yahoo_league.season
        league.num_teams = yahoo_league.league_metadata.num_teams
        league.num_playoff_slots = yahoo_league.playoff_slots
        league.num_regular_season_weeks = yahoo_league.num_regular_season_weeks

        # league.fetch_player_function = yahoo_league.yahoo_data.retrieve
        # league.fetch_player_params = {
        #     "yff_query": yahoo_league.yahoo_query,
        #     "params": {"player_key": player_key, "chosen_week": str(week_for_report)},
        #     "data_type_class": Player,
        #     "new_data_dir": os.path.join(self.data_dir, str(self.season), self.league_key, "week_" + str(week), "players")
        # }

        for pos in league.roster_positions:
            position_name = pos.position
            position_count = int(pos.count)

            count = position_count
            while count > 0:
                if position_name not in league.bench_positions:
                    league.active_positions.append(position_name)
                count -= 1

            if position_name == "W/R":
                league.flex_positions = ["WR", "RB"]
            if position_name == "W/R/T":
                league.flex_positions = ["WR", "RB", "TE"]
            if position_name == "Q/W/R/T":
                league.flex_positions = ["QB", "WR", "RB", "TE"]

            if "/" in position_name:
                position_name = "FLEX"

            league.roster_position_counts[position_name] += position_count




    else:
        logger.error(
            "Generating fantasy football reports for the \"{}\" fantasy football platform is not currently supported."
            "Please change your settings in config.ini and try again.".format(platform))
        sys.exit()
