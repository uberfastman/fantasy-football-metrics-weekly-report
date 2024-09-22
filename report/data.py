__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import itertools
from typing import List

from calculate.metrics import CalculateMetrics
from calculate.points_by_position import PointsByPosition
from dao.base import BaseLeague, BaseMatchup, BaseTeam
from utilities.app import add_report_team_stats, get_player_game_time_statuses
from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)


class ReportData(object):

    def __init__(self, league: BaseLeague, season_weekly_teams_results, week_counter: int,
                 week_for_report: int, season: int, metrics_calculator: CalculateMetrics, metrics,
                 break_ties: bool = False, dq_ce: bool = False, testing: bool = False):
        logger.debug("Instantiating report data.")

        self.league: BaseLeague = league
        self.break_ties: bool = break_ties
        self.dq_ce: bool = dq_ce
        self.week: int = league.week
        self.bench_positions: List[str] = league.bench_positions
        self.has_divisions: bool = league.has_divisions
        self.has_waiver_priorities: bool = league.has_waiver_priorities
        self.is_faab: bool = league.is_faab

        inactive_players = []
        if dq_ce:
            injured_players = get_player_game_time_statuses(week_counter, league).findAll("div", {"class": "tr"})
            for player in injured_players:
                player_name = player.find("a").text.strip()
                player_status_info = player.find("div", {"class": "td w20 hidden-xs"}).find("b")
                if player_status_info:
                    player_status = player_status_info.text.strip()
                    if player_status == "Out":
                        inactive_players.append(player_name)

        self.teams_results = {
            team.team_id: add_report_team_stats(
                team,
                league,
                week_counter,
                metrics_calculator,
                metrics,
                dq_ce,
                inactive_players
            ) for team in league.teams_by_week.get(str(week_counter)).values()
        }

        records = {}
        for team_id, team in self.teams_results.items():
            records[team_id] = team.record

        league.standings = sorted(
            league.teams_by_week.get(str(week_counter)).values(),
            key=lambda x: (
                league.records_by_week[str(week_counter)][x.team_id].rank,
                -league.records_by_week[str(week_counter)][x.team_id].get_points_for()
            )
        )

        # option to disqualify team(s) manually entered in the .env file for current week of coaching efficiency
        self.coaching_efficiency_dqs = {}
        if week_counter == week_for_report:
            for team in settings.coaching_efficiency_disqualified_teams_list:
                self.coaching_efficiency_dqs[team] = -2
                for team_result in self.teams_results.values():
                    if team == team_result.name:
                        team_result.coaching_efficiency = "DQ"

        # used only for testing what happens when different metrics are tied; requires uncommenting lines in method
        if testing:
            metrics_calculator.test_ties(self.teams_results)

        # get remaining matchups for Monte Carlo playoff simulations
        remaining_matchups = {}
        for week, matchups in league.matchups_by_week.items():
            if int(week) > week_for_report:
                remaining_matchups[str(week)] = []
                matchup: BaseMatchup
                for matchup in matchups:
                    matchup_teams = []
                    for team in matchup.teams:
                        matchup_teams.append(team.team_id)
                    remaining_matchups[str(week)].append(tuple(matchup_teams))

        # calculate z-scores (dependent on all previous weeks scores)
        z_score_results = metrics_calculator.calculate_z_scores(season_weekly_teams_results + [self.teams_results])

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ REPORT DATA ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        logger.debug("Creating report data.")

        # create attributes for later updating
        self.data_for_season_avg_points_by_position = None
        self.data_for_season_weekly_top_scorers = None
        self.data_for_season_weekly_highest_ce = None

        # current standings data
        self.data_for_current_standings = metrics_calculator.get_standings_data(league)

        # current division standings data
        self.divisions = None
        self.data_for_current_division_standings = None
        if self.has_divisions:
            self.divisions = league.divisions
            self.data_for_current_division_standings = metrics_calculator.get_division_standings_data(league)

        # current median standings data
        self.data_for_current_median_standings = metrics_calculator.get_median_standings_data(league)

        if league.num_playoff_slots > 0:
            # playoff probabilities data
            self.data_for_playoff_probs = metrics.get("playoff_probs").calculate(
                week_counter, week_for_report, league.standings, remaining_matchups
            )
        else:
            self.data_for_playoff_probs = None

        if self.data_for_playoff_probs:
            self.data_for_playoff_probs = metrics_calculator.get_playoff_probs_data(
                league.standings,
                self.data_for_playoff_probs
            )
        else:
            self.data_for_playoff_probs = None

        # z-scores data
        self.data_for_z_scores = []
        z_score_rank = 1
        if all(z_score_val is None for z_score_val in z_score_results.values()):
            create_z_score_data = False
        elif any(z_score_val is None for z_score_val in z_score_results.values()):
            create_z_score_data = True
            z_score_results = {
                team_id: 0 if not z_score_val else z_score_val for team_id, z_score_val in z_score_results.items()
            }
        else:
            create_z_score_data = True

        if create_z_score_data:
            for k_v in sorted(z_score_results.items(), key=lambda x: x[1], reverse=True):
                z_score = k_v[1]
                if z_score:
                    z_score = round(float(z_score), 2)
                else:
                    z_score = "N/A"

                team = self.teams_results[k_v[0]]
                self.data_for_z_scores.append(
                    [
                        z_score_rank,
                        team.name,
                        team.manager_str,
                        z_score
                    ]
                )
                z_score_rank += 1

        # points by position data
        points_by_position = PointsByPosition(league, week_for_report)
        self.data_for_weekly_points_by_position = points_by_position.get_weekly_points_by_position(self.teams_results)

        # teams data and season average points by position data
        self.data_for_teams = []
        team_result: BaseTeam
        for team_result in self.teams_results.values():
            self.data_for_teams.append([
                team_result.team_id,
                team_result.name,
                team_result.manager_str,
                team_result.points,
                team_result.coaching_efficiency,
                team_result.luck,
                team_result.optimal_points,
                z_score_results[team_result.team_id]
            ])

        self.data_for_teams.sort(key=lambda x: x[1])

        # scores data
        self.data_for_scores = metrics_calculator.get_score_data(
            sorted(self.teams_results.values(), key=lambda x: float(x.points), reverse=True))

        # coaching efficiency data
        self.data_for_coaching_efficiency = metrics_calculator.get_coaching_efficiency_data(
            sorted(self.teams_results.values(), key=lambda x: float(
                x.coaching_efficiency) if x.coaching_efficiency != "DQ" else 0, reverse=True))
        self.num_coaching_efficiency_dqs = metrics_calculator.coaching_efficiency_dq_count
        self.coaching_efficiency_dqs.update(metrics.get("coaching_efficiency").coaching_efficiency_dqs)

        # luck data
        self.data_for_luck = metrics_calculator.get_luck_data(
            sorted(self.teams_results.values(), key=lambda x: float(x.luck), reverse=True))

        # optimal score data
        self.data_for_optimal_scores = metrics_calculator.get_optimal_score_data(
            sorted(self.teams_results.values(), key=lambda x: float(x.optimal_points), reverse=True))

        # bad boy data
        self.data_for_bad_boy_rankings = metrics_calculator.get_bad_boy_data(
            sorted(self.teams_results.values(), key=lambda x: x.bad_boy_points, reverse=True))

        # beef rank data
        self.data_for_beef_rankings = metrics_calculator.get_beef_rank_data(
            sorted(self.teams_results.values(), key=lambda x: x.tabbu, reverse=True))

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ COUNT METRIC TIES ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        logger.debug("Counting metric ties.")

        # get number of scores ties and ties for first
        self.ties_for_scores = metrics_calculator.get_ties_count(self.data_for_scores, "score", self.break_ties)
        self.num_first_place_for_score_before_resolution = len(
            [list(group) for key, group in itertools.groupby(self.data_for_scores, lambda x: x[3])][0])

        # reorder score data based on bench points if there are ties and break_ties = True
        if self.ties_for_scores > 0:
            self.data_for_scores = metrics_calculator.resolve_score_ties(self.data_for_scores, self.break_ties)
            metrics_calculator.get_ties_count(self.data_for_scores, "score", self.break_ties)
        self.num_first_place_for_score = len(
            [list(group) for key, group in itertools.groupby(self.data_for_scores, lambda x: x[3])][0])

        # get number of coaching efficiency ties and ties for first
        self.ties_for_coaching_efficiency = metrics_calculator.get_ties_count(self.data_for_coaching_efficiency,
                                                                              "coaching_efficiency", self.break_ties)
        self.num_first_place_for_coaching_efficiency_before_resolution = len(
            [list(group) for key, group in itertools.groupby(self.data_for_coaching_efficiency, lambda x: x[0])][0])

        if self.ties_for_coaching_efficiency > 0:
            self.data_for_coaching_efficiency = metrics_calculator.resolve_coaching_efficiency_ties(
                self.data_for_coaching_efficiency, self.ties_for_coaching_efficiency, league, self.teams_results,
                int(week_counter), int(week_for_report), self.break_ties)
        self.num_first_place_for_coaching_efficiency = len(
            [list(group) for key, group in itertools.groupby(self.data_for_coaching_efficiency, lambda x: x[0])][0])

        # get number of luck ties and ties for first
        self.ties_for_luck = metrics_calculator.get_ties_count(self.data_for_luck, "luck", self.break_ties)
        self.num_first_place_for_luck = len(
            [list(group) for key, group in itertools.groupby(self.data_for_luck, lambda x: x[3])][0])

        # get number of bad boy rankings ties and ties for first
        self.ties_for_bad_boy_rankings = metrics_calculator.get_ties_count(self.data_for_bad_boy_rankings, "bad_boy",
                                                                           self.break_ties)
        self.num_first_place_for_bad_boy_rankings = len(
            [list(group) for key, group in itertools.groupby(self.data_for_bad_boy_rankings, lambda x: x[3])][0])
        # filter out teams that have no bad boys in their starting lineup
        self.data_for_bad_boy_rankings = [result for result in self.data_for_bad_boy_rankings if int(result[5]) != 0]

        # get number of beef rankings ties and ties for first
        self.ties_for_beef_rankings = metrics_calculator.get_ties_count(self.data_for_beef_rankings, "beef",
                                                                        self.break_ties)
        self.num_first_place_for_beef_rankings = len(
            [list(group) for key, group in itertools.groupby(self.data_for_beef_rankings, lambda x: x[3])][0])

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ CALCULATE POWER RANKING ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        logger.debug("Calculating power rankings.")

        # calculate power ranking last to account for metric rankings that have been reordered due to tiebreakers
        power_ranking_results = metrics_calculator.calculate_power_rankings(
            self.teams_results,
            self.data_for_scores,
            self.data_for_coaching_efficiency,
            self.data_for_luck
        )

        # update data_for_teams with power rankings
        for team in self.data_for_teams:
            for team_id in power_ranking_results.keys():
                if team[0] == team_id:
                    team.append(power_ranking_results[team_id]["power_ranking"])

        # power rankings data
        self.data_for_power_rankings = []
        for k_v in sorted(power_ranking_results.items(), key=lambda x: x[1]["power_ranking"]):
            # season avg calc does something where it _keys off the second value in the array
            self.data_for_power_rankings.append(
                [k_v[1]["power_ranking"], power_ranking_results[k_v[0]]["name"], k_v[1]["manager_str"]]
            )

        # get number of power rankings ties and ties for first
        self.ties_for_power_rankings = metrics_calculator.get_ties_count(self.data_for_power_rankings, "power_ranking",
                                                                         self.break_ties)
        self.ties_for_first_for_power_rankings = len(
            [list(group) for key, group in itertools.groupby(self.data_for_power_rankings, lambda x: x[0])][0])

        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ LOGGER OUTPUT ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        # ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~

        weekly_metrics_info = (
            f"\n~~~~~ WEEK {week_counter} METRICS INFO ~~~~~\n"
            f"              SCORE tie(s): {self.ties_for_scores}\n"
            f"COACHING EFFICIENCY tie(s): {self.ties_for_coaching_efficiency}\n"
        )

        # add line for coaching efficiency disqualifications if applicable
        ce_dq_str = None
        if self.num_coaching_efficiency_dqs > 0:
            ce_dqs = []
            for team_name, ineligible_players_count in self.coaching_efficiency_dqs.items():
                if ineligible_players_count == -1:
                    ce_dqs.append(f"{team_name} (incomplete active squad)")
                elif ineligible_players_count == -2:
                    ce_dqs.append(f"{team_name} (manually disqualified)")
                else:
                    ce_dqs.append(
                        f"{team_name} (ineligible bench players: "
                        f"{ineligible_players_count}/{league.roster_position_counts.get('BN')})"
                    )  # exclude IR

            ce_dq_str = ', '.join(ce_dqs)
            weekly_metrics_info += f"   COACHING EFFICIENCY DQs: {ce_dq_str}\n"

        # log weekly metrics info
        logger.debug(weekly_metrics_info)
        logger.info(
            f"Week {week_counter} data processed"
            f"{f' with the following coaching efficiency DQs: {ce_dq_str})' if ce_dq_str else ''}"
            f"."
        )
