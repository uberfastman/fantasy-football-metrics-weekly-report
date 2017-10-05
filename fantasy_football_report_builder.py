# Written by: Wren J. Rudolph
# Code snippets taken from: http://tech.thejoestory.com/2014/12/yahoo-fantasy-football-api-using-python.html

import collections
import datetime
import os
from ConfigParser import ConfigParser
from operator import itemgetter

import yql
from yql.storage import FileTokenStore

from pdf_generator import PdfGenerator
from metrics import CoachingEfficiency

# noinspection SqlNoDataSourceInspection,SqlDialectInspection
class FantasyFootballReport(object):
    def __init__(self, user_input_league_id=None, user_input_chosen_week=None):
        # config vars
        self.config = ConfigParser()
        self.config.read("config.ini")
        if user_input_league_id:
            self.league_id = user_input_league_id
        else:
            self.league_id = self.config.get("Fantasy_Football_Report_Settings", "chosen_league_id")

        # verification output message
        print("Generating fantasy football report for league with id: %s (report generated: %s)\n" % (
            self.league_id, "{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now())))

        # yahoo oauth api (consumer) key and secret
        with open("./authentication/private.txt", "r") as auth_file:
            auth_data = auth_file.read().split("\n")
        consumer_key = auth_data[0]
        consumer_secret = auth_data[1]

        # yahoo oauth process
        self.y3 = yql.ThreeLegged(consumer_key, consumer_secret)
        _cache_dir = self.config.get("OAuth_Settings", "yql_cache_dir")
        if not os.access(_cache_dir, os.R_OK):
            os.mkdir(_cache_dir)

        token_store = FileTokenStore(_cache_dir, secret="sasfasdfdasfdaf")
        stored_token = token_store.get("foo")

        if not stored_token:
            request_token, auth_url = self.y3.get_token_and_auth_url()
            print("Visit url %s and get a verifier string" % auth_url)
            verifier = raw_input("Enter the code: ")
            self.token = self.y3.get_access_token(request_token, verifier)
            token_store.set("foo", self.token)

        else:
            print("Verifying token...\n")
            self.token = self.y3.check_token(stored_token)
            if self.token != stored_token:
                print("Setting stored token!\n")
                token_store.set("foo", self.token)

        '''
        run base yql queries
        '''
        # get fantasy football game info
        game_data = self.yql_query("select * from fantasysports.games where game_key='nfl'")
        # unique league key composed of this year's yahoo fantasy football game id and the unique league id
        self.league_key = game_data[0].get("game_key") + ".l." + self.league_id
        print("League key: %s\n" % self.league_key)

        # get individual league roster
        roster_data = self.yql_query(
            "select * from fantasysports.leagues.settings where league_key='" + self.league_key + "'")

        roster_slots = collections.defaultdict(int)
        flex_positions = []

        for position in roster_data[0].get("settings").get("roster_positions").get("roster_position"):

            position_name = position.get("position")
            position_count = int(position.get("count"))

            if position_name == "W/R":
                flex_positions = ['WR", "RB']
            if position_name == "W/R/T":
                flex_positions = ["WR", "RB", "TE"]

            if "/" in position_name:
                position_name = "FLEX"

            roster_slots[position_name] += position_count

        self.roster = {
            "slots": roster_slots,
            "flex_positions": flex_positions
        }

        # get data for all teams in league
        self.teams_data = self.yql_query("select * from fantasysports.teams where league_key='" + self.league_key + "'")

        # get data for all league standings
        self.league_standings_data = self.yql_query(
            "select * from fantasysports.leagues.standings where league_key='" + self.league_key + "'")
        self.league_name = self.league_standings_data[0].get("name")
        # TODO: incorporate winnings into reports
        # entry_fee = league_standings_data[0].get("entry_fee")

        if user_input_chosen_week:
            chosen_week = user_input_chosen_week
        else:
            chosen_week = self.config.get("Fantasy_Football_Report_Settings", "chosen_week")
        try:
            if chosen_week == "default":
                self.chosen_week = str(int(self.league_standings_data[0].get("current_week")) - 1)
                # self.chosen_week = "1"
            elif 0 < int(chosen_week) < 18:
                if 0 < int(chosen_week) <= int(self.league_standings_data[0].get("current_week")) - 1:
                    self.chosen_week = chosen_week
                else:
                    incomplete_week = raw_input("Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                    if incomplete_week == "y":
                        self.chosen_week = chosen_week
                    elif incomplete_week == "n":
                        raise ValueError("It is recommended that you not generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")
            else:
                raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")
        except ValueError:
            raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")

    def yql_query(self, query):
        # print("Executing query: %s\n" % query)
        return self.y3.execute(query, token=self.token).rows

    def retrieve_scoreboard(self, chosen_week):
        """
        get weekly matchup data
        
        result format is like: 
        [
            {
                'team1': { 
                    'result': 'W',
                    'score': 100
                },
                'team2': {
                    'result': 'L',
                    'score': 50
                }
            },
            {
                'team3': {
                    'result': 'T',
                    'score': 75
                },
                'team4': {
                    'result': 'T',
                    'score': 75
                }
            }
        ]
        """
        result = self.yql_query("select * from fantasysports.leagues.scoreboard where league_key='{0}' and week='{1}'".format(self.league_key, chosen_week))

        matchups = result[0].get('scoreboard').get('matchups').get('matchup')

        matchup_list = []

        for matchup in matchups:
            winning_team = matchup.get('winner_team_key')
            is_tied = int(matchup.get('is_tied'))

            def team_result(team):
                """
                determine if team tied/won/lost
                """
                team_key = team.get('team_key')

                if is_tied:
                    return 'T'

                return 'W' if team_key == winning_team else 'L'

            teams = { 
                team.get('name').encode('utf-8'): {
                    'result': team_result(team),
                    'score': team.get('team_points').get('total')
                } for team in matchup.get('teams').get('team') 
            }

            matchup_list.append(teams)

        return matchup_list
        

    def retrieve_data(self, chosen_week):
                
        teams_dict = {}
        for team in self.teams_data:

            team_id = team.get("team_id")
            team_name = team.get("name")
            team_managers = team.get("managers").get("manager")

            team_manager = ""
            if type(team_managers) is dict:
                team_manager = team_managers.get("nickname")
            else:
                for manager in team_managers:
                    if manager.get("is_comanager") is None:
                        team_manager = manager.get("nickname")

            team_info_dict = {"name": team_name, "manager": team_manager}
            teams_dict[team_id] = team_info_dict

        # output league teams for verification
        if chosen_week == "1":
            print("TEAMS: {}\n".format(teams_dict))
            print("Generating report for week {}\n".format(self.chosen_week))

        team_results_dict = {}

        # iterate through all teams and build team_results_dict containing all relevant team stat information
        for team in teams_dict:

            team_id = team
            team_name = teams_dict.get(team).get("name").encode("utf-8")
            team_info_dict = teams_dict.get(team)

            # get data for this individual team
            roster_stats_data = self.yql_query(
                "select * from fantasysports.teams.roster.stats where team_key='" + self.league_key + ".t." + team + "' and week='" + chosen_week + "'")

            players = []

            for player in roster_stats_data[0].get("roster").get("players").get("player"):
                player_info_dict = {}
                player_info_dict["name"] = player.get("name")["full"]
                player_info_dict["status"] = player.get("status")
                player_info_dict["bye_week"] = int(player.get("bye_weeks")["week"])
                player_info_dict["selected_position"] = player.get("selected_position").get("position")
                player_info_dict["eligible_positions"]  = player.get("eligible_positions").get("position")
                player_info_dict["fantasy_points"] = float(player.get("player_points").get("total", 0.0))

                players.append(player_info_dict)

            team_results_dict[team_name] = {
                "manager": teams_dict.get(team).get("manager"),
                "players": players,
                "weekly_score": sum([p['fantasy_points'] for p in players if p['selected_position'] != 'BN']),
                "team_id": team_id
            }

        return team_results_dict

    def calculate_metrics(self, chosen_week):

        matchups_list = self.retrieve_scoreboard(chosen_week)

        team_results_dict = self.retrieve_data(chosen_week)

        coaching_efficiency = CoachingEfficiency(self.roster)

        for name, team in team_results_dict.items():
            disqualification_eligible = self.league_id == self.config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id")
            team['coaching_efficiency'] = coaching_efficiency.execute(team, int(chosen_week), disqualification_eligible=disqualification_eligible)

        final_weekly_score_results_list = sorted(team_results_dict.iteritems(),
                                                 key=lambda (k, v): (float(v.get("weekly_score")), k))[::-1]

        weekly_score_results_data_list = []
        place = 1
        for key, value in final_weekly_score_results_list:
            ranked_team_name = key
            ranked_team_manager = value.get("manager")
            ranked_weekly_score = value.get("weekly_score")

            weekly_score_results_data_list.append([place, ranked_team_name, ranked_team_manager, ranked_weekly_score])

            place += 1

        ranked_team_scores = []

        for result in weekly_score_results_data_list:
            ranked_team_name = result[1]
            ranked_weekly_score = result[3]

            ranked_team = {"name": ranked_team_name, "score": ranked_weekly_score, "luck": ""}
            ranked_team_scores.append(ranked_team)

        # set team matchup results for this week
        team_matchup_result_dict = { name: value['result'] for pair in matchups_list for name, value in pair.items() }
        
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

                    luck += (
                        ((sum(score.get("score") >= ranked_team_score for score in ranked_team_score_without_team)) / (
                            float(len(ranked_team_score_without_team)))) * 100)
                else:
                    luck += (
                        ((0 - sum(
                            score.get("score") <= ranked_team_score for score in ranked_team_score_without_team)) / (
                             float(len(ranked_team_score_without_team)))) * 100)

                ranked_team["luck"] = luck

            ranked_team["matchup_result"] = ranked_team_matchup_result

            results.append(ranked_team)
            index += 1

            team_results_dict.get(ranked_team_name)["luck"] = "%.2f%%" % luck
            team_results_dict.get(ranked_team_name)["matchup_result"] = ranked_team_matchup_result

        results.sort(key=lambda x: x.get("luck"), reverse=True)

        final_coaching_efficiency_results_list = sorted(team_results_dict.iteritems(),
                                                        key=lambda (k, v): (
                                                            v.get("coaching_efficiency"), k))[
                                                 ::-1]
        final_luck_results_list = sorted(team_results_dict.iteritems(),
                                         key=lambda (k, v): (float(v.get("luck").strip("%")), k))[::-1]

        # create data for coaching efficiency table
        coaching_efficiency_results_data_list = []
        efficiency_dq_count = 0
        place = 1
        for key, value in final_coaching_efficiency_results_list:
            ranked_team_name = key
            ranked_team_manager = value.get("manager")
            ranked_coaching_efficiency = value.get("coaching_efficiency")

            if ranked_coaching_efficiency == 0.0:
                ranked_coaching_efficiency = "DQ"
                efficiency_dq_count += 1

            coaching_efficiency_results_data_list.append(
                [place, ranked_team_name, ranked_team_manager, "%.2f%%" % ranked_coaching_efficiency])

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
        num_tied_scores = sum(
            manager.count(weekly_score_results_data_list[0][3]) for manager in weekly_score_results_data_list)
        num_tied_efficiencies = sum(
            manager.count(coaching_efficiency_results_data_list[0][3]) for manager in
            coaching_efficiency_results_data_list)
        num_tied_luck = sum(
            manager.count(weekly_luck_results_data_list[0][3]) for manager in weekly_luck_results_data_list)

        # if there are ties, record them and break them if possible
        tied_weekly_score_bool = False
        if num_tied_scores > 1:
            print("THERE IS A WEEKLY SCORE TIE IN WEEK %s!" % chosen_week)
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
                    tied_scores_list[index][1].get("weekly_score") + " (bench score: " + tied_scores_list[index][1].get(
                        "bench_score") + ")"
                ]
                count -= 1
                index += 1
        else:
            print("No weekly score ties in week %s." % chosen_week)

        tied_coaching_efficiency_bool = False
        if num_tied_efficiencies > 1:
            print("THERE IS A COACHING EFFICIENCY TIE IN WEEK %s!" % chosen_week)
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
            print("No coaching efficiency ties in week %s." % chosen_week)

        tied_weekly_luck_bool = False
        if num_tied_luck > 1:
            print("THERE IS A LUCK TIE IN WEEK %s!" % chosen_week)
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
            print("No luck ties in week %s.\n" % chosen_week)

        # last minute formatting of scores to rounded score
        for team in weekly_score_results_data_list:
            team[3] = "%.2f" % team[3]

        report_info_dict = {
            "weekly_score_results_data_list": weekly_score_results_data_list,
            "coaching_efficiency_results_data_list": coaching_efficiency_results_data_list,
            "weekly_luck_results_data_list": weekly_luck_results_data_list,
            "num_tied_scores": num_tied_scores,
            "num_tied_efficiencies": num_tied_efficiencies,
            "num_tied_luck": num_tied_luck,
            "efficiency_dq_count": efficiency_dq_count,
            "tied_weekly_score_bool": tied_weekly_score_bool,
            "tied_coaching_efficiency_bool": tied_coaching_efficiency_bool,
            "tied_weekly_luck_bool": tied_weekly_luck_bool
        }
        return team_results_dict, report_info_dict

    def create_pdf_report(self):

        chosen_week_ordered_team_names = []
        chosen_week_report_info_dict = {}

        time_series_points_data = []
        time_series_efficiency_data = []
        time_series_luck_data = []

        week_counter = 1
        while week_counter <= int(self.chosen_week):
            calculated_metrics_results = self.calculate_metrics(chosen_week=str(week_counter))
            team_results_dict = calculated_metrics_results[0]
            report_info_dict = calculated_metrics_results[1]

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

            ordered_team_names = []
            weekly_points_data = []
            weekly_coaching_efficiency_data = []
            weekly_luck_data = []

            for team in teams_data_list:
                ordered_team_names.append(team[1])
                weekly_points_data.append([int(week_counter), float(team[2])])
                weekly_coaching_efficiency_data.append([int(week_counter), team[3]])
                weekly_luck_data.append([int(week_counter), float(team[4].replace("%", ""))])

            chosen_week_ordered_team_names = ordered_team_names
            chosen_week_report_info_dict = report_info_dict

            if week_counter == 1:
                for team_points in weekly_points_data:
                    time_series_points_data.append([team_points])
                for team_efficiency in weekly_coaching_efficiency_data:
                    time_series_efficiency_data.append([team_efficiency])
                for team_luck in weekly_luck_data:
                    time_series_luck_data.append([team_luck])
            else:
                for team_points in weekly_points_data:
                    time_series_points_data[weekly_points_data.index(team_points)].append(team_points)
                for team_efficiency in weekly_coaching_efficiency_data:
                    time_series_efficiency_data[weekly_coaching_efficiency_data.index(team_efficiency)].append(
                        team_efficiency)
                for team_luck in weekly_luck_data:
                    time_series_luck_data[weekly_luck_data.index(team_luck)].append(team_luck)
            week_counter += 1

        chart_data_list = [chosen_week_ordered_team_names, time_series_points_data, time_series_efficiency_data,
                           time_series_luck_data]

        filename = self.league_name.replace(" ",
                                            "-") + "(" + self.league_id + ")_week-" + self.chosen_week + "_report.pdf"
        report_save_dir = self.config.get("Fantasy_Football_Report_Settings",
                                          "report_directory_base_path") + "/" + self.league_name.replace(" ",
                                                                                                         "-") + "(" + self.league_id + ")"
        report_title_text = self.league_name + " (" + self.league_id + ") Week " + self.chosen_week + " Report"
        report_footer_text = "Report generated %s for Yahoo Fantasy Football league '%s' (%s)." % (
            "{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()), self.league_name, self.league_id)

        print("Filename: {}\n".format(filename))

        if not os.path.isdir(report_save_dir):
            os.makedirs(report_save_dir)

        filename_with_path = os.path.join(report_save_dir, filename)

        # instantiate pdf generator
        pdf_generator = PdfGenerator(
            chosen_week_report_info_dict.get("weekly_score_results_data_list"),
            chosen_week_report_info_dict.get("coaching_efficiency_results_data_list"),
            chosen_week_report_info_dict.get("weekly_luck_results_data_list"),
            chosen_week_report_info_dict.get("num_tied_scores"),
            chosen_week_report_info_dict.get("num_tied_efficiencies"),
            chosen_week_report_info_dict.get("num_tied_luck"),
            chosen_week_report_info_dict.get("efficiency_dq_count")
        )

        # generate pdf of report
        file_for_upload = pdf_generator.generate_pdf(
            filename_with_path,
            pdf_generator.create_report_title(report_title_text),
            report_footer_text,
            pdf_generator.create_weekly_points_title(),
            pdf_generator.create_weekly_points_table(pdf_generator.create_weekly_points_data(),
                                                     chosen_week_report_info_dict.get("tied_weekly_score_bool")),
            pdf_generator.create_coaching_efficiency_title(),
            pdf_generator.create_coaching_efficiency_table(pdf_generator.create_coaching_efficiency_data(),
                                                           chosen_week_report_info_dict.get(
                                                               "tied_coaching_efficiency_bool"),
                                                           chosen_week_report_info_dict.get("efficiency_dq_count")),
            chosen_week_report_info_dict.get("tied_coaching_efficiency_bool"),
            pdf_generator.create_luck_title(),
            pdf_generator.create_weekly_luck_table(pdf_generator.create_luck_data(),
                                                   chosen_week_report_info_dict.get("tied_weekly_luck_bool")),
            chosen_week_report_info_dict.get("tied_weekly_luck_bool"),
            self.league_id,
            chart_data_list
        )

        print("Generated PDF: {}\n".format(file_for_upload))

        return file_for_upload
