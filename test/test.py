__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import os
import unittest
from configparser import ConfigParser

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats

# config vars
config = ConfigParser()
config.read(os.path.join("..", "config.ini"))

test_data_dir = os.path.join("..", config.get("Configuration", "data_dir"), "test")
if not os.path.exists(test_data_dir):
    os.makedirs(test_data_dir)


class ReportMetricsTestCase(unittest.TestCase):

    def test_bad_boy_init(self):
        bad_boy_stats = BadBoyStats(
            data_dir=test_data_dir,
            save_data=True,
            dev_offline=False,
            refresh=True
        )
        bad_boy_stats.generate_crime_categories_json()
        self.assertIsNotNone(bad_boy_stats.bad_boy_data)

    def test_beef_init(self):
        beef_stats = BeefStats(
            data_dir=test_data_dir,
            save_data=True,
            dev_offline=False,
            refresh=True
        )
        beef_stats.generate_player_info_json()
        self.assertIsNotNone(beef_stats.beef_data)


if __name__ == '__main__':
    unittest.main()
