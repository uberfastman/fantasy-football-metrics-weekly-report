__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import logging
import os
import sys

from yffpy.models import Manager as YffManager
from yffpy.models import Matchup as YffMatchup
from yffpy.models import Player as YffPlayer
from yffpy.models import RosterPosition as YffRosterPosition
from yffpy.models import Stat as YffStat
from yffpy.models import Team as YffTeam

from calculate.bad_boy_stats import BadBoyStats
from calculate.beef_stats import BeefStats
from dao import yahoo
from dao.base import League, Matchup, Team, Manager, Player, Stat

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def league_data_class_factory(config, game_id, league_id, base_dir, data_dir, week_for_report, save_data, dev_offline):
    platform = config.get("Configuration", "platform")

    if platform == "yahoo":
        yahoo_auth_dir = os.path.join(base_dir, config.get("Yahoo", "yahoo_auth_dir"))
        yahoo_league = yahoo.LeagueData(
            config=config,
            yahoo_game_id=game_id,
            yahoo_league_id=league_id,
            yahoo_auth_dir=yahoo_auth_dir,
            data_dir=data_dir,
            week_for_report=week_for_report,
            week_validation_function=user_week_input_validation,
            save_data=save_data,
            dev_offline=dev_offline
        )

        league = League(config, league_id, data_dir, yahoo_league.week_for_report, yahoo_auth_dir, save_data,
                        dev_offline)

        league.name = yahoo_league.league_info.name
        league.current_week = int(yahoo_league.current_week)
        league.season = yahoo_league.season
        league.num_teams = int(yahoo_league.league_info.num_teams)
        league.num_playoff_slots = int(yahoo_league.playoff_slots)
        league.num_regular_season_weeks = int(yahoo_league.num_regular_season_weeks)
        league.url = yahoo_league.league_info.url

        league.bench_positions = ["BN", "IR"]
        for position in yahoo_league.roster_positions:
            pos = position.get("roster_position")  # type: YffRosterPosition

            pos_name = pos.position

            if pos_name not in league.bench_positions:
                league.active_positions.append(pos_name)

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

        for week, matchups in yahoo_league.matchups_by_week.items():
            league.teams_by_week[str(week)] = {}
            league.matchups_by_week[str(week)] = []
            for matchup in matchups:
                y_matchup = matchup.get("matchup")  # type: YffMatchup
                base_matchup = Matchup()

                base_matchup.week_for_report = int(y_matchup.week)
                base_matchup.complete = True if y_matchup.status == "postevent" else False
                base_matchup.tied = True if (y_matchup.is_tied and int(y_matchup.is_tied) == 1) else False

                for team in y_matchup.teams:  # type: dict
                    y_team = team.get("team")  # type: YffTeam
                    base_team = Team()

                    base_team.week_for_report = int(y_matchup.week)
                    base_team.name = y_team.name
                    base_team.num_moves = int(y_team.number_of_moves)
                    base_team.num_trades = int(y_team.number_of_trades)

                    if isinstance(y_team.managers, list):
                        y_team_manager = y_team.managers
                    else:
                        y_team_manager = [y_team.managers]

                    for manager in y_team_manager:
                        y_manager = manager.get("manager")  # type: YffManager
                        base_manager = Manager()

                        base_manager.manager_id = str(y_manager.manager_id)
                        base_manager.email = y_manager.email
                        base_manager.name = y_manager.nickname

                        base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name for manager in base_team.managers])

                    # TODO: change y_team.team_id to y_team.team_key
                    base_team.team_id = str(y_team.team_id)
                    base_team.team_key = str(y_team.team_key)
                    base_team.points = float(y_team.points)
                    base_team.projected_points = float(y_team.projected_points)
                    base_team.waiver_priority = int(y_team.waiver_priority)
                    base_team.url = str(y_team.url)

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

        for week, rosters in yahoo_league.rosters_by_week.items():
            league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                league_team = league.teams_by_week.get(str(week)).get(str(team_id))  # type: Team
                for player in roster:
                    y_player = player.get("player")  # type: YffPlayer
                    base_player = Player()

                    base_player.week_for_report = int(week)
                    base_player.player_id = str(y_player.player_key)
                    base_player.bye_week = int(y_player.bye)
                    base_player.display_position = str(y_player.display_position)
                    base_player.nfl_team_id = str(y_player.editorial_team_key)
                    base_player.nfl_team_abbr = str(y_player.editorial_team_abbr)
                    base_player.nfl_team_name = str(y_player.editorial_team_full_name)
                    base_player.first_name = str(y_player.first_name)
                    base_player.last_name = str(y_player.last_name)
                    base_player.full_name = str(y_player.full_name)
                    base_player.headshot_url = str(y_player.headshot_url)
                    base_player.owner_team_id = str(y_player.ownership.owner_team_key)
                    base_player.owner_team_id = str(y_player.ownership.owner_team_name)
                    base_player.percent_owned = float(
                        y_player.percent_owned_value) if y_player.percent_owned_value else 0
                    base_player.points = float(y_player.player_points_value)
                    base_player.position_type = str(y_player.position_type)
                    base_player.primary_position = str(y_player.primary_position)
                    base_player.selected_position = str(y_player.selected_position_value)
                    base_player.selected_position_is_flex = True if int(
                        y_player.selected_position.is_flex) == 1 else False
                    base_player.status = str(y_player.status)

                    eligible_positions = y_player.eligible_positions
                    if isinstance(eligible_positions, dict):
                        eligible_positions = [eligible_positions]

                    for position in eligible_positions:
                        pos = position.get("position")
                        base_player.eligible_positions.append(pos)

                    for stat in y_player.stats:
                        y_stat = stat.get("stat")  # type: YffStat
                        base_stat = Stat()

                        base_stat.stat_id = y_stat.stat_id
                        base_stat.name = y_stat.name
                        base_stat.value = y_stat.value

                        base_player.stats.append(base_stat)

                    # add player to team roster
                    league_team.roster.append(base_player)

                    # add player to league players by week
                    league.players_by_week[str(week)][base_player.player_id] = base_player

        for ranked_team in yahoo_league.league_info.standings.teams:
            y_team = ranked_team.get("team")  # type: YffTeam

            team = league.teams_by_week.get(str(yahoo_league.week_for_report)).get(str(y_team.team_id))  # type: Team

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
            league.teams_by_week.get(str(yahoo_league.week_for_report)).values(), key=lambda x: x.rank)

        return league

    else:
        logger.error(
            "Generating fantasy football reports for the \"{}\" fantasy football platform is not currently supported."
            "Please change your settings in config.ini and try again.".format(platform))
        sys.exit()


