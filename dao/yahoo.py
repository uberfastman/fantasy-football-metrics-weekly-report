__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os

from yffpy.data import Data
from yffpy.models import Game, League, Matchup, Team, Manager, Player, RosterPosition, Stat
from yffpy.query import YahooFantasyFootballQuery

from dao.base import BaseLeague, BaseMatchup, BaseTeam, BaseManager, BasePlayer, BaseStat

# Suppress YahooFantasyFootballQuery debug logging
logging.getLogger("yffpy.query").setLevel(level=logging.INFO)


class LeagueData(object):

    def __init__(self,
                 config,
                 yahoo_game_id,
                 yahoo_league_id,
                 base_dir,
                 data_dir,
                 week_for_report,
                 week_validation_function,
                 save_data=True,
                 dev_offline=False):

        self.config = config
        self.data_dir = data_dir
        self.league_id = yahoo_league_id
        self.save_data = save_data
        self.dev_offline = dev_offline
        self.yahoo_data = Data(self.data_dir, save_data=save_data, dev_offline=dev_offline)
        yahoo_auth_dir = os.path.join(base_dir, config.get("Yahoo", "yahoo_auth_dir"))
        self.yahoo_query = YahooFantasyFootballQuery(yahoo_auth_dir, self.league_id, yahoo_game_id,
                                                     offline=dev_offline)

        if yahoo_game_id and yahoo_game_id != "nfl":
            yahoo_fantasy_game = self.yahoo_data.retrieve(str(yahoo_game_id) + "-game-metadata",
                                                          self.yahoo_query.get_game_metadata_by_game_id,
                                                          params={"game_id": yahoo_game_id},
                                                          data_type_class=Game)
        else:
            yahoo_fantasy_game = self.yahoo_data.retrieve("current-game-metadata",
                                                          self.yahoo_query.get_current_game_metadata,
                                                          data_type_class=Game)

        self.league_key = yahoo_fantasy_game.game_key + ".l." + self.league_id
        self.season = yahoo_fantasy_game.season

        # YAHOO API QUERY: run query to retrieve all league information, including current standings
        self.league_info = self.yahoo_data.retrieve(str(self.league_id) + "-league-info",
                                                    self.yahoo_query.get_league_info,
                                                    data_type_class=League,
                                                    new_data_dir=os.path.join(self.data_dir,
                                                                              str(self.season),
                                                                              str(self.league_id)))  # type: League

        self.season = self.league_info.season
        self.current_week = self.league_info.current_week
        self.playoff_slots = self.league_info.settings.num_playoff_teams
        self.num_regular_season_weeks = int(self.league_info.settings.playoff_start_week) - 1
        self.roster_positions = self.league_info.settings.roster_positions

        # validate user selection of week for which to generate report
        self.week_for_report = week_validation_function(self.config, week_for_report, self.current_week)

        # # YAHOO API QUERY: run yahoo queries for season team roster stats
        # self.rosters = {
        #     str(team.get("team").team_id): {
        #         str(player.get("player").player_id): player.get("player") for player in self.yahoo_data.retrieve(
        #             str(team.get("team").team_id) + "-" +
        #             str(team.get("team").name.decode("utf-8")).replace(" ", "_") + "-roster_stats",
        #             self.yahoo_query.get_team_roster_player_stats,
        #             params={"team_id": str(team.get("team").team_id)},
        #             new_data_dir=os.path.join(self.data_dir, str(self.season), str(self.league_id), "rosters")
        #         )
        #     } for team in self.league_info.standings.teams
        # }

        # YAHOO API QUERY: run yahoo queries to retrieve matchups by week for the entire season
        self.matchups_by_week = {}
        for wk in range(1, self.num_regular_season_weeks + 1):
            self.matchups_by_week[wk] = self.yahoo_data.retrieve(
                "week_" + str(wk) + "-matchups_by_week",
                self.yahoo_query.get_league_matchups_by_week,
                params={"chosen_week": wk},
                new_data_dir=os.path.join(self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk))
            )

        # YAHOO API QUERY: run yahoo queries to retrieve team rosters by week for the season up to the current week
        self.rosters_by_week = {}
        for wk in range(1, int(self.week_for_report) + 1):
            self.rosters_by_week[str(wk)] = {
                str(team.get("team").team_id):
                    self.yahoo_data.retrieve(
                        str(team.get("team").team_id) + "-" +
                        str(team.get("team").name.decode("utf-8")).replace(" ", "_") + "-roster",
                        self.yahoo_query.get_team_roster_player_info_by_week,
                        params={"team_id": str(team.get("team").team_id), "chosen_week": str(wk)},
                        new_data_dir=os.path.join(
                            self.data_dir, str(self.season), str(self.league_id), "week_" + str(wk), "rosters")
                    ) for team in self.league_info.standings.teams
            }

    def get_player_data(self, player_key, week):
        # YAHOO API QUERY: run query to retrieve stats for specific player for a chosen week
        return self.yahoo_data.retrieve(
            player_key,
            self.yahoo_query.get_player_stats_by_week,
            params={"player_key": player_key, "chosen_week": str(week)},
            new_data_dir=os.path.join(self.data_dir, str(self.season), self.league_id, "week_" + str(week), "players"),
            data_type_class=Player
        )

    def map_data_to_base(self, base_league_class):
        league = base_league_class(self.config, self.league_id, self.data_dir, self.week_for_report, self.save_data,
                                   self.dev_offline)  # type: BaseLeague

        league.name = self.league_info.name
        league.current_week = int(self.current_week)
        league.season = self.season
        league.num_teams = int(self.league_info.num_teams)
        league.num_playoff_slots = int(self.playoff_slots)
        league.num_regular_season_weeks = int(self.num_regular_season_weeks)
        league.url = self.league_info.url

        league.player_data_by_week_function = self.get_player_data
        league.player_data_by_week_key = "player_points_value"

        league.bench_positions = [
            str(bench_position) for bench_position in self.config.get("Configuration", "bench_positions").split(",")]

        for position in self.roster_positions:
            pos = position.get("roster_position")  # type: RosterPosition

            pos_name = pos.position
            pos_count = int(pos.count)
            while pos_count > 0:
                if pos_name not in league.bench_positions:
                    league.active_positions.append(pos_name)
                pos_count -= 1

            if pos_name == "W/R":
                league.flex_positions = ["WR", "RB"]
            if pos_name == "W/R/T":
                league.flex_positions = ["WR", "RB", "TE"]
            if pos_name == "Q/W/R/T":
                league.flex_positions = ["QB", "WR", "RB", "TE"]

            if "/" in pos_name:
                pos_name = "FLEX"

            league.roster_positions.append(pos_name)
            league.roster_position_counts[pos_name] = pos.count

        for week, matchups in self.matchups_by_week.items():
            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []
            for matchup in matchups:
                y_matchup = matchup.get("matchup")  # type: Matchup
                base_matchup = BaseMatchup()

                base_matchup.week_for_report = int(y_matchup.week)
                base_matchup.complete = True if y_matchup.status == "postevent" else False
                base_matchup.tied = True if (y_matchup.is_tied and int(y_matchup.is_tied) == 1) else False

                for team in y_matchup.teams:  # type: dict
                    y_team = team.get("team")  # type: Team
                    base_team = BaseTeam()

                    base_team.week_for_report = int(y_matchup.week)
                    base_team.name = y_team.name
                    base_team.num_moves = y_team.number_of_moves
                    base_team.num_trades = y_team.number_of_trades

                    if isinstance(y_team.managers, list):
                        y_team_manager = y_team.managers
                    else:
                        y_team_manager = [y_team.managers]

                    for manager in y_team_manager:
                        y_manager = manager.get("manager")  # type: Manager
                        base_manager = BaseManager()

                        base_manager.manager_id = str(y_manager.manager_id)
                        base_manager.email = y_manager.email
                        base_manager.name = y_manager.nickname

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name for manager in base_team.managers])

                    # TODO: change y_team.team_id to y_team.team_key
                    base_team.team_id = str(y_team.team_id)
                    base_team.team_key = y_team.team_key
                    base_team.points = float(y_team.points)
                    base_team.projected_points = float(y_team.projected_points)
                    base_team.waiver_priority = y_team.waiver_priority
                    base_team.url = y_team.url

                    # add team to matchup teams
                    base_matchup.teams.append(base_team)

                    # add team to league teams by week
                    league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    if base_team.team_key == y_matchup.winner_team_key:
                        base_matchup.winner = base_team
                    else:
                        base_matchup.loser = base_team

                # add matchup to league matchups by week
                league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in self.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                league_team = league.teams_by_week.get(str(week)).get(str(team_id))  # type: BaseTeam
                for player in roster:
                    y_player_for_week = player.get("player")  # type: Player
                    base_player = BasePlayer()

                    base_player.week_for_report = int(week)
                    base_player.player_id = y_player_for_week.player_key
                    base_player.bye_week = int(y_player_for_week.bye)
                    base_player.display_position = y_player_for_week.display_position
                    base_player.nfl_team_id = y_player_for_week.editorial_team_key
                    base_player.nfl_team_abbr = y_player_for_week.editorial_team_abbr
                    base_player.nfl_team_name = y_player_for_week.editorial_team_full_name
                    base_player.first_name = y_player_for_week.first_name
                    base_player.last_name = y_player_for_week.last_name
                    base_player.full_name = y_player_for_week.full_name
                    base_player.headshot_url = y_player_for_week.headshot_url
                    base_player.owner_team_id = y_player_for_week.ownership.owner_team_key
                    base_player.owner_team_id = y_player_for_week.ownership.owner_team_name
                    base_player.percent_owned = float(
                        y_player_for_week.percent_owned_value) if y_player_for_week.percent_owned_value else 0
                    base_player.points = float(y_player_for_week.player_points_value)
                    base_player.position_type = y_player_for_week.position_type
                    base_player.primary_position = y_player_for_week.primary_position
                    base_player.selected_position = y_player_for_week.selected_position_value
                    base_player.selected_position_is_flex = True if int(
                        y_player_for_week.selected_position.is_flex) == 1 else False
                    base_player.status = y_player_for_week.status

                    eligible_positions = y_player_for_week.eligible_positions
                    if isinstance(eligible_positions, dict):
                        eligible_positions = [eligible_positions]

                    for position in eligible_positions:
                        pos = position.get("position")
                        base_player.eligible_positions.append(pos)

                    for stat in y_player_for_week.stats:
                        y_stat = stat.get("stat")  # type: Stat
                        base_stat = BaseStat()

                        base_stat.stat_id = y_stat.stat_id
                        base_stat.name = y_stat.name
                        base_stat.value = y_stat.value

                        base_player.stats.append(base_stat)

                    # add player to team roster
                    league_team.roster.append(base_player)

                    # add player to league players by week
                    league.players_by_week[str(week)][base_player.player_id] = base_player

        for ranked_team in self.league_info.standings.teams:
            y_team = ranked_team.get("team")  # type: Team

            team = league.teams_by_week.get(str(self.week_for_report)).get(str(y_team.team_id))  # type: BaseTeam

            team.wins = int(y_team.wins)
            team.losses = int(y_team.losses)
            team.ties = int(y_team.ties)
            team.percentage = float(y_team.percentage)
            if y_team.streak_type == "win":
                team.streak_type = "W"
            elif y_team.streak_type == "loss":
                team.streak_type = "L"
            else:
                team.streak_type = "T"
            team.streak_len = int(y_team.streak_length)
            team.streak_str = str(team.streak_type) + "-" + str(y_team.streak_length)
            team.points_against = float(y_team.points_against)
            team.points_for = float(y_team.points_for)
            team.rank = int(y_team.rank)

        league.current_standings = sorted(
            league.teams_by_week.get(str(self.week_for_report)).values(), key=lambda x: x.rank)

        return league
