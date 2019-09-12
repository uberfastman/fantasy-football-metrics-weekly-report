import json
import logging
import os

import requests

logger = logging.getLogger(__name__)


class BeefStats(object):

    def __init__(self, data_dir, save_data=False, dev_offline=False):
        """
        Initialize class, load data from FOX Sports, and combine defensive player data
        """
        self.save_data = save_data

        self.fox_sports_public_api_key = {"apikey": "jE7yBJVRNAwdDesMgTzTXUUSx1It41Fq"}
        self.teams_url = "https://api.foxsports.com/sportsdata/v1/football/nfl/teams.json"
        self.tabbu_value = 500.0

        self.beef_data = {}
        self.beef_data_file_path = os.path.join(data_dir, "beef_data.json")
        self.open_beef_data()

        if not dev_offline:
            if not self.beef_data:
                fox_sports_nfl_teams_data = requests.get(self.teams_url, params=self.fox_sports_public_api_key).json()

                for team in fox_sports_nfl_teams_data.get("page"):
                    team_url = team.get("links").get("api").get("athletes")
                    team_roster = requests.get(team_url, self.fox_sports_public_api_key).json()
                    for player in team_roster.get("page"):

                        player_full_name = player.get("firstName") + " " + player.get("lastName")

                        if player_full_name not in self.beef_data.keys():
                            self.add_player(player_full_name, player, team)

                        if player.get("position").get("abbreviation") in ["CB", "LB", "DE", "DT", "S"]:
                            if team.get("abbreviation") not in self.beef_data.keys():
                                self.beef_data[team.get("abbreviation")] = {
                                    "weight": player.get("weight"),
                                    "tabbu": float(player.get("weight")) / self.tabbu_value,
                                }
                            else:
                                weight = self.beef_data[team.get("abbreviation")].get("weight") + float(player.get("weight"))
                                tabbu = self.beef_data[team.get("abbreviation")].get("tabbu") + (float(player.get("weight")) / self.tabbu_value)
                                self.beef_data[team.get("abbreviation")]["weight"] = weight
                                self.beef_data[team.get("abbreviation")]["tabbu"] = tabbu
                self.save_beef_data()
        else:
            if not self.beef_data:
                raise FileNotFoundError(
                    "FILE {} DOES NOT EXIST. CANNOT RUN LOCALLY WITHOUT HAVING PREVIOUSLY PERSISTED DATA!".format(
                        self.beef_data_file_path))

        if len(self.beef_data) == 0:
            logger.warning(
                "NO beef data was loaded, please check your internet connection or the availability of "
                "'https://api.foxsports.com/sportsdata/v1/football/nfl.json?apikey=jE7yBJVRNAwdDesMgTzTXUUSx1It41Fq' "
                "and try generating a new report.")
        else:
            logger.info("{} player weights/TABBUs were loaded".format(len(self.beef_data)))

    def open_beef_data(self):
        if os.path.exists(self.beef_data_file_path):
            with open(self.beef_data_file_path, "r", encoding="utf-8") as beef_in:
                self.beef_data = dict(json.load(beef_in))

    def save_beef_data(self):
        if self.save_data:
            with open(self.beef_data_file_path, "w", encoding="utf-8") as beef_out:
                json.dump(self.beef_data, beef_out, ensure_ascii=False, indent=2)

    def add_player(self, player_full_name, player_json=None, team_json=None, update_saved_beef_data=False):

        if player_json:
            player_beef_dict = {
                "fullName": player_full_name,
                "firstName": player_json.get("firstName").replace(".", ""),
                "lastName": player_json.get("lastName"),
                "weight": player_json.get("weight"),
                "tabbu": float(player_json.get("weight")) / float(self.tabbu_value),
                "position": player_json.get("position").get("abbreviation"),
                "team": team_json.get("abbreviation")
            }
        else:
            player_beef_dict = {
                "fullName": player_full_name,
                "weight": 0,
                "tabbu": 0,
            }
        self.beef_data[player_full_name] = player_beef_dict
        if update_saved_beef_data:
            self.save_beef_data()
        return player_beef_dict

    def get_player_beef_stat(self, player_first_name, player_last_name, team_abbr, key_str):
        team_abbr = team_abbr.upper()

        if player_last_name:
            player_full_name = player_first_name + " " + player_last_name
        else:
            player_full_name = team_abbr
        if player_full_name not in self.beef_data.keys():
            return self._fetch_specific_player(
                player_first_name, player_last_name, player_full_name, team_abbr)[key_str]
        else:
            return self.beef_data[player_full_name][key_str]

    def get_player_weight(self, player_first_name, player_last_name, team_abbr):
        return self.get_player_beef_stat(player_first_name, player_last_name, team_abbr, "weight")

    def get_player_tabbu(self, player_first_name, player_last_name, team_abbr):
        return self.get_player_beef_stat(player_first_name, player_last_name, team_abbr, "tabbu")

    def _fetch_specific_player(self, player_first_name, player_last_name, player_full_name, team_abbr):

        if player_last_name:
            player_last_name = player_last_name.split(" ")[0] if len(player_last_name.split(" ")) > 1 else player_last_name

        fox_sports_nfl_teams_data = requests.get(self.teams_url, params=self.fox_sports_public_api_key).json()
        for team in fox_sports_nfl_teams_data.get("page"):
            if team.get("abbreviation") == team_abbr:
                team_url = team.get("links").get("api").get("athletes")
                team_roster = requests.get(team_url, self.fox_sports_public_api_key).json()
                for player in team_roster.get("page"):
                    if player_first_name == player.get("firstName").replace(".", "") and player_last_name in player.get("lastName"):
                        return self.add_player(player_full_name, player, team, update_saved_beef_data=True)

        logger.info("Player not found: {}. Setting weight and TABBU to 0.".format(player_full_name))
        return self.add_player(player_full_name, update_saved_beef_data=True)
