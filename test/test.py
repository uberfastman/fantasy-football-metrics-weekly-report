import unittest
from configparser import ConfigParser
import os

from calculate.beef_stats import BeefStats

# config vars
config = ConfigParser()
config.read(os.path.join("..", "config.ini"))


class BeefStatsTestCase(unittest.TestCase):
    def test_beef_init(self):
        beef_stats = BeefStats(
            data_dir=os.path.join("..", config.get("Fantasy_Football_Report_Settings", "data_dir"), "test"),
            save_data=True,
            dev_offline=False)
        self.assertIsNotNone(beef_stats.beef_data)


if __name__ == '__main__':
    unittest.main()