def user_week_input_validation(config, week, retrieved_current_week):
    # user input validation
    if week:
        week_for_report = week
    else:
        week_for_report = config.getint("Configuration", "week_for_report")
    try:
        current_week = retrieved_current_week
        if week_for_report == "default":
            if (int(current_week) - 1) > 0:
                week_for_report = str(int(current_week) - 1)
            else:
                first_week_incomplete = input(
                    "The first week of the season is not yet complete. "
                    "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                if first_week_incomplete == "y":
                    week_for_report = current_week
                elif first_week_incomplete == "n":
                    raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")

        elif 0 < int(week_for_report) < 18:
            if 0 < int(week_for_report) <= int(current_week) - 1:
                week_for_report = week_for_report
            else:
                incomplete_week = input(
                    "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                if incomplete_week == "y":
                    week_for_report = week_for_report
                elif incomplete_week == "n":
                    raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")
        else:
            raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")
    except ValueError:
        raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")

    return int(week_for_report)


def add_report_player_stats(player,  # type: Player
                            bench_positions,
                            metrics):
    player.bad_boy_crime = str()
    player.bad_boy_points = int()
    player.bad_boy_num_offenders = int()
    player.weight = float()
    player.tabbu = float()

    if player.selected_position not in bench_positions:
        bad_boy_stats = metrics.get("bad_boy_stats")  # type: BadBoyStats
        player.bad_boy_crime = bad_boy_stats.get_player_bad_boy_crime(
            player.full_name, player.nfl_team_abbr, player.primary_position)
        player.bad_boy_points = bad_boy_stats.get_player_bad_boy_points(
            player.full_name, player.nfl_team_abbr, player.primary_position)
        player.bad_boy_num_offenders = bad_boy_stats.get_player_bad_boy_num_offenders(
            player.full_name, player.nfl_team_abbr, player.primary_position)

        beef_stats = metrics.get("beef_stats")  # type: BeefStats
        player.weight = beef_stats.get_player_weight(player.first_name, player.last_name, player.nfl_team_abbr)
        player.tabbu = beef_stats.get_player_tabbu(player.first_name, player.last_name, player.nfl_team_abbr)

    return player


def add_report_team_stats(team,  # type: Team
                          league,  # type: League
                          week_counter,
                          metrics,
                          dq_ce):

    team.name = team.name.decode("utf-8")
    bench_positions = league.get_roster_slots_by_type().get("positions_bench")

    # if len(team.managers) > 1:
    #     team.manager_str = ", ".join([manager.name for manager in team.managers])
    # else:
    #     team.manager_str = team.managers[0].name

    for player in team.roster:
        add_report_player_stats(player, bench_positions, metrics)

    starting_lineup_points = round(
        sum([p.points for p in team.roster if p.selected_position not in bench_positions]), 2)
    # confirm total starting lineup points is the same as team points
    if team.points != starting_lineup_points:
        logger.warning(
            "Team {} points ({}) are not equal to sum of team starting lineup points ({}). Check data!".format(
                team.name, team.points, starting_lineup_points))

    team.bench_points = round(sum([p.points for p in team.roster if p.selected_position in bench_positions]), 2)

    team.bad_boy_points = 0
    team.worst_offense = None
    team.num_offenders = 0
    team.worst_offense_score = 0
    for p in team.roster:
        if p.selected_position not in bench_positions:
            if p.bad_boy_points > 0:
                team.bad_boy_points += p.bad_boy_points
                if p.selected_position == "DEF":
                    team.num_offenders += p.bad_boy_num_offenders
                else:
                    team.num_offenders += 1
                if p.bad_boy_points > team.worst_offense_score:
                    team.worst_offense = p.bad_boy_crime
                    team.worst_offense_score = p.bad_boy_points

    team.total_weight = sum([p.weight for p in team.roster if p.selected_position not in bench_positions])
    team.tabbu = sum([p.tabbu for p in team.roster if p.selected_position not in bench_positions])
    team.positions_filled_active = list(set([p.selected_position for p in team.roster if
                                             p.selected_position not in bench_positions]))

    # calculate coaching efficiency
    team.coaching_efficiency = metrics.get("coaching_efficiency").execute_coaching_efficiency(
        team.name,
        team.roster,
        team.points,
        team.positions_filled_active,
        int(week_counter),
        dq_eligible=dq_ce
    )

    # # retrieve luck and record
    team.luck = metrics.get("matchups_results").get(team.team_key).get("luck")
    team.record = metrics.get("matchups_results").get(team.team_key).get("record")

    return team
