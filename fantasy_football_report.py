# Written by: Wren J. Rudolph
# Code snippets taken from: http://tech.thejoestory.com/2014/12/yahoo-fantasy-football-api-using-python.html

import collections
import datetime
import os
import random
from ConfigParser import ConfigParser
from operator import itemgetter
import distutils.util as distutils

import simplejson
import yql
from yql.storage import FileTokenStore

from google_drive_uploader import GoogleDriveUploader
from pdf_generator import PdfGenerator
from slack_messenger import SlackMessenger

# local config vars
config = ConfigParser()
config.read('config.ini')
league_id = config.get("Fantasy_Football_Report_Settings", "chosen_league_id")

# verification output message
print "Generating fantasy football report for league with id: %s (report generated: %s)\n" % (league_id, "{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))

# yahoo oauth api (consumer) key and secret
with open('private.txt', 'r') as auth_file:
    auth_data = auth_file.read().split("\n")
consumer_key = auth_data[0]
consumer_secret = auth_data[1]

# yahoo oauth process
y3 = yql.ThreeLegged(consumer_key, consumer_secret)
_cache_dir = config.get("OAuth_Settings", "yql_cache_dir")
if not os.access(_cache_dir, os.R_OK):
    os.mkdir(_cache_dir)

token_store = FileTokenStore(_cache_dir, secret='sasfasdfdasfdaf')

stored_token = token_store.get('foo')

if not stored_token:

    request_token, auth_url = y3.get_token_and_auth_url()

    print "Visit url %s and get a verifier string" % auth_url

    verifier = raw_input("Enter the code: ")

    token = y3.get_access_token(request_token, verifier)

    token_store.set('foo', token)

else:

    print "Verifying token...\n"

    token = y3.check_token(stored_token)

    if token != stored_token:

        print "Setting stored token!\n"

        token_store.set('foo', token)

"""
Functions
"""


def yql_query(query):

    # print "Executing query: %s\n" % query
    return y3.execute(query, token=token).rows


def check_eligible_players_by_position(position_str, player_name_str, weekly_player_points, eligible_player_positions,
                                       position_list):
    if position_str in eligible_player_positions:

        float_point_value = 0.0
        if weekly_player_points is not None:
            float_point_value += float(weekly_player_points)

        position_list.append([player_name_str, float_point_value])


def check_eligible_players_by_position_with_flex(position_str, player_name_str, weekly_player_points,
                                                 eligible_player_positions, flex_option_positions, position_list,
                                                 flex_player_candidates):
    if position_str in eligible_player_positions:

        float_point_value = 0.0
        if weekly_player_points is not None:
            float_point_value += float(weekly_player_points)

        position_list.append([player_name_str, float_point_value])

        if position_str in flex_option_positions:
            flex_player_candidates.append([player_name_str, float_point_value])


def get_optimal_players(player_list, position_slots, optimal_players_list):
    if player_list:
        player_list = sorted(player_list, key=itemgetter(1))[::-1]

        player_index = 0
        optimal_players_at_position = []
        temp_position_slots = position_slots
        while temp_position_slots > 0:
            try:
                optimal_players_at_position.append(player_list[player_index])
            except IndexError:
                pass
            player_index += 1
            temp_position_slots -= 1

        optimal_players_list.append(optimal_players_at_position)
        return optimal_players_at_position


def instantiate_data_from_txt_file(time_series_data, time_series_data_filename):

    with open(time_series_data_filename, "a+") as json_data:

        json_data.seek(0)
        data = json_data.read(1)
        json_data.seek(0)

        if data:
            return simplejson.load(json_data)
        else:
            return simplejson.dump(time_series_data, json_data)


def load_time_series_data(time_series_data, weekly_data, time_series_data_filename):

    if time_series_data:
        with open(time_series_data_filename, "w") as json_data:
            simplejson.dump(time_series_data, json_data)
    else:
        with open(time_series_data_filename, "w") as json_data:
            simplejson.dump(weekly_data, json_data)

    with open(time_series_data_filename, "r") as json_data:
        return simplejson.load(json_data)


game_data_query = "select * from fantasysports.games where game_key='nfl'"
game_data = yql_query(game_data_query)
game_key = game_data[0].get("game_key")

# unique league key composed of this year's yahoo fantasy football game id and the unique league id
league_key = game_key + ".l." + league_id
print "League key: %s\n" % league_key

# get individual league roster
roster_data_query = "select * from fantasysports.leagues.settings where league_key='" + league_key + "'"
roster_data = y3.execute(roster_data_query, token=token).rows

league_roster_active = []
league_roster_bench = []
qb_slots = 0
wr_slots = 0
rb_slots = 0
flex_slots = 0
te_slots = 0
k_slots = 0
def_slots = 0
idp_slots = 0
flex_positions = []

for position in roster_data[0].get("settings").get("roster_positions").get("roster_position"):

    position_name = position.get("position")
    position_count = int(position.get("count"))

    count = position_count
    while count > 0:
        if position_name != "BN":
            league_roster_active.append(position_name)
        else:
            league_roster_bench.append(position_name)
        count -= 1

    if position_name == "QB":
        qb_slots += position_count
    if position_name == "WR":
        wr_slots += position_count
    if position_name == "RB":
        rb_slots += position_count
    if position_name == "W/R":
        flex_slots += position_count
        flex_positions = ["WR", "RB"]
    if position_name == "W/R/T":
        flex_slots += position_count
        flex_positions = ["WR", "RB", "TE"]
    if position_name == "TE":
        te_slots += position_count
    if position_name == "K":
        k_slots += position_count
    if position_name == "DEF":
        def_slots += position_count
    if position_name == "D":
        idp_slots += position_count

# get data for all teams in league
teams_data_query = "select * from fantasysports.teams where league_key='" + league_key + "'"
teams_data = yql_query(teams_data_query)
teams_dict = {}

for team in teams_data:

    team_id = team.get("team_id")
    team_name = team.get("name")
    team_managers = team.get("managers").get("manager")

    if type(team_managers) is dict:
        team_manager = team_managers.get("nickname")

    else:
        for manager in team_managers:
            if manager.get("is_comanager") is None:
                team_manager = manager.get("nickname")

    team_info_dict = {"name": team_name, "manager": team_manager}
    teams_dict[team_id] = team_info_dict

# output league teams for verification
print "TEAMS: {}\n".format(teams_dict)

# get data for all league standings
league_standings_data_query = "select * from fantasysports.leagues.standings where league_key='" + league_key + "'"
league_standings_data = yql_query(league_standings_data_query)

# league information for potential later features
# start_week = league_standings_data[0].get("start_week")
# start_date = league_standings_data[0].get("start_date")
# end_week = league_standings_data[0].get("end_week")
# end_date = league_standings_data[0].get("end_date")
#
# game_code = league_standings_data[0].get("game_code")
# season = league_standings_data[0].get("season")
#
league_name = league_standings_data[0].get("name")
# league_id = league_standings_data[0].get("league_id")
# league_url = league_standings_data[0].get("url")
# entry_fee = league_standings_data[0].get("entry_fee")

chosen_week = str(int(league_standings_data[0].get("current_week")) - 1)
# chosen_week = str(int(league_standings_data[0].get("current_week")))
print "Generating report for week {}\n".format(chosen_week)

# prohibited statuses to check team coaching efficiency eligibility
prohibited_status_list = ["PUP-P", "SUSP", "O", "IR"]

team_results_dict = {}

# iterate through all teams and build team_results_dict containing all relevant team stat information
for team in teams_dict:

    team_id = team
    team_name = teams_dict.get(team).get("name")
    team_info_dict = teams_dict.get(team)

    # get data for this individual team
    roster_stats_data_query = "select * from fantasysports.teams.roster.stats where team_key='" + league_key + ".t." + team + "' and week='" + chosen_week + "'"
    roster_stats_data = yql_query(roster_stats_data_query)

    positions_filled_active = []
    positions_filled_bench = []

    players = []
    active_players = []
    bench_players = []
    ineligible_efficiency_player_count = 0

    quarterbacks = []
    wide_receivers = []
    running_backs = []
    flex_candidates = []
    tight_ends = []
    kickers = []
    team_defenses = []
    individual_defenders = []

    actual_weekly_score = 0.0
    actual_bench_score = 0.0

    for player in roster_stats_data[0].get("roster").get("players").get("player"):

        player_info_dict = {}

        player_name = player.get("name")["full"]
        player_status = player.get("status")
        player_bye = player.get("bye_weeks")["week"]
        player_selected_position = player.get("selected_position").get("position")
        player_eligible_positions = player.get("eligible_positions").get("position")
        player_points = player.get("player_points").get("total")

        if player_points is None:

            # UNCOMMENT FOR PROPER FUNCTIONING OF SCRIPT!
            player_points = 0.0

            # ----------------------------------------------------------------------------------------------------------
            # --------------------------------------FOR TESTING ONLY----------------------------------------------------
            # ----------------------------------------------------------------------------------------------------------
            # player_points = random.uniform(0, 15)
            # ----------------------------------------------------------------------------------------------------------
            # ----------------------------------------------------------------------------------------------------------
            # ----------------------------------------------------------------------------------------------------------
        else:
            player_points = float(player_points)

        if player_selected_position != "BN":
            positions_filled_active.append(player_selected_position)
            actual_weekly_score += player_points
        else:
            positions_filled_bench.append(player_selected_position)
            if int(player_bye) == int(chosen_week):
                ineligible_efficiency_player_count += 1
            elif player_status in prohibited_status_list:
                ineligible_efficiency_player_count += 1
            actual_bench_score += player_points

        player_info_dict["name"] = player_name
        player_info_dict["status"] = player_status
        player_info_dict["bye_week"] = player_bye
        player_info_dict["selected_position"] = player_selected_position
        player_info_dict["fantasy_points"] = player_points

        check_eligible_players_by_position("QB", player_name, player_points, player_eligible_positions, quarterbacks)
        check_eligible_players_by_position_with_flex("WR", player_name, player_points, player_eligible_positions, flex_positions, wide_receivers, flex_candidates)
        check_eligible_players_by_position_with_flex("RB", player_name, player_points, player_eligible_positions, flex_positions, running_backs, flex_candidates)
        check_eligible_players_by_position_with_flex("TE", player_name, player_points, player_eligible_positions, flex_positions, tight_ends, flex_candidates)
        check_eligible_players_by_position("K", player_name, player_points, player_eligible_positions, kickers)
        check_eligible_players_by_position("DEF", player_name, player_points, player_eligible_positions, team_defenses)

        if "D" in player_eligible_positions and "DEF" not in player_eligible_positions:

            point_value = 0.0
            if player_points is not None:
                point_value += float(player_points)

            individual_defenders.append([player_name, point_value])

        players.append(player_info_dict)

    # used to calculate optimal score for coaching efficiency
    optimal_players = []

    optimal_qbs = get_optimal_players(quarterbacks, qb_slots, optimal_players)
    optimal_wrs = get_optimal_players(wide_receivers, wr_slots, optimal_players)
    optimal_rbs = get_optimal_players(running_backs, rb_slots, optimal_players)
    optimal_tes = get_optimal_players(tight_ends, te_slots, optimal_players)
    optimal_ks = get_optimal_players(kickers, k_slots, optimal_players)
    optimal_defs = get_optimal_players(team_defenses, def_slots, optimal_players)
    optimal_idps = get_optimal_players(individual_defenders, idp_slots, optimal_players)

    optimal_flexes = []
    if flex_candidates:
        flex_set = set(map(tuple, flex_candidates))
        wr_set = set(map(tuple, optimal_wrs))
        rb_set = set(map(tuple, optimal_rbs))
        te_set = set(map(tuple, optimal_tes))
        flex_set = flex_set - wr_set
        flex_set = flex_set - rb_set
        flex_set = flex_set - te_set

        flex_list = sorted(list(flex_set), key=itemgetter(1))[::-1]

        index = 0
        temp_slots = flex_slots
        while temp_slots > 0:
            try:
                optimal_flexes.append(flex_list[index])
            except IndexError:
                pass
            index += 1
            temp_slots -= 1

        optimal_players.append(optimal_flexes)

    optimal_lineup = [item for sublist in optimal_players for item in sublist]

    # calculate optimal score
    optimal_score = 0.0
    for player in optimal_lineup:
        optimal_score += player[1]

    # calculate coaching efficiency
    coaching_efficiency = (actual_weekly_score / optimal_score) * 100

    team_results_dict[team_name] = {
        "manager": teams_dict.get(team).get("manager"),
        "coaching_efficiency": "%.2f%%" % coaching_efficiency,
        "weekly_score": "%.2f" % actual_weekly_score,
        "bench_score": "%.2f" % actual_bench_score, "luck": "",
        "team_id": team_id
    }

    team_info_dict["players"] = players

    # apply coaching efficiency eligibility requirements for League of Emperors
    if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):

        efficiency_disqualification = False

        active_roster_bool = False
        if collections.Counter(league_roster_active) == collections.Counter(positions_filled_active):
            active_roster_bool = True

            if active_roster_bool and ineligible_efficiency_player_count <= 4:
                efficiency_disqualification = False
            else:
                print "ROSTER INVALID! There are %d inactive players on the bench of %s!\n" % (ineligible_efficiency_player_count, team_name)
                efficiency_disqualification = True

        else:
            print "ROSTER INVALID! There is not a full squad of active players starting on %s!\n" % team_name
            efficiency_disqualification = True

        if efficiency_disqualification:
            team_results_dict.get(team_name)["coaching_efficiency"] = "0.0%"

