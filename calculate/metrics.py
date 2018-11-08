# written by Wren J.R.
# contributors: Kevin N., Joe M.

import itertools
from calculate.playoff_probabilities import Team, Record


class CalculateMetrics(object):
    def __init__(self, config, league_id, playoff_slots):
        self.config = config
        self.league_id = league_id
        self.playoff_slots = playoff_slots
        self.coaching_efficiency_dq_count = 0
        self.teams_info = {}

    def get_standings(self, league_standings_data):
        current_standings_data = []

        for team in league_standings_data.loc[0, "standings"].get("teams").get("team"):
            streak_type = team.get("team_standings").get("streak").get("type")
            if streak_type == "loss":
                streak_type = "L"
            elif streak_type == "win":
                streak_type = "W"
            else:
                streak_type = "T"

            # Handle co-managers - if there are co-managers, select the primary manager's name to display
            manager = ""
            manager_info = team["managers"]["manager"]
            if type(manager_info) is dict:
                manager = manager_info["nickname"]
            else:
                for manager in manager_info:
                    if manager["is_comanager"] is None:
                        manager = manager_info["nickname"]

            current_standings_data.append([
                team.get("team_standings").get("rank"),
                team.get("name"),
                manager,
                team.get("team_standings").get("outcome_totals").get("wins") + "-" +
                team.get("team_standings").get("outcome_totals").get("losses") + "-" +
                team.get("team_standings").get("outcome_totals").get("ties") + " (" +
                team.get("team_standings").get("outcome_totals").get("percentage") + ")",
                team.get("team_standings").get("points_for"),
                team.get("team_standings").get("points_against"),
                streak_type + "-" + team.get("team_standings").get("streak").get("value"),
                team.get("waiver_priority"),
                team.get("number_of_moves"),
                team.get("number_of_trades")
            ])

            self.teams_info[team.get("team_id")] = Team(
                team.get("team_id"),
                team.get("name"),
                manager,
                Record(
                    int(team.get("team_standings").get("outcome_totals").get("wins")),
                    int(team.get("team_standings").get("outcome_totals").get("losses")),
                    int(team.get("team_standings").get("outcome_totals").get("ties")),
                    team.get("team_standings").get("outcome_totals").get("percentage")
                ),
                float(team.get("team_standings").get("points_for")),
                self.playoff_slots,
                self.config.getint("Fantasy_Football_Report_Settings", "num_playoff_simulations")
            )

        return current_standings_data

    @staticmethod
    def get_playoff_probs_data(league_standings_data, team_playoffs_data):

        playoff_probs_data = []

        for team in league_standings_data.loc[0, "standings"].get("teams").get("team"):

            # sum rolling place percentages together to get a cumulative percentage chance of achieving that place
            summed_stats = []
            ndx = 1
            team_stats = team_playoffs_data[int(team["team_id"])][2]
            while ndx <= len(team_stats):
                summed_stats.append(sum(team_stats[:ndx]))
                ndx += 1
            if summed_stats[-1] > 100.00:
                summed_stats[-1] = 100.00

            # Handle co-managers - if there are co-managers, select the primary manager's name to display
            manager = ""
            manager_info = team["managers"]["manager"]
            if type(manager_info) is dict:
                manager = manager_info["nickname"]
            else:
                for manager in manager_info:
                    if manager["is_comanager"] is None:
                        manager = manager_info["nickname"]

            wins = int(team.get("team_standings").get("outcome_totals").get("wins"))

            playoff_probs_data.append(
                [
                    team.get("name"),
                    manager,
                    str(wins) + "-" +
                    team.get("team_standings").get("outcome_totals").get("losses") + "-" +
                    team.get("team_standings").get("outcome_totals").get("ties") + " (" +
                    team.get("team_standings").get("outcome_totals").get("percentage") + ")",
                    team_playoffs_data[int(team["team_id"])][1],
                    team_playoffs_data[int(team["team_id"])][3]
                ] +
                summed_stats
                # [
                #     team_playoffs_data[int(team["team_id"])][2][x] for x in range(self.config.getint(
                #         "Fantasy_Football_Report_Settings", "num_playoff_slots"))
                # ]
            )

        sorted_playoff_probs_data = sorted(playoff_probs_data, key=lambda x: x[3], reverse=True)
        for team in sorted_playoff_probs_data:
            team[3] = "%.2f%%" % team[3]
            if team[4] == 1:
                team[4] = "%d win" % team[4]
            else:
                team[4] = "%d wins" % team[4]
            ndx = 5
            for stat in team[5:]:
                team[ndx] = "%.2f%%" % stat
                ndx += 1

        return sorted_playoff_probs_data

    @staticmethod
    def get_score_data(score_results):
        score_results_data = []
        place = 1
        for key, value in score_results:
            ranked_team_name = key
            ranked_team_manager = value.get("manager")
            ranked_weekly_score = "%.2f" % float(value.get("score"))
            ranked_weekly_bench_score = "%.2f" % float(value.get("bench_score"))

            score_results_data.append(
                [place, ranked_team_name, ranked_team_manager, ranked_weekly_score, ranked_weekly_bench_score])

            place += 1

        return score_results_data

    def get_coaching_efficiency_data(self, coaching_efficiency_results):
        coaching_efficiency_results_data = []
        place = 1
        for key, value in coaching_efficiency_results:
            ranked_team_name = key
            ranked_team_manager = value.get("manager")
            ranked_coaching_efficiency = value.get("coaching_efficiency")

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
        for key, value in luck_results:
            ranked_team_name = key
            ranked_team_manager = value.get("manager")
            ranked_luck = "%.2f%%" % value.get("luck")

            luck_results_data.append([place, ranked_team_name, ranked_team_manager, ranked_luck])

            place += 1
        return luck_results_data

    @staticmethod
    def get_bad_boy_data(bad_boy_results):
        bad_boy_results_data = []
        place = 1
        for key, value in bad_boy_results:
            ranked_team_name = key
            ranked_team_manager = value.get("manager")
            ranked_bb_points = "%d" % value.get("bad_boy_points")
            ranked_offense = value.get("worst_offense")
            ranked_count = "%d" % value.get("num_offenders")

            bad_boy_results_data.append([place, ranked_team_name, ranked_team_manager, ranked_bb_points,
                                         ranked_offense, ranked_count])

            place += 1
        return bad_boy_results_data

    def get_num_ties(self, results_data, tie_type, break_ties_bool):

        if tie_type == "power_rank":
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
                            if tie_type == "power_rank":
                                results_data[team_index] = [
                                    str(place) + ".0*",
                                    team[1],
                                    team[2],
                                ]
                            elif tie_type == "score" and break_ties_bool:
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
                        if tie_type == "power_rank":
                            results_data[team_index] = [
                                str(place) + ".0",
                                group[0][1],
                                group[0][2],
                            ]
                        elif tie_type == "score" and break_ties_bool:
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
            if len(group) > 1:
                num_ties += sum(range(len(group)))

        return num_ties

    @staticmethod
    def resolve_score_ties(score_results_data, break_ties_bool):

        groups = [list(group) for key, group in itertools.groupby(score_results_data, lambda x: x[3])]

        resolved_score_results_data = []
        place = 1
        for group in groups:
            for team in sorted(group, key=lambda x: x[-1], reverse=True):
                if groups.index(group) != 0:
                    team[0] = place
                else:
                    if break_ties_bool:
                        team[0] = place
                resolved_score_results_data.append(team)
                place += 1

        return resolved_score_results_data

    @staticmethod
    def resolve_season_average_ties(season_average_results_data, with_percent_bool):

        groups = [list(group) for key, group in itertools.groupby(season_average_results_data, lambda x: x[2])]

        resolved_season_average_results_data = []
        place = 1
        for group in groups:
            for team in sorted(group, key=lambda x: x[-1], reverse=True):
                team[0] = place
                if with_percent_bool:
                    team[2] = "{0}% ({1})".format(str(team[2]), str(place))
                else:
                    team[2] = "{0} ({1})".format(str(team[2]), str(place))

                resolved_season_average_results_data.append(team)
            place += 1

        return resolved_season_average_results_data

    # noinspection PyUnusedLocal
    @staticmethod
    def test_ties(team_results_dict):
        for team in list(team_results_dict.keys()):
            team_id = team_results_dict.get(team).get("team_id")

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
            elif int(team_id) == len(list(team_results_dict.keys())):
                test_score = 85
                test_efficiency = 85.00
                test_luck = -5.00
                test_power_rank = 6.0

            # # uncomment to test scoring ties
            # team_results_dict.get(team)["score"] = test_score
            #
            # # uncomment to test coaching efficiency ties
            # team_results_dict.get(team)["coaching_efficiency"] = test_efficiency
            #
            # # # uncomment to test luck ties
            # team_results_dict.get(team)["luck"] = test_luck
            #
            # # # uncomment to test power ranking ties
            # team_results_dict.get(team)["power_rank"] = test_power_rank
