from sleeper_wrapper import League
import json
import requests
from collections import defaultdict
import pprint
import os
from datetime import datetime, timedelta
from operator import itemgetter


import io
from PIL import Image

week = 1
season = 2019
# league_id = "355526480094113792"
# league_id = "363728866864312320"
# league_id = "479455148251279360"
league_id = "422592816833646592"


sleeper_players_filepath = "sleeper-players.json"
if not os.path.exists(sleeper_players_filepath):
    print("Player data does not exist... retrieving.")
    players_data = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    with open(sleeper_players_filepath, "w") as players_file:
        json.dump(players_data, players_file, ensure_ascii=False, indent=2)
else:
    sleeper_players_file_modified_timestamp = datetime.fromtimestamp(os.path.getmtime(sleeper_players_filepath))
    if sleeper_players_file_modified_timestamp < (datetime.today() - timedelta(days=1)):
        print("Player data over a day old... refreshing.")
        players_data = requests.get("https://api.sleeper.app/v1/players/nfl").json()
        with open("sleeper-players.json", "w") as players_file:
            json.dump(players_data, players_file, ensure_ascii=False, indent=2)
    else:
        print("Player data still recent... skipping refresh.")


sleeper_players_stats_by_week_filepath = "sleeper-players-stats-week_" + str(week) + ".json"
if not os.path.exists(sleeper_players_stats_by_week_filepath):
    print("Player stats for week {} data does not exist... retrieving.".format(str(week)))
    players_stats_by_week_data = requests.get(
        "https://api.sleeper.app/v1/stats/nfl/regular/" + str(season) + "/" + str(week)).json()
    with open(sleeper_players_stats_by_week_filepath, "w") as players_stats_by_week_file:
        json.dump(players_stats_by_week_data, players_stats_by_week_file, ensure_ascii=False, indent=2)
else:
    sleeper_players_stats_by_week_file_modified_timestamp = datetime.fromtimestamp(
        os.path.getmtime(sleeper_players_stats_by_week_filepath))
    if sleeper_players_stats_by_week_file_modified_timestamp < (datetime.today() - timedelta(days=1)):
        print("Player stats for week {} data over a day old... refreshing.".format(str(week)))
        players_stats_by_week_data = requests.get(
            "https://api.sleeper.app/v1/stats/nfl/regular/" + str(season) + "/" + str(week)).json()
        with open(sleeper_players_stats_by_week_filepath, "w") as players_stats_by_week_file:
            json.dump(players_stats_by_week_data, players_stats_by_week_file, ensure_ascii=False, indent=2)
    else:
        print("Player stats for week {} data still recent... skipping refresh.".format(str(week)))

sleeper_players_projected_stats_by_week_filepath = "sleeper-players-projected-stats-week_" + str(week) + ".json"
if not os.path.exists(sleeper_players_projected_stats_by_week_filepath):
    print("Player projected stats for week {} data does not exist... retrieving.".format(str(week)))
    players_projected_stats_by_week_data = requests.get(
        "https://api.sleeper.app/v1/projections/nfl/regular/" + str(season) + "/" + str(week)).json()
    with open(sleeper_players_projected_stats_by_week_filepath, "w") as players_projected_stats_by_week_file:
        json.dump(players_projected_stats_by_week_data, players_projected_stats_by_week_file, ensure_ascii=False, indent=2)
else:
    sleeper_players_projected_stats_by_week_file_modified_timestamp = datetime.fromtimestamp(
        os.path.getmtime(sleeper_players_projected_stats_by_week_filepath))
    if sleeper_players_projected_stats_by_week_file_modified_timestamp < (datetime.today() - timedelta(days=1)):
        print("Player projected stats for week {} data over a day old... refreshing.".format(str(week)))
        players_projected_stats_by_week_data = requests.get(
            "https://api.sleeper.app/v1/projections/nfl/regular/" + str(season) + "/" + str(week)).json()
        with open(sleeper_players_projected_stats_by_week_filepath, "w") as players_projected_stats_by_week_file:
            json.dump(players_projected_stats_by_week_data, players_projected_stats_by_week_file, ensure_ascii=False, indent=2)
    else:
        print("Player projected stats for week {} data still recent... skipping refresh.".format(str(week)))


with open(sleeper_players_filepath, "r") as player_json:
    players = json.load(player_json)

with open(sleeper_players_stats_by_week_filepath, "r") as player_stats_by_week_json:
    player_stats_by_week = json.load(player_stats_by_week_json)

with open(sleeper_players_projected_stats_by_week_filepath, "r") as player_projected_stats_by_week_json:
    player_projected_stats_by_week = json.load(player_projected_stats_by_week_json)


# out = requests.get("https://api.sleeper.app/v1/league/" + league_id).json()
# out_type = "league_info"
# print(out)

def fetch_player_data(player_id):
    player = players.get(player_id)
    player["stats"] = player_stats_by_week.get(player_id)
    player["projected"] = player_projected_stats_by_week.get(player_id)


users = requests.get("https://api.sleeper.app/v1/league/" + league_id + "/users").json()
users = {user.get("user_id"): user for user in users}

