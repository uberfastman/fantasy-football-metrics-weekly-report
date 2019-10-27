import os
from configparser import ConfigParser

from ff_espn_api import League

# TODO: WORK-IN-PROGRESS

# config vars
config = ConfigParser()
config.read(os.path.join("..", "config.ini"))

espn_auth_dir = os.path.join("..", config.get("ESPN", "espn_auth_dir"))

league_id = config.get("Configuration", "league_id")
season = config.get("Configuration", "season")
league = League(int(league_id), int(season))
print(league.authentication())
