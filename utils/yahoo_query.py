import json
import os

import pandas as pd
from yahoo_oauth import OAuth2


class YahooQuery(object):

    def __init__(self, config, league_id, refresh_data, save_bool, dev_bool, league_test_dir, base_dir=""):

        self.config = config
        self.league_id = league_id
        self.refresh_data = refresh_data
        self.save_bool = save_bool
        self.dev_bool = dev_bool
        self.league_test_dir = league_test_dir
        self.league_key = None
        self.league_name = None
        self.playoff_slots = None
        self.num_regular_season_weeks = None

        command_line_only = config.getboolean("OAuth_Settings", "command_line_only")
        yahoo_oauth_token_cache_dir = os.path.dirname(os.path.abspath(__file__)) + "/../" + config.get("OAuth_Settings", "yahoo_oauth_token_cache_dir")

        if not self.dev_bool and not self.refresh_data:

            with open(yahoo_oauth_token_cache_dir + "private.json") as yahoo_app_credentials:
                auth_info = json.load(yahoo_app_credentials)
            self._yahoo_consumer_key = auth_info["consumer_key"]
            self._yahoo_consumer_secret = auth_info["consumer_secret"]

            token_file_path = yahoo_oauth_token_cache_dir + "token.json"
            if os.path.isfile(token_file_path):
                with open(token_file_path) as yahoo_oauth_token:
                    auth_info = json.load(yahoo_oauth_token)
            else:
                with open(token_file_path, "w") as yahoo_oauth_token:
                    json.dump(auth_info, yahoo_oauth_token)

            if "access_token" in auth_info.keys():
                self._yahoo_access_token = auth_info["access_token"]

            self.oauth = OAuth2(None, None, from_file=token_file_path)
            if not self.oauth.token_is_valid():
                self.oauth.refresh_access_token()

    def query(self, url):
        response = self.oauth.session.get(url, params={"format": "json"})
        return response.json().get("fantasy_content")

    def get_league_key(self):

        if not self.dev_bool and not self.refresh_data:
            # get fantasy football game info
            # game_data = self.query("select * from fantasysports.games where game_key='nfl'")
            game_data = self.query("https://fantasysports.yahooapis.com/fantasy/v2/game/nfl").get("game")
        else:
            with open(self.league_test_dir +
                      "/" +
                      "game_data.json", "r") as gd_file:
                game_data = json.load(gd_file)

        if self.save_bool:
            with open(self.league_test_dir +
                      "/" +
                      "game_data.json", "w") as gd_file:
                json.dump(game_data, gd_file)

        df = pd.DataFrame(game_data)
        # unique league key composed of this year's yahoo fantasy football game id and the unique league id
        self.league_key = df.loc[0, "game_key"] + ".l." + self.league_id
        # self.league_key = "380.l." + self.league_id

        return self.league_key

    def get_user_game_history(self):
        user_game_history = self.query("https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games/")

        return user_game_history

    def get_user_league_history(self):
        user_league_history = self.query("https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games/leagues/")

        return user_league_history

    def get_league_overview(self):
        league_overview = self.query("https://fantasysports.yahooapis.com/fantasy/v2/league/" + self.league_key + "/")

        return league_overview

    def get_league_standings_data(self):

        if not self.dev_bool and not self.refresh_data:
            # get data for all league standings
            # league_standings_data = self.query(
            #     "select * from fantasysports.leagues.standings where league_key='" + self.league_key + "'")
            league_standings_data = self.query("https://fantasysports.yahooapis.com/fantasy/v2/league/" + self.league_key + "/standings").get("league")
            # TODO: incorporate winnings into reports
            # entry_fee = league_standings_data[0].get("entry_fee")
        else:
            with open(self.league_test_dir +
                      "/" +
                      "league_standings_data.json", "r") as lsd_file:
                league_standings_data = json.load(lsd_file)

        if self.save_bool:
            with open(self.league_test_dir +
                      "/" +
                      "league_standings_data.json", "w") as lsd_file:
                json.dump(league_standings_data, lsd_file)

        df = pd.DataFrame(league_standings_data)
        self.league_name = df.loc[0, "name"]

        # return league_standings_data
        return df

    def get_roster_data(self):

        if not self.dev_bool and not self.refresh_data:
            # get individual league roster
            # roster_data = self.query(
            #     "select * from fantasysports.leagues.settings where league_key='" + self.league_key + "'")
            roster_data = self.query("https://fantasysports.yahooapis.com/fantasy/v2/league/" + self.league_key + "/settings").get("league")
        else:
            with open(self.league_test_dir +
                      "/" +
                      "roster_data.json", "r") as rd_file:
                roster_data = json.load(rd_file)

        if self.save_bool:
            with open(self.league_test_dir +
                      "/" +
                      "roster_data.json", "w") as rd_file:
                json.dump(roster_data, rd_file)

        playoff_slots = roster_data[0].get("num_playoff_teams")
        playoff_start_week = roster_data[0].get("playoff_start_week")

        if playoff_slots:
            self.playoff_slots = int(playoff_slots)
        else:
            self.playoff_slots = self.config.getint("Fantasy_Football_Report_Settings", "num_playoff_slots")

        if playoff_start_week:
            self.num_regular_season_weeks = int(playoff_start_week) - 1
        else:
            self.num_regular_season_weeks = self.config.getint("Fantasy_Football_Report_Settings",
                                                               "num_regular_season_weeks")

        return roster_data

    def get_teams_data(self):

        if not self.dev_bool and not self.refresh_data:
            # get data for all teams in league
            # teams_data = self.query(
            #     "select * from fantasysports.teams where league_key='" + self.league_key + "'")
            teams_data = self.query("https://fantasysports.yahooapis.com/fantasy/v2/league/" + self.league_key + "/teams").get("league")
        else:
            with open(self.league_test_dir +
                      "/" +
                      "teams_data.json", "r") as td_file:
                teams_data = json.load(td_file)

        if self.save_bool:
            with open(self.league_test_dir +
                      "/" +
                      "teams_data.json", "w") as td_file:
                json.dump(teams_data, td_file)

        return teams_data

    def get_matchups_data(self, chosen_week):

        if not self.dev_bool and not self.refresh_data:
            # result = self.query(
            #     "select * from fantasysports.leagues.scoreboard where league_key='{0}' and week='{1}'".format(
            #         self.league_key, str(chosen_week)))
            result = self.query("https://fantasysports.yahooapis.com/fantasy/v2/league/" + self.league_key + "/scoreboard;week=" + str(chosen_week)).get("league")
        else:
            with open(self.league_test_dir +
                      "/week_" + str(chosen_week) + "/" +
                      "result_data.json", "r") as rsd_file:
                result = json.load(rsd_file)

        if self.save_bool:

            result_data_path = self.league_test_dir + "/week_" + str(chosen_week) + "/"

            if not os.path.exists(result_data_path):
                os.makedirs(result_data_path)
            with open(result_data_path + "result_data.json", "w") as rsd_file:
                json.dump(result, rsd_file)
        return result[1].get("scoreboard").get("0")

    def get_roster_stats_data(self, team, team_name, chosen_week):

        if not self.dev_bool and not self.refresh_data:
            # get data for this individual team
            # roster_stats_data = self.query(
            #     "select * from fantasysports.teams.roster.stats where team_key='" + self.league_key + ".t." +
            #     team + "' and week='" + chosen_week + "'")
            roster_stats_data = self.query("https://fantasysports.yahooapis.com/fantasy/v2/team/" + self.league_key + ".t." + str(team) + "/roster;week=" + str(chosen_week)).get("team")[0]
        else:
            with open(self.league_test_dir +
                      "/week_" + chosen_week + "/roster_data/" +
                      str(team_name, "utf-8").replace(" ", "-") +
                      "_roster_data.json", "r") as trd_file:
                roster_stats_data = json.load(trd_file)

        if self.save_bool:
            with open(self.league_test_dir +
                      "/week_" + chosen_week + "/roster_data/" +
                      str(team_name, "utf-8").replace(" ", "-") +
                      "_roster_data.json", "w") as trd_file:
                json.dump(roster_stats_data, trd_file)

        return roster_stats_data