# ----------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------FOR TESTING ONLY---------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):
#     team_results_dict["Legion"] = {'manager': u'Uberfastman', 'coaching_efficiency': '98.00%', 'weekly_score': '150.00', 'bench_score': '50.00', "luck": "100.00", "team_id": "1"}
#     team_results_dict["The Implications"] = {'manager': u'Charlie', 'coaching_efficiency': '100.00%', 'weekly_score': '150.00', 'bench_score': '55.00', "luck": "0.00", "team_id": "4"}
#     team_results_dict["Stormin Normans"] = {'manager': u'Mike', 'coaching_efficiency': '0.0%', 'weekly_score': '148.00', 'bench_score': '65.00', "luck": "100.00", "team_id": "2"}
#
# if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "making_football_orange_id"):
#     team_results_dict["LeGEOn"] = {'manager': u'Uberfastman', 'coaching_efficiency': '100.00%', 'weekly_score': '149.00', 'bench_score': '50.00', "luck": "", "team_id": "8"}
#     team_results_dict["Washington IceNinjas"] = {'manager': u'Ryan', 'coaching_efficiency': '100.00%', 'weekly_score': '150.00', 'bench_score': '55.00', "luck": "", "team_id": "4"}
#     team_results_dict["Beamerball"] = {'manager': u'Andrew Mulrean', 'coaching_efficiency': '100.00%', 'weekly_score': '150.00', 'bench_score': '65.00', "luck": "", "team_id": "11"}
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

