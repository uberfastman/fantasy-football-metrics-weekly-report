__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import collections
import os
import logging
# import sys

from yffpy.models import Game, League, Settings, Standings

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from calculate.playoff_probabilities import PlayoffProbabilities

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# Suppress YahooFantasyFootballQuery debug logging
logging.getLogger("yffpy.query").setLevel(level=logging.INFO)


def user_week_input_validation(config, week, retrieved_current_week):
    # user input validation
    if week:
        chosen_week = week
    else:
        chosen_week = config.get("Fantasy_Football_Report_Settings", "chosen_week")
    try:
        current_week = retrieved_current_week
        if chosen_week == "default":
            if (int(current_week) - 1) > 0:
                chosen_week = str(int(current_week) - 1)
            else:
                first_week_incomplete = input(
                    "The first week of the season is not yet complete. "
                    "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                if first_week_incomplete == "y":
                    chosen_week = current_week
                elif first_week_incomplete == "n":
                    raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")

        elif 0 < int(chosen_week) < 18:
            if 0 < int(chosen_week) <= int(current_week) - 1:
                chosen_week = chosen_week
            else:
                incomplete_week = input(
                    "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                if incomplete_week == "y":
                    chosen_week = chosen_week
                elif incomplete_week == "n":
                    raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")
        else:
            raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")
    except ValueError:
        raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")

    return chosen_week


class RetrieveYffLeagueData(object):

    def __init__(self, config, yahoo_data, yahoo_query, yahoo_game_id, yahoo_league_id, data_dir, selected_week):

        self.config = config
        self.data_dir = data_dir

        if yahoo_game_id and yahoo_game_id != "nfl":
            yahoo_fantasy_game = yahoo_data.retrieve(str(yahoo_game_id) + "-game-metadata",
                                                     yahoo_query.get_game_metadata_by_game_id,
                                                     params={"game_id": yahoo_game_id},
                                                     data_type_class=Game)
        else:
            yahoo_fantasy_game = yahoo_data.retrieve("current-game-metadata",
                                                     yahoo_query.get_current_game_metadata,
                                                     data_type_class=Game)

        self.league_key = yahoo_fantasy_game.game_key + ".l." + yahoo_league_id
        self.season = yahoo_fantasy_game.season

        # print(self.league_key)
        # sys.exit()

        league_metadata = yahoo_data.retrieve(str(yahoo_league_id) + "-league-metadata",
                                              yahoo_query.get_league_metadata,
                                              data_type_class=League,
                                              new_data_dir=os.path.join(self.data_dir,
                                                                        str(self.season),
                                                                        self.league_key))
        self.name = league_metadata.name

        # print(self.name)
        # print(league_metadata)
        # sys.exit()

        league_settings = yahoo_data.retrieve(str(yahoo_league_id) + "-league-settings",
                                              yahoo_query.get_league_settings,
                                              data_type_class=Settings,
                                              new_data_dir=os.path.join(self.data_dir,
                                                                        str(self.season),
                                                                        self.league_key))
        # print(league_settings)
        # sys.exit()

        self.playoff_slots = league_settings.num_playoff_teams
        self.num_regular_season_weeks = int(league_settings.playoff_start_week) - 1
        self.roster_positions = league_settings.roster_positions
        self.roster_positions_by_type = self.get_roster_slots(self.roster_positions)

        # print(self.playoff_slots)
        # print(self.num_regular_season_weeks)
        # print(self.roster_positions)
        # sys.exit()

        self.standings = yahoo_data.retrieve(str(yahoo_league_id) + "-league-standings",
                                             yahoo_query.get_league_standings,
                                             data_type_class=Standings,
                                             new_data_dir=os.path.join(self.data_dir,
                                                                       str(self.season),
                                                                       self.league_key))
        # print(self.league_standings_data)
        # sys.exit()

        self.teams = yahoo_data.retrieve(str(yahoo_league_id) + "-league-teams",
                                         yahoo_query.get_league_teams,
                                         new_data_dir=os.path.join(self.data_dir,
                                                                   str(self.season),
                                                                   self.league_key))
        # print(self.teams)
        # sys.exit()

        # validate user selection of week for which to generate report
        self.chosen_week = user_week_input_validation(self.config, selected_week, league_metadata.current_week)

        # run yahoo queries requiring chosen week
        self.matchups_by_week = {}
        for wk in range(1, self.num_regular_season_weeks + 1):
            self.matchups_by_week[wk] = yahoo_data.retrieve("week_" + str(wk) + "-matchups_by_week",
                                                            yahoo_query.get_league_matchups_by_week,
                                                            params={"chosen_week": wk},
                                                            new_data_dir=os.path.join(self.data_dir,
                                                                                      str(self.season),
                                                                                      self.league_key,
                                                                                      "week_" + str(wk)))
        # print(self.matchups_by_week)
        # sys.exit()

        self.rosters_by_week = {}
        for wk in range(1, int(self.chosen_week) + 1):
            self.rosters_by_week[str(wk)] = {
                str(team.get("team").team_id):
                    yahoo_data.retrieve(
                        str(team.get("team").team_id) + "-" +
                        str(team.get("team").name.decode("utf-8")).replace(" ", "_") + "-roster",
                        yahoo_query.get_team_roster_player_stats_by_week,
                        params={"team_id": str(team.get("team").team_id), "chosen_week": str(wk)},
                        new_data_dir=os.path.join(
                            self.data_dir, str(self.season), self.league_key, "week_" + str(wk), "rosters")
                    ) for team in self.teams
            }
        # print(self.rosters_by_week.keys())
        # sys.exit()

    @staticmethod
    def get_roster_slots(roster_positions):

        position_counts = collections.defaultdict(int)
        positions_active = []
        positions_flex = []
        positions_bench = ["BN", "IR"]
        for roster_position in roster_positions:

            roster_position = roster_position.get("roster_position")

            position_name = roster_position.position
            position_count = int(roster_position.count)

            count = position_count
            while count > 0:
                if position_name not in positions_bench:
                    positions_active.append(position_name)
                count -= 1

            if position_name == "W/R":
                positions_flex = ["WR", "RB"]
            if position_name == "W/R/T":
                positions_flex = ["WR", "RB", "TE"]
            if position_name == "Q/W/R/T":
                positions_flex = ["QB", "WR", "RB", "TE"]

            if "/" in position_name:
                position_name = "FLEX"

            position_counts[position_name] += position_count

        roster_positions_by_type = {
            "position_counts": position_counts,
            "positions_active": positions_active,
            "positions_flex": positions_flex,
            "positions_bench": positions_bench
        }

        # print(self.roster_positions)
        # sys.exit()

        return roster_positions_by_type

    def get_playoff_probs(self, save_data=False, playoff_prob_sims=None, dev_offline=False, recalculate=True):
        # TODO: UPDATE USAGE OF recalculate PARAM (could use self.dev_offline)

        playoff_probs = PlayoffProbabilities(
            int(playoff_prob_sims) if playoff_prob_sims is not None else self.config.getint("Fantasy_Football_Report_Settings", "num_playoff_simulations"),
            # self.config.getint("Fantasy_Football_Report_Settings", "num_playoff_simulations"),
            self.num_regular_season_weeks,
            self.playoff_slots,
            data_dir=os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=save_data,
            recalculate=recalculate
        )
        # print(self.playoff_probs_data)
        # sys.exit()
        return playoff_probs

    def get_bad_boy_stats(self, save_data=False, dev_offline=False):
        bad_boy_stats = BadBoyStats(
            os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=save_data,
            dev_offline=dev_offline)
        # print(self.bad_boy_stats)
        # sys.exit()
        return bad_boy_stats

    def get_beef_stats(self, save_data=False, dev_offline=False):

        beef_stats = BeefStats(
            os.path.join(self.data_dir, str(self.season), self.league_key),
            save_data=save_data,
            dev_offline=dev_offline)
        # print(self.beef_rank)
        # sys.exit()
        return beef_stats
