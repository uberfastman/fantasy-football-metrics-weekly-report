# written by Wren J.R.
# contributors: Kevin N., Joe M.
# code snippets taken from: http://tech.thejoestory.com/2014/12/yahoo-fantasy-football-api-using-python.html

import collections
import datetime
import itertools
import logging
import os
import sys
from configparser import ConfigParser

from yffpy import Data
from yffpy.models import Game, League, Standings, Settings
from yffpy.query import YahooFantasyFootballQuery

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.breakdown import Breakdown
from calculate.metrics import CalculateMetrics
from calculate.playoff_probabilities import PlayoffProbabilities
from calculate.points_by_position import PointsByPosition
from calculate.power_ranking import PowerRanking
from calculate.season_averages import SeasonAverageCalculator
from calculate.z_score import ZScore
from report.pdf.pdf_generator import PdfGenerator

logger = logging.getLogger(__name__)
# Suppress YahooFantasyFootballQuery debug logging
logging.getLogger("yffpy.query").setLevel(level=logging.INFO)


class FantasyFootballReport(object):
    def __init__(self,
                 league_id=None,
                 week=None,
                 dq_ce_bool=False,
                 break_ties_bool=False,
                 test_bool=False,
                 save_data=False,
                 dev_offline=False):

        # config vars
        self.config = ConfigParser()
        self.config.read("config.ini")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.yahoo_auth_dir = os.path.join(base_dir, "..", self.config.get("Yahoo_Settings", "yahoo_auth_dir"))
        self.data_dir = os.path.join(base_dir, "..", self.config.get("Fantasy_Football_Report_Settings", "data_dir"))
        self.game_id = self.config.get("Fantasy_Football_Report_Settings", "game_id")
        self.season = self.config.get("Fantasy_Football_Report_Settings", "season")
        if league_id:
            self.league_id = league_id
        else:
            self.league_id = self.config.get("Fantasy_Football_Report_Settings", "league_id")

        self.dq_ce_bool = dq_ce_bool
        self.break_ties_bool = break_ties_bool

        self.test_bool = test_bool

        self.save_data = save_data
        self.dev_offline = dev_offline

        # verification output message
        logger.info("\nGenerating%s fantasy football report for league with id: %s on %s..." % (
            " TEST" if test_bool else "", self.league_id, "{:%b %d, %Y}".format(datetime.datetime.now())))

        # set up yahoo data obj
        yahoo_data = Data(self.data_dir, save_data=self.save_data, dev_offline=self.dev_offline)

        # run base yahoo queries
        yahoo_query = YahooFantasyFootballQuery(self.yahoo_auth_dir, self.league_id, self.game_id, offline=self.dev_offline)

        # TODO: REMOVE LEAGUE KEY OVERRIDE
        # yahoo_query.league_key = "380.l.169896"

        if self.season and self.game_id:
            self.yahoo_fantasy_game = yahoo_data.retrieve(str(self.game_id) + "-yahoo_nfl_fantasy_game",
                                                          yahoo_query.get_nfl_fantasy_game,
                                                          params={"game_id": self.game_id}, data_type_class=Game,
                                                          new_data_dir=os.path.join(self.data_dir, str(self.season)))
        else:
            self.yahoo_fantasy_game = yahoo_data.retrieve(str(self.game_id) + "-yahoo_nfl_fantasy_game",
                                                          yahoo_query.get_current_nfl_fantasy_game,
                                                          data_type_class=Game,
                                                          new_data_dir=os.path.join(self.data_dir, str(self.season)))

        self.league_key = self.yahoo_fantasy_game.game_key + ".l." + self.league_id
        self.season = self.yahoo_fantasy_game.season

        # print(self.league_key)
        # sys.exit()

        league_overview = yahoo_data.retrieve("overview", yahoo_query.get_overview, data_type_class=League,
                                              new_data_dir=os.path.join(self.data_dir, str(self.season),
                                                                        self.league_key))
        self.league_name = league_overview.name

        # print(self.league_name)
        # print(league_overview)
        # sys.exit()

        self.league_standings_data = yahoo_data.retrieve("standings", yahoo_query.get_standings,
                                                         data_type_class=Standings,
                                                         new_data_dir=os.path.join(self.data_dir, str(self.season),
                                                                                   self.league_key))
        # print(self.league_standings_data)
        # sys.exit()

        self.teams_data = yahoo_data.retrieve("teams", yahoo_query.get_teams,
                                              new_data_dir=os.path.join(self.data_dir, str(self.season),
                                                                        self.league_key))
        # print(self.teams_data)
        # sys.exit()

        league_settings = yahoo_data.retrieve("settings", yahoo_query.get_settings, data_type_class=Settings,
                                              new_data_dir=os.path.join(self.data_dir, str(self.season),
                                                                        self.league_key))
        # print(league_settings)
        # sys.exit()

        self.playoff_slots = league_settings.num_playoff_teams
        self.num_regular_season_weeks = int(league_settings.playoff_start_week) - 1
        # print(self.playoff_slots)
        # print(self.num_regular_season_weeks)
        # sys.exit()

        roster_slots = collections.defaultdict(int)
        self.league_roster_active_slots = []
        flex_positions = []
        for roster_position in league_settings.roster_positions:

            roster_position = roster_position.get("roster_position")

            position_name = roster_position.position
            position_count = int(roster_position.count)

            count = position_count
            while count > 0:
                if position_name != "BN":
                    self.league_roster_active_slots.append(position_name)
                count -= 1

            if position_name == "W/R":
                flex_positions = ["WR", "RB"]
            if position_name == "W/R/T":
                flex_positions = ["WR", "RB", "TE"]

            if "/" in position_name:
                position_name = "FLEX"

            roster_slots[position_name] += position_count

        self.roster = {
            "slots": roster_slots,
            "flex_positions": flex_positions
        }

        # print(self.roster)
        # sys.exit()

        self.bad_boy_stats = BadBoyStats(os.path.join(self.data_dir, str(self.season), self.league_key),
                                         save_data=self.save_data, dev_offline=self.dev_offline)
        # print(self.bad_boy_stats)
        # sys.exit()

        self.beef_rank = BeefStats(os.path.join(self.data_dir, str(self.season), self.league_key),
                                   save_data=self.save_data, dev_offline=self.dev_offline)

        # print(self.beef_rank)
        # sys.exit()

        # TODO: UPDATE USAGE OF recalculate PARAM (could use self.dev_offline)
        self.playoff_probs_data = PlayoffProbabilities(
            self.config.getint("Fantasy_Football_Report_Settings", "num_playoff_simulations"),
            self.num_regular_season_weeks,
            self.playoff_slots,
            data_dir=os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=self.save_data,
            recalculate=True
        )
        # print(self.playoff_probs_data)
        # sys.exit()

        # user input validation
        if week:
            chosen_week = week
        else:
            chosen_week = self.config.get("Fantasy_Football_Report_Settings", "chosen_week")
        try:
            current_week = league_overview.current_week
            if chosen_week == "default":
                if (int(current_week) - 1) > 0:
                    self.chosen_week = str(int(current_week) - 1)
                else:
                    first_week_incomplete = input(
                        "The first week of the season is not yet complete. "
                        "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                    if first_week_incomplete == "y":
                        self.chosen_week = current_week
                    elif first_week_incomplete == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")

            elif 0 < int(chosen_week) < 18:
                if 0 < int(chosen_week) <= int(current_week) - 1:
                    self.chosen_week = chosen_week
                else:
                    incomplete_week = input(
                        "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                    if incomplete_week == "y":
                        self.chosen_week = chosen_week
                    elif incomplete_week == "n":
                        raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                    else:
                        raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")
            else:
                raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")
        except ValueError:
            raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")

        # run yahoo queries requiring chosen week
        self.matchups = {}
        for wk in range(1, self.num_regular_season_weeks + 1):
            self.matchups[wk] = yahoo_data.retrieve("matchups", yahoo_query.get_matchups, params={"chosen_week": wk},
                                                    new_data_dir=os.path.join(self.data_dir, str(self.season),
                                                                              self.league_key, "week_" + str(wk)))
        # print(self.matchups)
        # sys.exit()

        self.rosters = {}
        for wk in range(1, int(self.chosen_week) + 1):
            self.rosters[str(wk)] = {
                str(team.get("team").team_id):
                    yahoo_data.retrieve(
                        str(team.get("team").team_id) + "-" + str(team.get("team").name.decode("utf-8")).replace(" ",
                                                                                                                 "_"),
                        yahoo_query.get_team_roster,
                        params={"team_id": str(team.get("team").team_id), "chosen_week": str(wk)},
                        new_data_dir=os.path.join(
                            self.data_dir, str(self.season), self.league_key, "week_" + str(wk), "rosters")
                    ) for team in self.teams_data.values()
            }
        # print(self.rosters.keys())
        # sys.exit()

        # output league info for verification
        logger.info("...setup complete for \"{}\" ({}) week {} report.\n".format(self.league_name.upper(),
                                                                                 self.league_id,
                                                                                 self.chosen_week))

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
                }371.l.52364
            }
        ]
        """

        matchups = self.matchups.get(int(chosen_week))
        matchup_list = []
        for matchup in matchups.values():

            matchup = matchup.get("matchup")
            if matchup.status == "postevent":
                winning_team = matchup.winner_team_key
                is_tied = int(matchup.is_tied) if matchup.is_tied else 0
            elif matchup.status == "midevent":
                winning_team = ""
                is_tied = 1
            else:
                winning_team = ""
                is_tied = 0

            teams = {}
            for team in matchup.teams.values():
                team = team.get("team")
                teams[team.name] = {
                    "result": "T" if is_tied else "W" if team.team_key == winning_team else "L",
                    "score": team.team_points.total
                }

            matchup_list.append(teams)
        return matchup_list

    def retrieve_data(self, chosen_week):

        teams_dict = {}
        for team in self.teams_data.values():

            team = team.get("team")

            team_id = team.team_id
            team_name = team.name

            if isinstance(team.managers, list):
                team_manager = ", ".join([manager.get("manager").nickname for manager in team.managers])
            else:
                team_manager = team.managers.get("manager").nickname

            team_info_dict = {"name": team_name, "manager": team_manager}
            teams_dict[team_id] = team_info_dict

        team_results_dict = {}

        # iterate through all teams and build team_results_dict containing all relevant team stat information
        for team_id, team_info in teams_dict.items():

            team_name = team_info["name"]

            players = []
            positions_filled_active = []
            for player in self.rosters[chosen_week].get(team_id).values():

                player = player.get("player")

                custom_field_dict = {"bad_boy_crime": str, "bad_boy_points": int, "weight": float, "tabbu": float}
                player._keys.extend(list(custom_field_dict.keys()))
                for field, data_type in custom_field_dict.items():
                    player.__dict__[field] = data_type()

                if player.selected_position.position != "BN":
                    player.bad_boy_points, player.bad_boy_crime = self.bad_boy_stats.check_bad_boy_status(
                        player.name.full, player.editorial_team_abbr, player.selected_position.position)
                    player.weight = self.beef_rank.get_player_weight(player.name.first, player.name.last,
                                                                     player.editorial_team_abbr)
                    player.tabbu = self.beef_rank.get_player_tabbu(player.name.first, player.name.last,
                                                                   player.editorial_team_abbr)
                    positions_filled_active.append(player.selected_position.position)

                players.append(player)

            team_name = team_name.decode("utf-8")
            bad_boy_total = 0
            worst_offense = ""
            worst_offense_score = 0
            num_offenders = 0
            for p in players:
                if p.selected_position.position != "BN":
                    bad_boy_total = bad_boy_total + p.bad_boy_points
                    if p.bad_boy_points > 0:
                        num_offenders = num_offenders + 1
                        if p.bad_boy_points > worst_offense_score:
                            worst_offense = p.bad_boy_crime
                            worst_offense_score = p.bad_boy_points

            team_results_dict[team_name] = {
                "name": team_name,
                "manager": teams_dict[team_id]["manager"],
                "players": players,
                "score": sum([p.player_points.total for p in players if p.selected_position.position != "BN"]),
                "bench_score": sum([p.player_points.total for p in players if p.selected_position.position == "BN"]),
                "team_id": team_id,
                "bad_boy_points": bad_boy_total,
                "worst_offense": worst_offense,
                "num_offenders": num_offenders,
                "total_weight": sum([p.weight for p in players if p.selected_position.position != "BN"]),
                "tabbu": sum([p.tabbu for p in players if p.selected_position.position != "BN"]),
                "positions_filled_active": positions_filled_active
            }

        return team_results_dict

    def calculate_metrics(self, weekly_team_info, week, chosen_week):

        matchups_list = self.retrieve_scoreboard(week)
        team_results_dict = self.retrieve_data(week)

        # get current standings
        calc_metrics = CalculateMetrics(self.config, self.league_id, self.playoff_slots)

        # calculate coaching efficiency metric and add values to team_results_dict, and get points by position
        points_by_position = PointsByPosition(self.roster, self.chosen_week)
        weekly_points_by_position_data = \
            points_by_position.get_weekly_points_by_position(self.dq_ce_bool, self.config, week,
                                                             self.roster, self.league_roster_active_slots,
                                                             team_results_dict)

        # calculate luck metric and add values to team_results_dict
        breakdown = Breakdown()
        breakdown_results = breakdown.execute_breakdown(team_results_dict, matchups_list)

        # yes, this is kind of redundant but its clearer that the individual metrics
        # are _not_ supposed to be modifying the things passed into it
        for team_id in team_results_dict:
            team_results_dict[team_id]["luck"] = breakdown_results[team_id]["luck"] * 100
            team_results_dict[team_id]["breakdown"] = breakdown_results[team_id]["breakdown"]

        # dependent on all previous weeks scores
        zscore = ZScore(weekly_team_info + [team_results_dict])
        zscore_results = zscore.execute()

        for team_id in team_results_dict:
            team_results_dict[team_id]["zscore"] = zscore_results[team_id]

        power_ranking_metric = PowerRanking()
        power_ranking_results = power_ranking_metric.execute_power_ranking(team_results_dict)

        for team_id in team_results_dict:
            team_results_dict[team_id]["power_rank"] = power_ranking_results[team_id]["power_rank"]
            team_results_dict[team_id]["zscore_rank"] = power_ranking_results[team_id]["zscore_rank"]

        # used only for testing what happens when different metrics are tied; requires uncommenting lines in method
        if self.test_bool:
            calc_metrics.test_ties(team_results_dict)

        for key in team_results_dict:
            try:
                st = team_results_dict[key]  # .decode('utf-8')
                team_results_dict[key] = st
            except AttributeError:
                pass

        # create score data for table
        score_results = sorted(iter(team_results_dict.items()),
                               key=lambda k_v: (float(k_v[1].get("score")), k_v[0]), reverse=True)
        score_results_data = calc_metrics.get_score_data(score_results)

        current_standings_data = calc_metrics.get_standings(self.league_standings_data)

        # create playoff probabilities data for table
        remaining_matchups = {
            int(week): [
                (
                    matchup.get("matchup").teams["0"].get("team").team_id,
                    matchup.get("matchup").teams["1"].get("team").team_id

                ) for matchup in matchups.values()
            ] for week, matchups in self.matchups.items() if int(week) != int(chosen_week)
        }

        playoff_probs_data = self.playoff_probs_data.calculate(week, chosen_week, calc_metrics.teams_info,
                                                               remaining_matchups)

        if playoff_probs_data:
            playoff_probs_data = calc_metrics.get_playoff_probs_data(
                self.league_standings_data,
                playoff_probs_data
            )
        else:
            playoff_probs_data = None

        # create coaching efficiency data for table
        coaching_efficiency_results = sorted(iter(team_results_dict.items()),
                                             key=lambda k_v: (k_v[1].get("coaching_efficiency"), k_v[0]), reverse=True)
        coaching_efficiency_results_data = calc_metrics.get_coaching_efficiency_data(
            coaching_efficiency_results)
        efficiency_dq_count = calc_metrics.coaching_efficiency_dq_count

        # create luck data for table
        luck_results = sorted(iter(team_results_dict.items()),
                              key=lambda k_v: (k_v[1].get("luck"), k_v[0]), reverse=True)
        luck_results_data = calc_metrics.get_luck_data(luck_results)

        # create power ranking data for table
        power_ranking_results = sorted(iter(list(team_results_dict.items())), key=lambda k_v: k_v[1]["power_rank"])
        power_ranking_results_data = []
        for key, value in power_ranking_results:
            # season avg calc does something where it _keys off the second value in the array
            power_ranking_results_data.append(
                [value.get("power_rank"), key, value.get("manager")]
            )

        # create zscore data for table
        zscore_results = sorted(iter(list(team_results_dict.items())),
                                key=lambda k_v: (k_v[1].get("zscore_rank"), k_v[0]))

        zscore_results_data = []
        for key, value in zscore_results:
            zscore = value.get("zscore", None)
            zscore_rank = value.get("zscore_rank", "N/A")
            if zscore:
                zscore = round(float(zscore), 2)
            else:
                zscore = "N/A"
            zscore_results_data.append([zscore_rank, key, value.get("manager"), zscore])

        # create bad boy data for table
        bad_boy_results = sorted(iter(team_results_dict.items()),
                                 key=lambda k_v: (float(k_v[1].get("bad_boy_points")), k_v[0]), reverse=True)
        bad_boy_results_data = calc_metrics.get_bad_boy_data(bad_boy_results)

        # create beef rank data for table
        beef_results = sorted(iter(team_results_dict.items()),
                              key=lambda k_v: (float(k_v[1].get("tabbu")), k_v[0]), reverse=True)
        beef_results_data = calc_metrics.get_beef_rank_data(beef_results)

        # count number of ties for points, coaching efficiency, luck, power ranking, or bad boy ranking
        # tie_type can be "score", "coaching_efficiency", "luck", "power_rank", or "bad_boy"

        num_tied_scores = calc_metrics.get_num_ties(score_results_data, "score", self.break_ties_bool)
        # reorder score data based on bench points
        if num_tied_scores > 0:
            score_results_data = calc_metrics.resolve_score_ties(score_results_data, self.break_ties_bool)
            calc_metrics.get_num_ties(score_results_data, "score", self.break_ties_bool)
        tie_for_first_score = False
        if score_results_data[0][0] == score_results_data[1][0]:
            tie_for_first_score = True
        num_tied_for_first_scores = len(
            [list(group) for key, group in itertools.groupby(score_results_data, lambda x: x[3])][0])

        num_tied_coaching_efficiencies = calc_metrics.get_num_ties(coaching_efficiency_results_data,
                                                                   "coaching_efficiency", self.break_ties_bool)
        tie_for_first_coaching_efficiency = False
        if coaching_efficiency_results_data[0][0] == coaching_efficiency_results_data[1][0]:
            tie_for_first_coaching_efficiency = True
        num_tied_for_first_coaching_efficiency = len(
            [list(group) for key, group in itertools.groupby(coaching_efficiency_results_data, lambda x: x[3])][0])

        num_tied_lucks = calc_metrics.get_num_ties(luck_results_data, "luck", self.break_ties_bool)
        tie_for_first_luck = False
        if luck_results_data[0][0] == luck_results_data[1][0]:
            tie_for_first_luck = True
        num_tied_for_first_luck = len(
            [list(group) for key, group in itertools.groupby(luck_results_data, lambda x: x[3])][0])

        num_tied_power_rankings = calc_metrics.get_num_ties(power_ranking_results_data, "power_rank",
                                                            self.break_ties_bool)
        tie_for_first_power_ranking = False
        if power_ranking_results_data[0][0] == power_ranking_results_data[1][0]:
            tie_for_first_power_ranking = True
        num_tied_for_first_power_ranking = len(
            [list(group) for key, group in itertools.groupby(power_ranking_results_data, lambda x: x[0])][0])

        num_tied_bad_boys = calc_metrics.get_num_ties(bad_boy_results_data, "bad_boy", self.break_ties_bool)

        tie_for_first_bad_boy = False
        if num_tied_bad_boys > 0:
            if bad_boy_results_data[0][0] == bad_boy_results_data[1][0]:
                tie_for_first_bad_boy = True
        num_tied_for_first_bad_boy = len(
            [list(group) for key, group in itertools.groupby(bad_boy_results_data, lambda x: x[3])][0])

        num_tied_beef = calc_metrics.get_num_ties(beef_results_data, "beef", self.break_ties_bool)

        tie_for_first_beef = False
        if num_tied_beef > 0:
            if beef_results_data[0][0] == beef_results_data[1][0]:
                tie_for_first_beef = True
        num_tied_for_first_beef = len(
            [list(group) for key, group in itertools.groupby(beef_results_data, lambda x: x[3])][0])

        # output weekly metrics info
        logger.info("\n~~~~~ WEEK {} METRICS INFO ~~~~~\n"
                    "              SCORE tie(s): {}\n"
                    "COACHING EFFICIENCY tie(s): {}\n"
                    "               LUCK tie(s): {}\n".format(week, num_tied_scores, num_tied_coaching_efficiencies,
                                                              num_tied_lucks))

        coaching_efficiency_dq_dict = points_by_position.coaching_efficiency_dq_dict
        if coaching_efficiency_dq_dict:
            ce_dq_str = ""
            for team in list(coaching_efficiency_dq_dict.keys()):
                if coaching_efficiency_dq_dict.get(team) == -1:
                    ce_dq_str += "{} (incomplete active squad), ".format(team)
                else:
                    ce_dq_str += "{} (ineligible bench players: {}/{}), ".format(team,
                                                                                 coaching_efficiency_dq_dict.get(team),
                                                                                 self.roster.get("slots").get("BN"))
            logger.info("   COACHING EFFICIENCY DQs: {}\n".format(ce_dq_str[:-2]))
        else:
            logger.info("")

        report_info_dict = {
            "team_results": team_results_dict,
            "current_standings_data": current_standings_data,
            "playoff_probs_data": playoff_probs_data,
            "score_results_data": score_results_data,
            "coaching_efficiency_results_data": coaching_efficiency_results_data,
            "luck_results_data": luck_results_data,
            "power_ranking_results_data": power_ranking_results_data,
            "zscore_results_data": zscore_results_data,
            "bad_boy_results_data": bad_boy_results_data,
            "beef_results_data": beef_results_data,
            "num_tied_scores": num_tied_scores,
            "num_tied_coaching_efficiencies": num_tied_coaching_efficiencies,
            "num_tied_lucks": num_tied_lucks,
            "num_tied_power_rankings": num_tied_power_rankings,
            "num_tied_bad_boys": num_tied_bad_boys,
            "num_tied_beef": num_tied_beef,
            "efficiency_dq_count": efficiency_dq_count,
            "tied_scores_bool": num_tied_scores > 0,
            "tied_coaching_efficiencies_bool": num_tied_coaching_efficiencies > 0,
            "tied_lucks_bool": num_tied_lucks > 0,
            "tied_power_rankings_bool": num_tied_power_rankings > 0,
            "tied_bad_boy_bool": num_tied_bad_boys > 0,
            "tied_beef_bool": num_tied_beef > 0,
            "tie_for_first_score": tie_for_first_score,
            "tie_for_first_coaching_efficiency": tie_for_first_coaching_efficiency,
            "tie_for_first_luck": tie_for_first_luck,
            "tie_for_first_power_ranking": tie_for_first_power_ranking,
            "tie_for_first_bad_boy": tie_for_first_bad_boy,
            "tie_for_first_beef": tie_for_first_beef,
            "num_tied_for_first_scores": num_tied_for_first_scores,
            "num_tied_for_first_coaching_efficiency": num_tied_for_first_coaching_efficiency,
            "num_tied_for_first_luck": num_tied_for_first_luck,
            "num_tied_for_first_power_ranking": num_tied_for_first_power_ranking,
            "num_tied_for_first_bad_boy": num_tied_for_first_bad_boy,
            "num_tied_for_first_beef": num_tied_for_first_beef,
            "weekly_points_by_position_data": weekly_points_by_position_data
        }

        return report_info_dict

    def create_pdf_report(self):

        chosen_week_ordered_team_names = []
        chosen_week_ordered_managers = []
        report_info_dict = {}

        weekly_team_info = []

        time_series_points_data = []
        time_series_efficiency_data = []
        time_series_luck_data = []
        time_series_power_rank_data = []
        time_series_zscore_data = []

        weekly_top_scores = []

        season_average_points_by_position_dict = collections.defaultdict(list)

        week_counter = 1
        while week_counter <= int(self.chosen_week):
            report_info_dict = self.calculate_metrics(weekly_team_info,
                                                      week=str(week_counter),
                                                      chosen_week=self.chosen_week)

            top_scorer = {
                "week": week_counter,
                "team": report_info_dict.get("score_results_data")[0][1],
                "manager": report_info_dict.get("score_results_data")[0][2],
                "score": report_info_dict.get("score_results_data")[0][3]
            }
            weekly_top_scores.append(top_scorer)

            weekly_team_info.append(report_info_dict.get("team_results"))

            # create team data for charts
            teams_data_list = []
            team_results = report_info_dict.get("team_results")
            for team in team_results:
                temp_team_info = team_results.get(team)
                teams_data_list.append([
                    temp_team_info.get("team_id"),
                    team,
                    temp_team_info.get("manager"),
                    temp_team_info.get("score"),
                    temp_team_info.get("coaching_efficiency"),
                    temp_team_info.get("luck"),
                    temp_team_info.get("power_rank"),
                    temp_team_info.get("zscore")
                ])

                points_by_position = report_info_dict.get("weekly_points_by_position_data")
                for weekly_info in points_by_position:
                    if weekly_info[0] == team:
                        season_average_points_by_position_dict[team].append(weekly_info[1])

            teams_data_list.sort(key=lambda x: int(x[0]))

            ordered_team_names = []
            ordered_team_managers = []
            weekly_points_data = []
            weekly_coaching_efficiency_data = []
            weekly_luck_data = []
            weekly_power_rank_data = []
            weekly_zscore_data = []

            for team in teams_data_list:
                ordered_team_names.append(team[1])
                ordered_team_managers.append(team[2])
                weekly_points_data.append([int(week_counter), float(team[3])])
                weekly_coaching_efficiency_data.append([int(week_counter), team[4]])
                weekly_luck_data.append([int(week_counter), float(team[5])])
                weekly_power_rank_data.append([int(week_counter), team[6]])
                weekly_zscore_data.append([int(week_counter), team[7]])

            chosen_week_ordered_team_names = ordered_team_names
            chosen_week_ordered_managers = ordered_team_managers

            if week_counter == 1:
                for team_points in weekly_points_data:
                    time_series_points_data.append([team_points])
                for team_efficiency in weekly_coaching_efficiency_data:
                    time_series_efficiency_data.append([team_efficiency])
                for team_luck in weekly_luck_data:
                    time_series_luck_data.append([team_luck])
                for team_power_rank in weekly_power_rank_data:
                    time_series_power_rank_data.append([team_power_rank])
                for team_zscore in weekly_zscore_data:
                    time_series_zscore_data.append([team_zscore])
            else:
                for index, team_points in enumerate(weekly_points_data):
                    time_series_points_data[index].append(team_points)
                for index, team_efficiency in enumerate(weekly_coaching_efficiency_data):
                    if float(team_efficiency[1]) != 0.0:
                        time_series_efficiency_data[index].append(team_efficiency)
                for index, team_luck in enumerate(weekly_luck_data):
                    time_series_luck_data[index].append(team_luck)
                for index, team_power_rank in enumerate(weekly_power_rank_data):
                    time_series_power_rank_data[index].append(team_power_rank)
                for index, team_zscore in enumerate(weekly_zscore_data):
                    time_series_zscore_data[index].append(team_zscore)
            week_counter += 1

        report_info_dict["weekly_top_scorers"] = weekly_top_scores

        # calculate season average metrics and then add columns for them to their respective metric table data
        season_average_calculator = SeasonAverageCalculator(chosen_week_ordered_team_names, report_info_dict)
        report_info_dict["score_results_data"] = season_average_calculator.get_average(
            time_series_points_data, "score_results_data", with_percent_bool=False)
        report_info_dict["coaching_efficiency_results_data"] = season_average_calculator.get_average(
            time_series_efficiency_data, "coaching_efficiency_results_data", with_percent_bool=True)
        report_info_dict["luck_results_data"] = season_average_calculator.get_average(time_series_luck_data,
                                                                                      "luck_results_data",
                                                                                      with_percent_bool=True)
        report_info_dict["power_ranking_results_data"] = season_average_calculator.get_average(
            time_series_power_rank_data, "power_ranking_results_data", with_percent_bool=False, bench_column_bool=False,
            reverse_bool=False)

        # report_info_dict["zscore_results_data"] = season_average_calculator.get_average(
        #      time_series_zscore_data, "zscore_results_data", with_percent_bool=False, bench_column_bool=False,
        #      reverse_bool=False)

        line_chart_data_list = [chosen_week_ordered_team_names,
                                chosen_week_ordered_managers,
                                time_series_points_data,
                                time_series_efficiency_data,
                                time_series_luck_data,
                                time_series_power_rank_data,
                                time_series_zscore_data]

        # calculate season average points by position and add them to the report_info_dict
        PointsByPosition.calculate_points_by_position_season_averages(season_average_points_by_position_dict,
                                                                      report_info_dict)

        filename = self.league_name.replace(" ", "-") + \
            "(" + str(self.league_id) + ")_week-" + str(self.chosen_week) + "_report.pdf"
        report_save_dir = os.path.join(self.config.get("Fantasy_Football_Report_Settings", "output_dir"),
                                       self.league_name.replace(" ", "-") + "(" + self.league_id + ")")
        report_title_text = self.league_name + " (" + str(self.league_id) + ") Week " + str(self.chosen_week) + " Report"
        report_footer_text = \
            "<para alignment='center'>Report generated %s for Yahoo Fantasy Football league '%s' (%s).</para>" % \
            ("{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()), self.league_name, self.league_id)

        if not os.path.isdir(report_save_dir):
            os.makedirs(report_save_dir)

        if not self.test_bool:
            filename_with_path = os.path.join(report_save_dir, filename)
        else:
            filename_with_path = os.path.join(self.config.get("Fantasy_Football_Report_Settings", "output_dir"),
                                              "test_report.pdf")

        # instantiate pdf generator
        pdf_generator = PdfGenerator(
            config=self.config,
            league_id=self.league_id,
            playoff_slots=self.playoff_slots,
            num_regular_season_weeks=self.num_regular_season_weeks,
            week=self.chosen_week,
            data_dir=os.path.join(self.data_dir, str(self.season), self.league_key),
            break_ties_bool=self.break_ties_bool,
            report_title_text=report_title_text,
            report_footer_text=report_footer_text,
            report_info_dict=report_info_dict
        )

        # generate pdf of report
        file_for_upload = pdf_generator.generate_pdf(filename_with_path, line_chart_data_list)

        logger.info("...SUCCESS! Generated PDF: {}\n".format(file_for_upload))

        return file_for_upload
