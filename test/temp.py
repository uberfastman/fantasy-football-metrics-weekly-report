from sleeper_wrapper import League
import json
import pprint


week = 1


league = League("355526480094113792")

# out = league.get_league()
# out_type = "league_info"
# print(out)

out = league.get_matchups(week)
out_type = "league_matchups"
print(out)

# out = league.get_rosters()
# out_type = "league_rosters"
# print(out)

# out = league.get_standings(league.get_rosters(), league.get_users())
# out_type = "league_standings"
# print(out)

# out = league.get_scoreboards(league.get_rosters(), league.get_matchups(week), league.get_users(), "pts_std", week)
# out_type = "league_scoreboards"
# print(out)


with open(out_type + "-out.json", "w") as out_file:
    json.dump(out, out_file, ensure_ascii=False, indent=2)

# with open(out_type + "-out.txt", "w") as out_file:
#     out_file.write(pprint.pformat(out))