final_weekly_score_results_list = sorted(team_results_dict.iteritems(), key=lambda (k, v): (float(v.get("weekly_score")), k))[::-1]

weekly_score_results_data_list = []
place = 1
for key, value in final_weekly_score_results_list:
    ranked_team_name = key
    ranked_team_manager = value.get("manager")
    ranked_weekly_score = value.get("weekly_score")

    weekly_score_results_data_list.append([place, ranked_team_name, ranked_team_manager, ranked_weekly_score])

    place += 1

# get league scoreboard data
scoreboard_data = yql_query("select * from fantasysports.leagues.scoreboard where league_key='" + league_key + "' and week='" + chosen_week + "'")[0].get("scoreboard").get("matchups").get("matchup")
matchups_list = []
for matchup in scoreboard_data:
    individual_matchup = {}

    for team in matchup.get("teams").get("team"):
        individual_matchup[team.get("name")] = 0.0

    matchups_list.append(individual_matchup)

ranked_team_scores = []

for result in weekly_score_results_data_list:
    ranked_team_name = result[1]
    ranked_weekly_score = 0.0
    if "bench" in result[3]:
        ranked_weekly_score += float(result[3].split(" ")[0])
    else:
        ranked_weekly_score += float(result[3])

    ranked_team = {"name": ranked_team_name, "score": ranked_weekly_score, "luck": ""}
    ranked_team_scores.append(ranked_team)

