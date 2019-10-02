__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

from yffpy.models import Team, Player

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats


class ReportPlayer(Player):

    def __init__(self, yffpy_player, bench_positions, metrics):
        Player.__init__(self, yffpy_player.extracted_data)

        self.bad_boy_crime = str()
        self.bad_boy_points = int()
        self.bad_boy_num_offenders = int()
        self.weight = float()
        self.tabbu = float()

        if self.selected_position_value not in bench_positions:
            bad_boy_stats = metrics.get("bad_boy_stats")  # type: BadBoyStats
            self.bad_boy_crime = bad_boy_stats.get_player_bad_boy_crime(
                self.full_name, self.editorial_team_abbr, self.primary_position)
            self.bad_boy_points = bad_boy_stats.get_player_bad_boy_points(
                self.full_name, self.editorial_team_abbr, self.primary_position)
            self.bad_boy_num_offenders = bad_boy_stats.get_player_bad_boy_num_offenders(
                self.full_name, self.editorial_team_abbr, self.primary_position)

            beef_stats = metrics.get("beef_stats")  # type: BeefStats
            self.weight = beef_stats.get_player_weight(self.first_name, self.last_name, self.editorial_team_abbr)
            self.tabbu = beef_stats.get_player_tabbu(self.first_name, self.last_name, self.editorial_team_abbr)


class ReportTeam(Team):

    def __init__(self,
                 yffpy_team,
                 league_data,
                 week_counter,
                 metrics,
                 dq_ce):
        Team.__init__(self, yffpy_team.extracted_data)

        self.name = self.name.decode("utf-8")
        bench_positions = league_data.roster_positions_by_type.get("positions_bench")

        if isinstance(yffpy_team.managers, list):
            self.manager_str = ", ".join([manager.get("manager").nickname for manager in yffpy_team.managers])
        else:
            self.manager_str = yffpy_team.managers.get("manager").nickname

        self.players = []
        for player in league_data.rosters_by_week[week_counter].get(self.team_id):
            self.players.append(ReportPlayer(player.get("player"), bench_positions, metrics))

        self.score = sum(
            [p.player_points_value for p in self.players if p.selected_position_value not in bench_positions])
        self.bench_score = sum(
            [p.player_points_value for p in self.players if p.selected_position_value in bench_positions])

        self.bad_boy_points = 0
        self.worst_offense = None
        self.num_offenders = 0
        worst_offense_score = 0
        for p in self.players:
            if p.selected_position_value not in bench_positions:
                if p.bad_boy_points > 0:
                    self.bad_boy_points += p.bad_boy_points
                    if p.selected_position_value == "DEF":
                        self.num_offenders += p.bad_boy_num_offenders
                    else:
                        self.num_offenders += 1
                    if p.bad_boy_points > worst_offense_score:
                        self.worst_offense = p.bad_boy_crime
                        worst_offense_score = p.bad_boy_points

        self.total_weight = sum([p.weight for p in self.players if p.selected_position_value not in bench_positions])
        self.tabbu = sum([p.tabbu for p in self.players if p.selected_position_value not in bench_positions])
        self.positions_filled_active = [p.selected_position_value for p in self.players if
                                        p.selected_position_value not in bench_positions]

        # calculate coaching efficiency
        self.coaching_efficiency = metrics.get("coaching_efficiency").execute_coaching_efficiency(
            self.name,
            self.players,
            self.score,
            self.positions_filled_active,
            int(week_counter),
            dq_eligible=dq_ce
        )

        # # retrieve luck and record
        self.luck = metrics.get("matchups_results").get(self.team_key).get("luck")
        self.record = metrics.get("matchups_results").get(self.team_key).get("record")

        # add new attributes to _keys list in order to allow ReportTeam objects to be output to stdout/console
        dict_keys = set(self.__dict__.keys()).difference({"extracted_data", "_index", "_keys"})
        self._keys.extend(dict_keys.difference(set(self._keys)))
