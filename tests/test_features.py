__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from ffmwr.features.bad_boy import BadBoyFeature  # noqa: E402
from ffmwr.features.beef import BeefFeature  # noqa: E402
from ffmwr.features.high_roller import HighRollerFeature  # noqa: E402
from ffmwr.utilities.logger import get_logger  # noqa: E402

logger = get_logger(__file__)

test_data_dir = Path(root_dir) / "output" / "data" / "tests" / "feature_data"
if not test_data_dir.exists():
    test_data_dir.mkdir(parents=True, exist_ok=True)

player_first_name = "Rashee"
player_last_name = "Rice"
player_full_name = f"{player_first_name} {player_last_name}"
player_team_abbr = "KC"
player_position = "WR"

season = 2023
week_for_report = 1


def test_bad_boy_init():
    bad_boy_feature = BadBoyFeature(
        week_for_report=week_for_report,
        root_dir=root_dir,
        data_dir=test_data_dir,
        refresh=True,
        save_data=True,
        offline=False,
    )
    bad_boy_feature.generate_crime_categories_json()

    player_bad_boy_crime = bad_boy_feature.get_player_bad_boy_crime(
        player_first_name, player_last_name, player_team_abbr, player_position
    )
    logger.info(f"\nPlayer Bad Boy crime for {player_first_name} {player_last_name}: {player_bad_boy_crime}")
    player_bad_boy_points = bad_boy_feature.get_player_bad_boy_points(
        player_first_name, player_last_name, player_team_abbr, player_position
    )
    logger.info(f"\nPlayer Bad Boy points for {player_first_name} {player_last_name}: {player_bad_boy_points}")

    assert bad_boy_feature.feature_data is not None


def test_beef_init():
    beef_feature = BeefFeature(
        week_for_report=week_for_report, data_dir=test_data_dir, refresh=True, save_data=True, offline=False
    )
    beef_feature.generate_player_info_json()

    logger.info(
        f"\nPlayer weight for {player_full_name}: "
        f"{beef_feature.get_player_weight(player_first_name, player_last_name, player_team_abbr, player_position)}"
    )
    logger.info(
        f"\nPlayer TABBU for {player_full_name}: "
        f"{beef_feature.get_player_tabbu(player_first_name, player_last_name, player_team_abbr, player_position)}"
    )

    assert beef_feature.feature_data is not None


def test_high_roller_init():
    high_roller_feature = HighRollerFeature(
        season=season,
        week_for_report=week_for_report,
        data_dir=test_data_dir,
        refresh=True,
        save_data=True,
        offline=False,
    )

    player_worst_violation = high_roller_feature.get_player_worst_violation(
        player_first_name, player_last_name, player_team_abbr, player_position
    )
    logger.info(f"\nPlayer worst violation for {player_full_name}: {player_worst_violation}")
    player_worst_violation_fine = high_roller_feature.get_player_worst_violation_fine(
        player_first_name, player_last_name, player_team_abbr, player_position
    )
    logger.info(f"\nPlayer worst violation fine for {player_full_name}: {player_worst_violation_fine}")
    player_fines_total = high_roller_feature.get_player_fines_total(
        player_first_name, player_last_name, player_team_abbr, player_position
    )
    logger.info(f"\nPlayer fines total for {player_full_name}: {player_fines_total}")

    assert high_roller_feature.feature_data is not None


if __name__ == "__main__":
    logger.info("Testing features...")

    # test bad boy data retrieval
    test_bad_boy_init()

    # test player weight (beef) data retrieval
    test_beef_init()

    # test player NFL fines (high roller) data retrieval
    test_high_roller_init()