for team in ranked_team_scores:

    team_name = team.get("name")
    for matchup in matchups_list:
        if team_name in matchup.keys():
            matchup[team_name] = team.get("score")

# set team matchup results for this week
team_matchup_result_dict = {}
for matchup in matchups_list:
    keys = matchup.keys()

    team_1_name = keys[0]
    team_2_name = keys[1]

    team_1_score = matchup.get(team_1_name)
    team_2_score = matchup.get(team_2_name)

    if team_1_score > team_2_score:
        team_matchup_result_dict[team_1_name] = "W"
        team_matchup_result_dict[team_2_name] = "L"
    elif team_1_score < team_2_score:
        team_matchup_result_dict[team_1_name] = "L"
        team_matchup_result_dict[team_2_name] = "W"
    else:
        team_matchup_result_dict[team_1_name] = "T"
        team_matchup_result_dict[team_2_name] = "T"

index = 0
results = []
top_team_score = ranked_team_scores[0].get("score")
bottom_team_score = ranked_team_scores[-1].get("score")

# calculate weekly luck metric
for ranked_team in ranked_team_scores:

    ranked_team_name = ranked_team.get("name")
    ranked_team_score = ranked_team.get("score")
    ranked_team_matchup_result = team_matchup_result_dict.get(ranked_team_name)

    ranked_team_score_without_team = list(ranked_team_scores)
    del ranked_team_score_without_team[ranked_team_scores.index(ranked_team)]

    luck = 0.00
    if ranked_team_score == top_team_score or ranked_team_score == bottom_team_score:
        ranked_team["luck"] = luck

    else:
        if ranked_team_matchup_result == "W" or ranked_team_matchup_result == "T":

            luck += (((sum(score.get("score") >= ranked_team_score for score in ranked_team_score_without_team)) / (float(len(ranked_team_score_without_team)))) * 100)
        else:
            luck += (((0 - sum(score.get("score") <= ranked_team_score for score in ranked_team_score_without_team)) / (float(len(ranked_team_score_without_team)))) * 100)

        ranked_team["luck"] = luck

    ranked_team["matchup_result"] = ranked_team_matchup_result

    results.append(ranked_team)
    index += 1

    team_results_dict.get(ranked_team_name)["luck"] = "%.2f%%" % luck
    team_results_dict.get(ranked_team_name)["matchup_result"] = ranked_team_matchup_result

