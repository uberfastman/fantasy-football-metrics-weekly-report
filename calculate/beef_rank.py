import requests


class BeefRank(object):

    def __init__(self):
        pass


br = BeefRank()

params = {"apikey": "jE7yBJVRNAwdDesMgTzTXUUSx1It41Fq"}

teams = requests.get("https://api.foxsports.com/sportsdata/v1/football/nfl/teams.json", params=params).json()

player_first_name = "Aaron"
player_last_name = "Rodgers"
prof_token = player_first_name.lower() + "-" + player_last_name.lower()
team_abbr = "GB"
for team in teams.get("page"):

    if team.get("abbreviation") == team_abbr:
        url = team.get("links").get("api").get("athletes")
        roster = requests.get(url, params).json()

        for player in roster.get("page"):
            if player.get("profileToken") == prof_token:
                print(player.get("firstName") + " " + player.get("lastName") + ": " + str(player.get("weight")) + " lbs.")
