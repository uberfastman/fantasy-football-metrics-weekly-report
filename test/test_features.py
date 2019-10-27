__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import os
import sys

module_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(module_dir)

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats

test_data_dir = os.path.join(module_dir, "test")
if not os.path.exists(test_data_dir):
    os.makedirs(test_data_dir)


def test_bad_boy_init():
    bad_boy_stats = BadBoyStats(
        data_dir=test_data_dir,
        save_data=True,
        dev_offline=False,
        refresh=True
    )
    bad_boy_stats.generate_crime_categories_json()
    assert bad_boy_stats.bad_boy_data is not None


def test_beef_init():
    beef_stats = BeefStats(
        data_dir=test_data_dir,
        save_data=True,
        dev_offline=False,
        refresh=True
    )
    beef_stats.generate_player_info_json()
    assert beef_stats.beef_data is not None