results.sort(key=lambda x: x.get("luck"), reverse=True)

# ----------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------FOR TESTING ONLY---------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "making_football_orange_id"):
#     team_results_dict["LeGEOn"] = {'manager': u'Uberfastman', 'coaching_efficiency': '100.00%', 'weekly_score': '149.00', 'bench_score': '50.00', "luck": "100.00%", "team_id": "8"}
#     team_results_dict["Washington IceNinjas"] = {'manager': u'Ryan', 'coaching_efficiency': '100.00%', 'weekly_score': '150.00', 'bench_score': '55.00', "luck": "100.00%", "team_id": "4"}
#     team_results_dict["Beamerball"] = {'manager': u'Andrew Mulrean', 'coaching_efficiency': '100.00%', 'weekly_score': '150.00', 'bench_score': '65.00', "luck": "100.00%", "team_id": "11"}
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

final_coaching_efficiency_results_list = sorted(team_results_dict.iteritems(), key=lambda (k, v): (float(v.get("coaching_efficiency").strip("%")), k))[::-1]
final_luck_results_list = sorted(team_results_dict.iteritems(), key=lambda (k, v): (float(v.get("luck").strip("%")), k))[::-1]

# create data for coaching efficiency table
coaching_efficiency_results_data_list = []
efficiency_dq_count = 0
place = 1
for key, value in final_coaching_efficiency_results_list:
    ranked_team_name = key
    ranked_team_manager = value.get("manager")
    ranked_coaching_efficiency = str(value.get("coaching_efficiency"))

    if ranked_coaching_efficiency == "0.0%":
        ranked_coaching_efficiency = ranked_coaching_efficiency.replace("0.0%", "DQ")
        efficiency_dq_count += 1

    coaching_efficiency_results_data_list.append([place, ranked_team_name, ranked_team_manager, ranked_coaching_efficiency])

    place += 1

# create data for luck table
weekly_luck_results_data_list = []
place = 1
for key, value in final_luck_results_list:
    ranked_team_name = key
    ranked_team_manager = value.get("manager")
    ranked_luck = value.get("luck")

    weekly_luck_results_data_list.append([place, ranked_team_name, ranked_team_manager, ranked_luck])

    place += 1

# count number of ties for points, coaching efficiency, and luck
num_tied_scores = sum(manager.count(weekly_score_results_data_list[0][3]) for manager in weekly_score_results_data_list)
num_tied_efficiencies = sum(manager.count(coaching_efficiency_results_data_list[0][3]) for manager in coaching_efficiency_results_data_list)
num_tied_luck = sum(manager.count(weekly_luck_results_data_list[0][3]) for manager in weekly_luck_results_data_list)