matchups = requests.get("https://api.sleeper.app/v1/league/" + league_id + "/matchups/" + str(week)).json()
for matchup_team in matchups:

    matchup_team["starters"] = [
        fetch_player_data(player_id) for player_id in matchup_team.get("starters")
    ] if matchup_team.get("starters") else []

    matchup_team["players"] = [
        fetch_player_data(player_id) for player_id in matchup_team.get("players")
    ] if matchup_team.get("players") else []

matchup_pairs = defaultdict(lambda: defaultdict(list))
for matchup_team in matchups:
    matchup_pairs[matchup_team.get("matchup_id")]["teams"].append(matchup_team)

for matchup_pair in matchup_pairs.values():
    matchup_pair_roster_ids = [matchup_pair["teams"][0].get("roster_id"), matchup_pair["teams"][1].get("roster_id")]
    matchup_pair["roster_ids"] = matchup_pair_roster_ids

matchups = {week: matchup_pairs}

out_type = "league_matchups-week_" + str(week)
# print("MATCHUPS:")
# print(matchups)

with open(out_type + "-out.json", "w") as out_file:
    json.dump(matchups, out_file, ensure_ascii=False, indent=2)


rosters = requests.get("https://api.sleeper.app/v1/league/" + league_id + "/rosters").json()
rosters = sorted(rosters, key=lambda x: (
    x.get("settings").get("wins"),
    -x.get("settings").get("losses"),
    x.get("settings").get("ties"),
    float(str(x.get("settings").get("fpts")) + "." + str(x.get("settings").get("fpts_decimal")))
), reverse=True)

for team in rosters:
    team["taxi"] = [players.get(player) for player in team.get("taxi")] if team.get("taxi") else []
    team["starters"] = [players.get(player) for player in team.get("starters")] if team.get("starters") else []
    team["reserve"] = [players.get(player) for player in team.get("reserve")] if team.get("reserve") else []
    team["players"] = [players.get(player) for player in team.get("players")] if team.get("players") else []
    team["owner"] = users.get(team.get("owner_id"))
    team["co_owners"] = [users.get(co_owner) for co_owner in team.get("co_owners")] if team.get("co_owners") else []

    for week, matchup_pairs in matchups.items():

        matchups_by_week = []
        for pair, matchup_pair in matchup_pairs.items():
            if team.get("roster_id") in matchup_pair.get("roster_ids"):
                matchups_by_week.extend(matchup_pair["teams"])
        team["matchups"] = {
            week: matchups_by_week
        }


out_type = "league_rosters"
# print("ROSTERS:")
# print(rosters)

with open(out_type + "-out.json", "w") as out_file:
    json.dump(rosters, out_file, ensure_ascii=False, indent=2)






# out = requests.get("https://api.sleeper.app/v1/league/" + league_id + "/users").json()
# out_type = "league_users"
# print(out)

# avatar = requests.get("https://sleepercdn.com/avatars/f41d6e80519da8a4fe532196a3bb34f4").content
# out_type = "avatar_f41d6e80519da8a4fe532196a3bb34f4"
# print(avatar)

# image = Image.frombytes('RGBA', (128, 128), avatar, 'raw')

# image = Image.open(io.BytesIO(avatar))
# # image.show()
# image.save(out_type + ".png")


# out = requests.get("https://api.sleeper.app/v1/league/" + league_id + "/transactions/" + str(week)).json()
# out_type = "league_transactions-week_" + str(week)
# print(out)

# out = requests.get("https://api.sleeper.app/v1/stats/nfl/regular/" + str(season) + "/" + str(week)).json()
# out_type = "league_player_stats-week_" + str(week)
# print(out)

# out = requests.get("https://api.sleeper.app/v1/projections/nfl/regular/" + str(season) + "/" + str(week)).json()
# out_type = "league_player_projections-week_" + str(week)
# print(out)

# league = League(league_id)
#
# out = league.get_league()
# # out_type = "league_info"
# # print(out)
#
# users = league.get_users()
# # out_type = "league_users"
# # print(users)
#
# matchups = league.get_matchups(week)
# # out_type = "league_matchups"
# # print(matchups)
#
# rosters = league.get_rosters()
# # out_type = "league_rosters"
# # print(rosters)
# #
# out = league.get_standings(rosters, users)
# # out_type = "league_standings"
# # print(out)
#
# out = league.get_scoreboards(rosters, matchups, users, "pts_std", week)
# out_type = "league_scoreboard"
# print(out)
#



# with open(out_type + "-out.json", "w") as out_file:
#     json.dump(out, out_file, ensure_ascii=False, indent=2)


#
# with open("league_matchups-week_6-out.json", "r") as week_6_matchups:
#     matchups_week_6 = json.load(week_6_matchups)
#
# mapped_matchups_week_6 = []
# for matchup in matchups_week_6:
#     matchup["starters"] = [players.get(starter) for starter in matchup.get("starters")]
#     matchup["players"] = [players.get(player) for player in matchup.get("players")]
#     mapped_matchups_week_6.append(matchup)
#
# with open("mapped_matchups_week_6-out.json", "w") as mapped_matchups:
#     json.dump(mapped_matchups_week_6, mapped_matchups, ensure_ascii=False, indent=2)

