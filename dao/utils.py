__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os
import sys

from dao.yahoo import LeagueData

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def league_data_class_factory(config, game_id, league_id, base_dir, data_dir, week_for_report, save_data, dev_offline):
    platform = config.get("Configuration", "platform")

    if platform == "yahoo":
        yahoo_auth_dir = os.path.join(base_dir, config.get("Yahoo", "yahoo_auth_dir"))
        return LeagueData(
            config=config,
            yahoo_game_id=game_id,
            yahoo_league_id=league_id,
            yahoo_auth_dir=yahoo_auth_dir,
            data_dir=data_dir,
            week_for_report=week_for_report,
            save_data=save_data,
            dev_offline=dev_offline
        )

    else:
        logger.error(
            "Generating fantasy football reports for the \"{}\" fantasy football platform is not currently supported."
            "Please change your settings in config.ini and try again.".format(platform))
        sys.exit()