# if there are ties, record them and break them if possible
tied_weekly_score_bool = False
if num_tied_scores > 1:
    print "THERE IS A WEEKLY SCORE TIE!\n"
    tied_weekly_score_bool = True
    tied_scores_list = list(final_weekly_score_results_list[:num_tied_scores])
    tied_scores_list = sorted(tied_scores_list, key=lambda x: float(x[1].get("bench_score")))[::-1]

    count = num_tied_scores
    index = 0
    while count > 0:
        weekly_score_results_data_list[index] = [
            index + 1,
            tied_scores_list[index][0],
            tied_scores_list[index][1].get("manager"),
            tied_scores_list[index][1].get("weekly_score") + " (bench score: " + tied_scores_list[index][1].get("bench_score") + ")"
        ]
        count -= 1
        index += 1
else:
    print "No weekly score ties.\n"

tied_coaching_efficiency_bool = False
if num_tied_efficiencies > 1:
    print "THERE IS A COACHING EFFICIENCY TIE!\n"
    tied_coaching_efficiency_bool = True
    tied_efficiencies_list = list(final_coaching_efficiency_results_list[:num_tied_efficiencies])

    count = num_tied_efficiencies
    index = 0
    while count > 0:
        coaching_efficiency_results_data_list[index] = [
            "1*",
            tied_efficiencies_list[index][0],
            tied_efficiencies_list[index][1].get("manager"),
            tied_efficiencies_list[index][1].get("coaching_efficiency")
        ]
        count -= 1
        index += 1
else:
    print "No coaching efficiency ties.\n"

tied_weekly_luck_bool = False
if num_tied_luck > 1:
    print "THERE IS A LUCK TIE!\n"
    tied_weekly_luck_bool = True
    tied_luck_list = list(final_luck_results_list[:num_tied_luck])

    count = num_tied_luck
    index = 0
    while count > 0:
        weekly_luck_results_data_list[index] = [
            "1*",
            tied_luck_list[index][0],
            tied_luck_list[index][1].get("manager"),
            tied_luck_list[index][1].get("luck")
        ]
        count -= 1
        index += 1
else:
    print "No luck ties.\n"

# create team data for charts
teams_data_list = []
for team in team_results_dict:

    temp_team_info = team_results_dict.get(team)

    teams_data_list.append([
        temp_team_info.get("team_id"),
        team,
        temp_team_info.get("weekly_score"),
        temp_team_info.get("coaching_efficiency"),
        temp_team_info.get("luck")
    ])

teams_data_list.sort(key=lambda x: int(x[0]))

# build lists for time series charts
time_series_points_data = []
time_series_points_data_filename = "time_series_points_data_" + league_id + "_json.txt"
time_series_efficiency_data = []
time_series_efficiency_data_filename = "time_series_efficiency_data_" + league_id + "_json.txt"
time_series_luck_data = []
time_series_luck_data_filename = "time_series_luck_data_" + league_id + "_json.txt"

time_series_points_data = instantiate_data_from_txt_file(time_series_points_data, time_series_points_data_filename)
time_series_efficiency_data = instantiate_data_from_txt_file(time_series_efficiency_data, time_series_efficiency_data_filename)
time_series_luck_data = instantiate_data_from_txt_file(time_series_luck_data, time_series_luck_data_filename)

ordered_team_names = []
weekly_points_data = []
weekly_coaching_efficiency_data = []
weekly_luck_data = []

