__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from features.bad_boy import BadBoyFeature  # noqa: E402
from features.beef import BeefFeature  # noqa: E402
from features.high_roller import HighRollerStats  # noqa: E402

from utilities.logger import get_logger  # noqa: E402

logger = get_logger(__file__)

test_data_dir = Path(root_dir) / "tests"
if not Path(test_data_dir).exists():
    os.makedirs(test_data_dir)

player_first_name = "Marquise"
player_last_name = "Brown"
player_full_name = f"{player_first_name} {player_last_name}"
player_team_abbr = "ARI"
player_position = "WR"

season = 2024


def test_bad_boy_init():
    bad_boy_stats = BadBoyFeature(
        root_dir=root_dir,
        data_dir=test_data_dir,
        save_data=True,
        offline=False,
        refresh=True
    )
    bad_boy_stats.generate_crime_categories_json()

    logger.info(
        f"\nPlayer Bad Boy crime for {player_first_name} {player_last_name}: "
        f"{bad_boy_stats.get_player_bad_boy_crime(player_first_name, player_last_name, player_team_abbr, player_position)}"
    )
    logger.info(
        f"\nPlayer Bad Boy points for {player_first_name} {player_last_name}: "
        f"{bad_boy_stats.get_player_bad_boy_points(player_first_name, player_last_name, player_team_abbr, player_position)}"
    )

    assert bad_boy_stats.bad_boy_data is not None


def test_beef_init():
    beef_stats = BeefFeature(
        data_dir=test_data_dir,
        save_data=True,
        offline=False,
        refresh=True
    )
    beef_stats.generate_player_info_json()

    logger.info(
        f"\nPlayer weight for {player_full_name}: "
        f"{beef_stats.get_player_weight(player_first_name, player_last_name, player_team_abbr)}"
    )
    logger.info(
        f"\nPlayer TABBU for {player_full_name}: "
        f"{beef_stats.get_player_tabbu(player_first_name, player_last_name, player_team_abbr)}"
    )

    assert beef_stats.beef_data is not None


def test_high_roller_init():
    high_roller_stats = HighRollerStats(
        season=season,
        data_dir=test_data_dir,
        save_data=True,
        offline=False,
        refresh=True
    )

    logger.info(f"\n{high_roller_stats}")

    assert high_roller_stats.high_roller_data is not None


if __name__ == "__main__":
    logger.info("Testing features...")

    # test bad boy data retrieval
    test_bad_boy_init()

    # test player weight (beef) data retrieval
    test_beef_init()

    # test player NFL fines (high roller) data retrieval
    test_high_roller_init()
