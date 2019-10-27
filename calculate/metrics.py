__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import itertools
import logging
from collections import defaultdict
from statistics import mean

import numpy as np

from dao.base import BaseLeague, BaseTeam, BasePlayer

logger = logging.getLogger(__name__)


class CalculateMetrics(object):
    def __init__(self, config, league_id, playoff_slots, playoff_simulations):
        self.config = config
        self.league_id = league_id
        self.playoff_slots = playoff_slots
        self.playoff_simulations = playoff_simulations
        self.coaching_efficiency_dq_count = 0

    @staticmethod
    def decode_byte_string(string):
        try:
            return string.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return string

    @staticmethod
    def get_standings_data(
            league  # type: BaseLeague
    ):
        current_standings_data = []
        for team in league.current_standings:  # type: BaseTeam
            current_standings_data.append([
                team.rank,
                team.name,
                team.manager_str,
                str(team.wins) + "-" + str(team.losses) + "-" + str(team.ties) + " (" + str(team.percentage) + ")",
                round(float(team.points_for), 2),
                round(float(team.points_against), 2),
                team.streak_str,
                team.waiver_priority if not league.is_faab else "$%d" % team.faab,
                team.num_moves,
                team.num_trades
            ])
        return current_standings_data

    @staticmethod
    def get_playoff_probs_data(league_standings, team_playoffs_data):

        playoff_probs_data = []
        for team in league_standings:  # type: BaseTeam

            # sum rolling place percentages together to get a cumulative percentage chance of achieving that place
            summed_stats = []
            ndx = 1
            team_stats = team_playoffs_data[int(team.team_id)][2]
            while ndx <= len(team_stats):
                summed_stats.append(sum(team_stats[:ndx]))
                ndx += 1
            if summed_stats[-1] > 100.00:
                summed_stats[-1] = 100.00

            playoff_probs_data.append(
                [
                    team.name,
                    team.manager_str,
                    str(team.wins) + "-" + str(team.losses) + "-" + str(team.ties) + " (" + str(team.percentage) + ")",
                    team_playoffs_data[int(team.team_id)][1],
                    team_playoffs_data[int(team.team_id)][3]
                ] +
                summed_stats
                # FOR LEAGUES WITH CUSTOM PLAYOFFS NOT SUPPORTED BY YAHOO
                # TODO: FIX/REFACTOR
                # [
                #     team_playoffs_data[int(team["team_id"])][2][x] for x in range(self.config.getint(
                #         "Report", "num_playoff_slots"))
                # ]
            )

        sorted_playoff_probs_data = sorted(playoff_probs_data, key=lambda x: x[3], reverse=True)
        for team_playoff_probs_data in sorted_playoff_probs_data:
            team_playoff_probs_data[3] = "%.2f%%" % team_playoff_probs_data[3]
            if team_playoff_probs_data[4] == 1:
                team_playoff_probs_data[4] = "%d win" % team_playoff_probs_data[4]
            else:
                team_playoff_probs_data[4] = "%d wins" % team_playoff_probs_data[4]
            ndx = 5
            for stat in team_playoff_probs_data[5:]:
                team_playoff_probs_data[ndx] = "%.2f%%" % stat
                ndx += 1

        return sorted_playoff_probs_data

    @staticmethod
    def get_score_data(score_results):
        score_results_data = []
        place = 1
        for team in score_results:  # type: BaseTeam
            ranked_team_name = team.name
            ranked_team_manager = team.manager_str
            ranked_weekly_score = "%.2f" % float(team.points)
            ranked_weekly_bench_score = "%.2f" % float(team.bench_points)

            score_results_data.append(
                [place, ranked_team_name, ranked_team_manager, ranked_weekly_score, ranked_weekly_bench_score])

            place += 1

        return score_results_data

    def get_coaching_efficiency_data(self, coaching_efficiency_results):
        coaching_efficiency_results_data = []
        place = 1
        for team in coaching_efficiency_results:  # type: BaseTeam
            ranked_team_name = team.name
            ranked_team_manager = team.manager_str
            ranked_coaching_efficiency = team.coaching_efficiency

            if ranked_coaching_efficiency == 0.0:
                ranked_coaching_efficiency = "DQ"
                self.coaching_efficiency_dq_count += 1
            else:
                ranked_coaching_efficiency = "%.2f%%" % float(ranked_coaching_efficiency)

            coaching_efficiency_results_data.append(
                [place, ranked_team_name, ranked_team_manager, ranked_coaching_efficiency])

            place += 1

        return coaching_efficiency_results_data

    @staticmethod
    def get_luck_data(luck_results):
        luck_results_data = []
        place = 1
        for team in luck_results:  # type: BaseTeam
            ranked_team_name = team.name
            ranked_team_manager = team.manager_str
            ranked_luck = "%.2f%%" % team.luck

            luck_results_data.append([place, ranked_team_name, ranked_team_manager, ranked_luck])

            place += 1
        return luck_results_data

    @staticmethod
    def get_bad_boy_data(bad_boy_results):
        bad_boy_results_data = []
        place = 1
        for team in bad_boy_results:  # type: BaseTeam
            ranked_team_name = team.name
            ranked_team_manager = team.manager_str
            ranked_bb_points = "%d" % team.bad_boy_points
            ranked_offense = team.worst_offense
            ranked_count = "%d" % team.num_offenders

            bad_boy_results_data.append([place, ranked_team_name, ranked_team_manager, ranked_bb_points,
                                         ranked_offense, ranked_count])

            place += 1
        return bad_boy_results_data

    @staticmethod
    def get_beef_rank_data(beef_results):
        beef_results_data = []
        place = 1
        for team in beef_results:  # type: BaseTeam
            ranked_team_name = team.name
            ranked_team_manager = team.manager_str
            ranked_beef_points = "%.3f" % team.tabbu

            beef_results_data.append([place, ranked_team_name, ranked_team_manager, ranked_beef_points])
            place += 1
        return beef_results_data

    def get_ties_count(self, results_data, tie_type, break_ties):

        if tie_type == "power_ranking":
            groups = [list(group) for key, group in itertools.groupby(results_data, lambda x: x[0])]
            num_ties = self.count_ties(groups)
        else:
            groups = [list(group) for key, group in itertools.groupby(results_data, lambda x: x[3])]
            num_ties = self.count_ties(groups)

        # if there are ties, record them and break them if possible
        if num_ties > 0:
            ties_count = 0
            team_index = 0
            place = 1
            while ties_count != num_ties:

                for group in groups:
                    if len(group) > 1:
                        ties_count += sum(range(len(group)))

                        for team in group:
                            if tie_type == "power_ranking":
                                results_data[team_index] = [
                                    str(team[0]) + "*",
                                    team[1],
                                    team[2],
                                ]
                            elif tie_type == "score" and break_ties:
                                results_data[team_index] = [
                                    str(place),
                                    team[1],
                                    team[2],
                                    team[3]
                                ]
                                if group.index(team) != (len(group) - 1):
                                    place += 1
                            elif tie_type == "bad_boy":
                                results_data[team_index] = [
                                    str(place) + "*",
                                    team[1],
                                    team[2],
                                    team[3],
                                    team[4],
                                    team[5]
                                ]
                            else:
                                results_data[team_index] = [
                                    str(place) + "*",
                                    team[1],
                                    team[2],
                                    team[3]
                                ]
                            if tie_type == "score":
                                results_data[team_index].append(team[4])
                            team_index += 1
                        place += 1

                    else:
                        if tie_type == "power_ranking":
                            results_data[team_index] = [
                                group[0][0],
                                group[0][1],
                                group[0][2],
                            ]
                        elif tie_type == "score" and break_ties:
                            results_data[team_index] = [
                                str(place),
                                group[0][1],
                                group[0][2],
                                group[0][3]
                            ]
                        elif tie_type == "bad_boy":
                            results_data[team_index] = [
                                str(place),
                                group[0][1],
                                group[0][2],
                                group[0][3],
                                group[0][4],
                                group[0][5]
                            ]
                        else:
                            results_data[team_index] = [
                                str(place),
                                group[0][1],
                                group[0][2],
                                group[0][3]
                            ]
                        if tie_type == "score":
                            results_data[team_index].append(group[0][4])
                        team_index += 1
                        place += 1
        return num_ties

    @staticmethod
    def count_ties(groups):
        num_ties = 0
        for group in groups:
            if len(group) > 1 and "DQ" not in group[0]:
                num_ties += sum(range(len(group)))

        return num_ties

    @staticmethod
    def resolve_score_ties(data_for_scores, break_ties):

        groups = [list(group) for key, group in itertools.groupby(data_for_scores, lambda x: x[3])]

        resolved_score_results_data = []
        place = 1
        for group in groups:
            for team in sorted(group, key=lambda x: x[-1], reverse=True):
                if groups.index(group) != 0:
                    team[0] = place
                else:
                    if break_ties:
                        team[0] = place
                resolved_score_results_data.append(team)
                place += 1

        return resolved_score_results_data

    @staticmethod
    def resolve_coaching_efficiency_ties(data_for_coaching_efficiency,
                                         ties_for_coaching_efficiency,
                                         league,  # type: BaseLeague
                                         teams_results,
                                         week,
                                         week_for_report,
                                         break_ties):

        if league.player_data_by_week_function:
            coaching_efficiency_results_data_with_tiebreakers = []
            bench_positions = league.get_roster_slots_by_type().get("positions_bench")

            season_average_points_by_player_dict = defaultdict(list)
            if break_ties and ties_for_coaching_efficiency > 0 and int(week) == int(week_for_report):
                for ce_result in data_for_coaching_efficiency:
                    if ce_result[0] == "1*":
                        players = []
                        for team_result in teams_results.values():
                            if team_result.name == ce_result[1]:
                                players = teams_results.get(team_result.team_id).roster

                        num_players_exceeded_season_avg_points = 0
                        total_percentage_points_players_exceeded_season_avg_points = 0
                        for player in players:  # type: BasePlayer
                            if player.selected_position not in bench_positions:
                                week_counter = 1
                                while week_counter <= int(week):
                                    players_by_week = league.players_by_week[str(week_counter)]
                                    if str(player.player_id) in players_by_week.keys():
                                        weekly_player_points = players_by_week[str(player.player_id)].points
                                    else:
                                        weekly_player_points = league.get_player_data_by_week(
                                            str(player.player_id), str(week_counter))

                                    season_average_points_by_player_dict[player.player_id].append(weekly_player_points)
                                    week_counter += 1

                                player_last_week_points = season_average_points_by_player_dict[player.player_id][-1]

                                # handle the beginning of the season when a player has only played one or no games
                                player_season_weekly_points = season_average_points_by_player_dict[player.player_id]
                                if len(player_season_weekly_points) == 0:
                                    player_season_avg_points = 0
                                elif len(player_season_weekly_points) == 1:
                                    player_season_avg_points = player_season_weekly_points[0]
                                else:
                                    player_season_avg_points = mean(player_season_weekly_points[:-1])

                                if player_last_week_points > player_season_avg_points:
                                    num_players_exceeded_season_avg_points += 1

                                    if player_season_avg_points > 0:
                                        total_percentage_points_players_exceeded_season_avg_points += \
                                            (((player_last_week_points - player_season_avg_points) /
                                              player_season_avg_points) * 100.0)
                                    else:
                                        total_percentage_points_players_exceeded_season_avg_points += 100.0

                        ce_result.extend([num_players_exceeded_season_avg_points,
                                          round(total_percentage_points_players_exceeded_season_avg_points, 2)])
                        coaching_efficiency_results_data_with_tiebreakers.append(ce_result)
                    else:
                        ce_result.extend(["N/A", "N/A"])
                        coaching_efficiency_results_data_with_tiebreakers.append(ce_result)

                groups = [list(group) for key, group in
                          itertools.groupby(coaching_efficiency_results_data_with_tiebreakers, lambda x: x[3])]
            else:
                groups = [list(group) for key, group in itertools.groupby(data_for_coaching_efficiency, lambda x: x[3])]

            resolved_coaching_efficiency_results_data = []
            place = 1
            for group in groups:
                # for team in sorted(group, key=lambda x: x[-2], reverse=True):
                for team in sorted(group, key=lambda x: (x[-2], x[-1]), reverse=True):
                    if groups.index(group) != 0:
                        team[0] = place
                    else:
                        if break_ties:
                            team[0] = place
                    resolved_coaching_efficiency_results_data.append(team)
                    place += 1
            return resolved_coaching_efficiency_results_data
        else:
            logger.warning(
                "No function to retrieve past player weekly points available. Cannot resolve coaching efficiency ties.")
            return data_for_coaching_efficiency

    @staticmethod
    def resolve_season_average_ties(data_for_season_averages, with_percent):

        groups = [list(group) for key, group in itertools.groupby(data_for_season_averages, lambda x: x[2])]

        resolved_season_average_results_data = []
        place = 1
        for group in groups:
            for team in sorted(group, key=lambda x: x[-1], reverse=True):
                team[0] = place
                if with_percent:
                    team[2] = "{0}% ({1})".format(str(team[2]), str(place))
                else:
                    team[2] = "{0} ({1})".format(str(team[2]), str(place))

                resolved_season_average_results_data.append(team)
            place += 1

        return resolved_season_average_results_data

    # noinspection PyUnusedLocal
    @staticmethod
    def test_ties(teams_results):
        for team_id, team in teams_results.items():

            team_id = team.team_id

            # for testing score ties
            test_score = 70
            test_efficiency = 75.00
            test_luck = 10.00
            test_power_rank = 5.0

            # swap the first team to test for non-first place ties vs. first place ties
            # if int(team_id) == 1:
            #     test_score = 101
            #     test_efficiency = 101.00
            #     test_luck = 99.50
            #     test_power_rank = 0.9
            if int(team_id) == 1:
                test_score = 100
                test_efficiency = 100.00
                test_luck = 99.00
                test_power_rank = 1.0
            elif int(team_id) == 2:
                test_score = 100
                test_efficiency = 100.00
                test_luck = 99.00
                test_power_rank = 1.0
            # swap the third time to test for middle ranked non-ties
            # elif int(team_id) == 3:
            #     test_score = 100
            #     test_efficiency = 100.00
            #     test_luck = 99.00
            #     test_power_rank = 1.0
            elif int(team_id) == 3:
                test_score = 95
                test_efficiency = 95.00
                test_luck = 50.00
                test_power_rank = 1.5
            elif int(team_id) == 4:
                test_score = 90
                test_efficiency = 90.00
                test_luck = 5.00
                test_power_rank = 2.0
            elif int(team_id) == 5:
                test_score = 90
                test_efficiency = 90.00
                test_luck = 5.00
                test_power_rank = 2.0
            elif int(team_id) == 6:
                test_score = 90
                test_efficiency = 90.00
                test_luck = 5.00
                test_power_rank = 2.0
            # uncomment to test ending teams with unique place
            elif int(team_id) == len(list(teams_results.keys())):
                test_score = 85
                test_efficiency = 85.00
                test_luck = -5.00
                test_power_rank = 6.0

            # # uncomment to test scoring ties
            # team.score = test_score
            #
            # # uncomment to test coaching efficiency ties
            # team.coaching_efficiency = test_efficiency
            #
            # # # uncomment to test luck ties
            # team.luck = test_luck
            #
            # # # uncomment to test power ranking ties
            # team.power_rank = test_power_rank

    def calculate_luck_and_record(self, teams, matchups_list):

        results = defaultdict(dict)
        matchups = {
            self.decode_byte_string(name): value[
                "result"] for pair in matchups_list for name, value in list(pair.items())
        }

        for team_1 in teams.values():  # type: BaseTeam
            record = {
                "W": 0,
                "L": 0,
                "T": 0
            }

            for team_2 in teams.values():
                if team_1.team_id == team_2.team_id:
                    continue
                score_1 = team_1.points
                score_2 = team_2.points

                if float(score_1) > float(score_2):
                    record["W"] += 1
                elif float(score_1) < float(score_2):
                    record["L"] += 1
                else:
                    record["T"] += 1

            results[team_1.team_id]["record"] = record

            # calc luck %
            # TODO: assuming no ties...  how are tiebreakers handled?
            luck = 0.0
            # number of teams excluding current team
            num_teams = float(len(teams)) - 1

            if record["W"] != 0 and record["L"] != 0:
                matchup_result = matchups[self.decode_byte_string(team_1.name)]
                if matchup_result == "W" or matchup_result == "T":
                    luck = (record["L"] + record["T"]) / num_teams
                else:
                    luck = 0 - (record["W"] + record["T"]) / num_teams

            # noinspection PyTypeChecker
            results[team_1.team_id]["luck"] = luck * 100

        return results

    @staticmethod
    def get_ranks_for_metric(data_for_metric, power_ranked_teams, metric_ranking_key):
        rank = 1
        for team in data_for_metric:
            for team_rankings in power_ranked_teams.values():
                if team[1] == team_rankings["name"]:
                    team_rankings[metric_ranking_key] = rank
            rank += 1

    def calculate_power_rankings(self, teams_results, data_for_scores, data_for_coaching_efficiency, data_for_luck):
        """ avg of (weekly score rank + weekly coaching efficiency rank + weekly luck rank)
        """
        power_ranked_teams = {
            team_result.team_id: {
                "name": team_result.name,
                "manager_str": team_result.manager_str
            } for team_result in teams_results.values()
        }

        self.get_ranks_for_metric(data_for_scores, power_ranked_teams, "score_ranking")
        self.get_ranks_for_metric(data_for_coaching_efficiency, power_ranked_teams, "coaching_efficiency_ranking")
        self.get_ranks_for_metric(data_for_luck, power_ranked_teams, "luck_ranking")

        for team_rankings in power_ranked_teams.values():
            team_rankings["power_ranking"] = (team_rankings["score_ranking"] +
                                              team_rankings["coaching_efficiency_ranking"] +
                                              team_rankings["luck_ranking"]) // 3.0
        return power_ranked_teams

    @staticmethod
    def calculate_z_scores(weekly_teams_results):

        results = {}

        # can only determine z_score
        can_calculate = len(weekly_teams_results) > 2

        # iterates through team ids of first week since team ids remain unchanged
        for team_id in weekly_teams_results[0].keys():
            z_score = None

            if can_calculate:
                scores = [week[team_id].points for week in weekly_teams_results]

                scores_excluding_current = scores[:-1]
                current_score = scores[-1]

                standard_deviation = np.std(scores_excluding_current)
                mean_score = np.mean(scores_excluding_current)
                z_score = (current_score - mean_score) / standard_deviation

            results[team_id] = z_score

        return results