for team in teams_data_list:

    # ------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------FOR TESTING ONLY-------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    test_week_var = 0
    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------

    ordered_team_names.append(team[1])
    weekly_points_data.append([(int(chosen_week), float(team[2]))])
    weekly_coaching_efficiency_data.append([(int(chosen_week), float(team[3].replace("%", "")))])
    weekly_luck_data.append([(int(chosen_week), float(team[4].replace("%", "")))])

    append_new_data_bool = bool(distutils.strtobool(config.get("Data_Settings", "append_new_data")))
    if append_new_data_bool:
        if time_series_points_data:
            time_series_points_data[teams_data_list.index(team)].append([int(chosen_week) + test_week_var, float(team[2])])
        if time_series_efficiency_data:
            if float(team[3].replace("%", "")) != 0.0:
                time_series_efficiency_data[teams_data_list.index(team)].append([int(chosen_week) + test_week_var, float(team[3].replace("%", ""))])
        if time_series_luck_data:
            time_series_luck_data[teams_data_list.index(team)].append([int(chosen_week) + test_week_var, float(team[4].replace("%", ""))])

    # ------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------FOR TESTING ONLY-------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    # test_weeks = 1
    # while test_weeks < 1:
    #     weekly_points_data[teams_data_list.index(team)].append((test_weeks + 1, float(random.uniform(50.0, 150.0))))
    #     weekly_coaching_efficiency_data[teams_data_list.index(team)].append((test_weeks + 1, float(random.uniform(0.0, 100.0))))
    #     weekly_luck_data[teams_data_list.index(team)].append((test_weeks + 1, float(random.uniform(-100.0, 100.0))))
    #     test_weeks += 1
    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------------------

time_series_points_data = load_time_series_data(time_series_points_data, weekly_points_data, time_series_points_data_filename)
time_series_efficiency_data = load_time_series_data(time_series_efficiency_data, weekly_coaching_efficiency_data, time_series_efficiency_data_filename)
time_series_luck_data = load_time_series_data(time_series_luck_data, weekly_luck_data, time_series_luck_data_filename)

# chart_data_list = [ordered_team_names, weekly_points_data, weekly_coaching_efficiency_data, weekly_luck_data]
chart_data_list = [ordered_team_names, time_series_points_data, time_series_efficiency_data, time_series_luck_data]


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == '__main__':

    filename = league_name.replace(" ", "-") + "(" + league_id + ")_week-" + chosen_week + "_report.pdf"
    report_save_dir = config.get("Generated_Report_Settings", "report_directory_base_path") + league_name.replace(" ", "-") + "(" + league_id + ")"
    report_title_text = league_name + " (" + league_id + ") Week " + chosen_week + " Report"
    report_footer_text = "Report generated %s for Yahoo Fantasy Football league '%s' (%s)." % ("{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()), league_name, league_id)

    print "Filename: {}\n".format(filename)

    if not os.path.isdir(report_save_dir):
        os.makedirs(report_save_dir)

    filename_with_path = os.path.join(report_save_dir, filename)

    # instantiate pdf generator
    pdf_generator = PdfGenerator(
        weekly_score_results_data_list,
        coaching_efficiency_results_data_list,
        weekly_luck_results_data_list,
        num_tied_scores,
        num_tied_efficiencies,
        num_tied_luck,
        efficiency_dq_count
    )

    # generate pdf of report
    file_for_upload = pdf_generator.generate_pdf(
        filename_with_path,
        pdf_generator.create_report_title(report_title_text),
        report_footer_text,
        pdf_generator.create_weekly_points_title(),
        pdf_generator.create_weekly_points_table(pdf_generator.create_weekly_points_data(), tied_weekly_score_bool),
        pdf_generator.create_coaching_efficiency_title(),
        pdf_generator.create_coaching_efficiency_table(pdf_generator.create_coaching_efficiency_data(), tied_coaching_efficiency_bool, efficiency_dq_count),
        tied_coaching_efficiency_bool,
        pdf_generator.create_luck_title(),
        pdf_generator.create_weekly_luck_table(pdf_generator.create_luck_data(), tied_weekly_luck_bool),
        tied_weekly_luck_bool,
        chart_data_list
    )

    print "Generated PDF: {}\n".format(file_for_upload)

    upload_file_to_google_drive_bool = bool(distutils.strtobool(config.get("Data_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        # upload pdf to google drive
        google_drive_uploader = GoogleDriveUploader(file_for_upload)
        upload_message = google_drive_uploader.upload_file()

    post_to_slack_bool = bool(distutils.strtobool(config.get("Data_Settings", "post_to_slack")))

    if post_to_slack_bool:
        # post shareable link to uploaded google drive pdf on slack
        if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "making_football_orange_id"):
            slack_messenger = SlackMessenger()
            print slack_messenger.post_to_hg_fantasy_football_channel(upload_message)
            # print slack_messenger.test_on_hg_slack(upload_message)
            print "DONE!"

        else:
            print "{}\n".format(upload_message)
            print "DONE!"
