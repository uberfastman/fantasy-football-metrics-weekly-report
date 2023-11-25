__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import datetime
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Dict, Callable, Union

import requests
from bs4 import BeautifulSoup

from dao.base import BaseMatchup, BaseTeam, BaseRecord, BaseManager, BasePlayer, BaseStat
from dao.platforms.base.base import BaseLeagueData
from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)

# Suppress Fleaflicker API debug logging
logger.setLevel(level=logging.INFO)


# noinspection DuplicatedCode
class LeagueData(BaseLeagueData):

    def __init__(self, base_dir: Union[Path, None], data_dir: Path, league_id: str,
                 season: int, start_week: int, week_for_report: int, get_current_nfl_week_function: Callable,
                 week_validation_function: Callable, save_data: bool = True, offline: bool = False):
        super().__init__(
            "Fleaflicker",
            f"https://www.fleaflicker.com",
            base_dir,
            data_dir,
            league_id,
            season,
            start_week,
            week_for_report,
            get_current_nfl_week_function,
            week_validation_function,
            save_data,
            offline
        )

    def _scrape(self, url: str, file_dir: Path, filename: str):

        file_path = Path(file_dir) / filename

        if not self.league.offline:
            logger.debug(f"Scraping Fleaflicker data from endpoint: {url}")

            user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 "
                "Safari/605.1.15"
            )
            headers = {"user-agent": user_agent}
            response = requests.get(url, headers)

            html_soup = BeautifulSoup(response.text, "html.parser")
            logger.debug(f"Response (HTML): {html_soup}")
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as data_in:
                    html_soup = BeautifulSoup(data_in.read(), "html.parser")
            except FileNotFoundError:
                logger.error(
                    f"FILE {file_path} DOES NOT EXIST. CANNOT LOAD DATA LOCALLY WITHOUT HAVING PREVIOUSLY SAVED DATA!"
                )
                sys.exit(1)

        if self.league.save_data:
            logger.debug(f"Saving Fleaflicker data scraped from endpoint: {url}")
            if not Path(file_dir).exists():
                os.makedirs(file_dir)

            with open(file_path, "w", encoding="utf-8") as data_out:
                data_out.write(html_soup.prettify())

        return html_soup

    def map_data_to_base(self):
        logger.debug(f"Retrieving {self.platform_display} league data and mapping it to base objects.")

        self.league.url = f"{self.base_url}/nfl/leagues/{self.league.league_id}"
        # noinspection PyUnusedLocal
        scraped_league_info = self._scrape(
            self.league.url,
            Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id),
            f"{self.league.league_id}-league-info.html"
        )

        scraped_league_scores = self._scrape(
            f"{self.league.url}/scores",
            Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id),
            f"{self.league.league_id}-league-scores.html"
        )

        try:
            scraped_current_week = int(scraped_league_scores.findAll(
                text=re.compile(".*This Week.*")
            )[-1].parent.findNext("li").text.strip().split(" ")[-1]) - 1
        except (IndexError, AttributeError) as e:
            logger.error(e)
            scraped_current_week = None

        scraped_league_rules = self._scrape(
            f"{self.league.url}/rules",
            Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id),
            f"{self.league.league_id}-league-rules.html"
        )

        elements = scraped_league_rules.findAll(["dt", "dd"])
        for elem in elements:
            if elem.text.strip() == "Playoffs":

                if elements[elements.index(elem) + 1].span:
                    self.league.num_playoff_slots = int(elements[elements.index(elem) + 1].span.text.strip())
                else:
                    self.league.num_playoff_slots = 0

                playoff_weeks_elements = elements[elements.index(elem) + 1].findAll(text=True, recursive=False)
                if any((text.strip() and "Weeks" in text) for text in playoff_weeks_elements):
                    for text in playoff_weeks_elements:
                        if text.strip() and "Weeks" in text:
                            for txt in text.split():
                                if "-" in txt:
                                    self.league.num_regular_season_weeks = int(txt.split("-")[0]) - 1
                elif self.league.num_playoff_slots == 0:
                    # TODO: figure out how to get total number of regular season weeks when league has no playoffs
                    self.league.num_regular_season_weeks = 18 if int(self.league.season) > 2020 else 17
                else:
                    self.league.num_regular_season_weeks = settings.num_regular_season_weeks
                break
            else:
                self.league.num_playoff_slots = settings.num_playoff_slots
                self.league.num_regular_season_weeks = settings.num_regular_season_weeks

        # TODO: how to get league rules for LAST YEAR from Fleaflicker API
        league_rules = self.query(
            f"https://www.fleaflicker.com/api/FetchLeagueRules?leagueId={self.league.league_id}",
            (Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id)
             / f"{self.league.league_id}-league-rules.json")
        )

        league_standings = self.query(
            (f"https://www.fleaflicker.com/api/FetchLeagueStandings"
             f"?leagueId={self.league.league_id}{f'&season={self.league.season}' if self.league.season else ''}"),
            (Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id)
             / f"{self.league.league_id}-league-standings.json")
        )

        league_info = league_standings.get("league")

        league_teams = {}
        ranked_league_teams = []
        for division in league_standings.get("divisions"):
            self.league.divisions[str(division.get("id"))] = division.get("name")
            self.league.num_divisions += 1
            for team in division.get("teams"):
                team["division_id"] = division.get("id")
                team["division_name"] = division.get("name")
                league_teams[team.get("id")] = team
                ranked_league_teams.append(team)

        ranked_league_teams.sort(
            key=lambda x: x.get("recordOverall").get("rank") if x.get("recordOverall").get("rank") else 0
        )

        median_score_by_week = {}
        matchups_by_week = {}
        for wk in range(self.start_week, int(self.league.num_regular_season_weeks) + 1):
            matchups_by_week[str(wk)] = self.query(
                (f"https://www.fleaflicker.com/api/FetchLeagueScoreboard"
                 f"?leagueId={self.league.league_id}&scoringPeriod={wk}"
                 f"{f'&season={self.league.season}' if self.league.season else ''}"),
                (Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id) / f"week_{wk}"
                 / f"week_{wk}-scoreboard.json")
            )

            if int(wk) <= self.league.week_for_report:
                scores = []
                for matchup in matchups_by_week[str(wk)].get("games"):
                    for key in ["home", "away"]:
                        team_score = matchup.get(key + "Score").get("score").get("value")
                        if team_score:
                            scores.append(team_score)

                weekly_median = round(median(scores), 2) if scores else None

                if weekly_median:
                    median_score_by_week[str(wk)] = weekly_median
                else:
                    median_score_by_week[str(wk)] = 0

        rosters_by_week = {}
        for wk in range(self.start_week, self.league.week_for_report + 1):
            rosters_by_week[str(wk)] = {
                str(team.get("id")): self.query(
                    (f"https://www.fleaflicker.com/api/FetchRoster"
                     f"?leagueId={self.league.league_id}&teamId={team.get('id')}&scoringPeriod={wk}"
                     f"{f'&season={self.league.season}' if self.league.season else ''}"),
                    (Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id) / f"week_{wk}"
                     / "rosters" / f"{team.get('id')}-{team.get('name').replace(' ', '_')}-roster.json")
                ) for team in ranked_league_teams
            }

        # TODO: how to get transactions for LAST YEAR from Fleaflicker API...?
        league_activity = self.query(
            f"https://www.fleaflicker.com/api/FetchLeagueActivity?leagueId={self.league.league_id}",
            (Path(self.league.data_dir) / str(self.league.season) / str(self.league.league_id)
             / f"{self.league.league_id}-league-transactions.json")
        )

        league_transactions_by_team = defaultdict(dict)
        for activity in league_activity.get("items"):

            epoch_milli = float(activity.get("timeEpochMilli"))
            timestamp = datetime.datetime.fromtimestamp(epoch_milli / 1000)

            season_start = datetime.datetime(self.league.season, 9, 1)
            season_end = datetime.datetime(self.league.season + 1, 3, 1)

            if season_start < timestamp < season_end:
                if activity.get("transaction"):
                    if activity.get("transaction").get("type"):
                        transaction_type = activity.get("transaction").get("type")
                    else:
                        transaction_type = "TRANSACTION_ADD"

                    is_move = False
                    is_trade = False
                    if "TRADE" in transaction_type:
                        is_trade = True
                    elif any(transaction_str in transaction_type for transaction_str in ["CLAIM", "ADD", "DROP"]):
                        is_move = True

                    if not league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))]:
                        league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))] = {
                            "transactions": [transaction_type],
                            "moves": 1 if is_move else 0,
                            "trades": 1 if is_trade else 0
                        }
                    else:
                        league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))][
                            "transactions"].append(transaction_type)
                        league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))][
                            "moves"] += 1 if is_move else 0
                        league_transactions_by_team[str(activity.get("transaction").get("team").get("id"))][
                            "trades"] += 1 if is_trade else 0

        self.league.name = league_info.get("name")
        self.league.week = int(scraped_current_week) if scraped_current_week else self.current_week
        # TODO: figure out how to get league starting week
        self.league.start_week = self.start_week
        self.league.num_teams = int(league_info.get("size"))
        self.league.has_divisions = self.league.num_divisions > 0
        # TODO: FIGURE OUT WHERE FLEAFLICKER EXPOSES THIS! Fleaflicker supports both MEDIAN and MEAN games
        self.league.has_median_matchup = False
        self.league.median_score = 0
        self.league.faab_budget = int(league_info.get("defaultWaiverBudget", 0))
        self.league.is_faab = self.league.faab_budget > 0

        # self.league.player_data_by_week_function = None
        # self.league.player_data_by_week_key = None

        for position in league_rules.get("rosterPositions"):
            pos_attributes = self.position_mapping.get(position.get("label"))
            pos_name = pos_attributes.get("base")
            if position.get("start"):
                pos_count = int(position.get("start"))
            elif position.get("label") == "BN":
                pos_count = int(position.get("max")) if position.get("max") else 0
            else:
                pos_count = 0

            if pos_attributes.get("is_flex"):
                self.league.__setattr__(
                    pos_attributes.get("league_positions_attribute"),
                    pos_attributes.get("positions")
                )

            self.league.roster_positions.append(pos_name)
            self.league.roster_position_counts[pos_name] = pos_count
            self.league.roster_active_slots.extend(
                [pos_name] * pos_count
                if pos_name not in self.league.bench_positions
                else []
            )

        league_median_records_by_team = {}
        for week, matchups in matchups_by_week.items():
            matchups_week = matchups.get("schedulePeriod").get("value")
            matchups = matchups.get("games")

            self.league.teams_by_week[str(week)] = {}
            self.league.matchups_by_week[str(week)] = []

            for matchup in matchups:
                base_matchup = BaseMatchup()

                base_matchup.week = int(matchups_week)
                base_matchup.complete = True if bool(matchup.get("isFinalScore")) else False
                base_matchup.tied = True if matchup.get("homeResult") == "TIE" else False

                for key in ["home", "away"]:
                    team_data: Dict = matchup.get(key)
                    base_team = BaseTeam()

                    opposite_key = "away" if key == "home" else "home"
                    team_division = league_teams[team_data.get("id")].get("division_id")
                    opponent_division = league_teams[matchup.get(opposite_key).get("id")].get("division_id")
                    if team_division and opponent_division and team_division == opponent_division:
                        base_matchup.division_matchup = True

                    base_team.week = int(matchups_week)
                    base_team.name = team_data.get("name")

                    managers = league_teams[team_data.get("id")].get("owners")
                    if managers:
                        for manager in managers:
                            base_manager = BaseManager()

                            base_manager.manager_id = str(manager.get("id"))
                            base_manager.email = None
                            base_manager.name = manager.get("displayName")

                            base_team.managers.append(base_manager)

                    base_team.manager_str = ", ".join([manager.name_str for manager in base_team.managers])

                    base_team.team_id = str(team_data.get("id"))
                    base_team.points = float(matchup.get(key + "Score", {}).get("score", {}).get("value", 0))
                    base_team.projected_points = None

                    # TODO: currently the fleaflicker API call only returns 1st PAGE of transactions... figure this out!
                    base_team.num_moves = f"{league_transactions_by_team[str(base_team.team_id)].get('moves', 0)}*"
                    base_team.num_trades = f"{league_transactions_by_team[str(base_team.team_id)].get('trades', 0)}*"

                    base_team.waiver_priority = team_data.get("waiverPosition", 0)
                    self.league.has_waiver_priorities = base_team.waiver_priority > 0
                    base_team.faab = team_data.get("waiverAcquisitionBudget", {}).get("value", 0)
                    base_team.url = (
                        f"https://www.fleaflicker.com"
                        f"/nfl/leagues/{self.league.league_id}/teams/{str(team_data.get('id'))}"
                    )

                    if team_data.get("streak").get("value"):
                        if team_data.get("streak").get("value") > 0:
                            streak_type = "W"
                        elif team_data.get("streak").get("value") < 0:
                            streak_type = "L"
                        else:
                            streak_type = "T"
                    else:
                        streak_type = "T"

                    base_team.division = team_division
                    base_team.current_record = BaseRecord(
                        wins=int(team_data.get("recordOverall", {}).get("wins", 0)),
                        losses=int(team_data.get("recordOverall", {}).get("losses", 0)),
                        ties=int(team_data.get("recordOverall", {}).get("ties", 0)),
                        percentage=round(float(team_data.get("recordOverall", {}).get("winPercentage", {}).get(
                            "value", 0)), 3),
                        points_for=float(team_data.get("pointsFor", {}).get("value", 0)),
                        points_against=float(team_data.get("pointsAgainst", {}).get("value", 0)),
                        streak_type=streak_type,
                        streak_len=int(abs(team_data.get("streak", {}).get("value", 0))),
                        team_id=base_team.team_id,
                        team_name=base_team.name,
                        rank=int(team_data.get("recordOverall", {}).get("rank", 0)),
                        division=base_team.division,
                        division_wins=int(team_data.get("recordDivision", {}).get("wins", 0)),
                        division_losses=int(team_data.get("recordDivision", {}).get("losses", 0)),
                        division_ties=int(team_data.get("recordDivision", {}).get("ties", 0)),
                        division_percentage=round(float(team_data.get("recordDivision", {}).get(
                            "winPercentage", {}).get("value", 0)), 3),
                        division_rank=int(team_data.get("recordDivision", {}).get("rank", 0))
                    )
                    base_team.streak_str = base_team.current_record.get_streak_str()
                    if base_matchup.division_matchup:
                        base_team.division_streak_str = base_team.current_record.get_division_streak_str()

                    # get median for week
                    week_median = median_score_by_week.get(str(week))

                    median_record: BaseRecord = league_median_records_by_team.get(str(base_team.team_id))

                    if not median_record:
                        median_record = BaseRecord(
                            team_id=base_team.team_id,
                            team_name=base_team.name
                        )
                        league_median_records_by_team[str(base_team.team_id)] = median_record

                    if week_median:
                        # use this if you want the tie-break to be season total points over/under median score
                        median_record.add_points_for(base_team.points - week_median)
                        # use this if you want the tie-break to be current week points over/under median score
                        # median_record.add_points_for(
                        #     (median_record.get_points_for() * -1) + (base_team.points - week_median))
                        median_record.add_points_against((median_record.get_points_against() * -1) + week_median)
                        if base_team.points > week_median:
                            median_record.add_win()
                        elif base_team.points < week_median:
                            median_record.add_loss()
                        else:
                            median_record.add_tie()

                        base_team.current_median_record = median_record

                    # add team to matchup teams
                    base_matchup.teams.append(base_team)

                    # add team to league teams by week
                    self.league.teams_by_week[str(week)][str(base_team.team_id)] = base_team

                    # no winner/loser if matchup is tied
                    if matchup.get(key + "Result") == "WIN":
                        base_matchup.winner = base_team
                    elif matchup.get(key + "Result") == "LOSE":
                        base_matchup.loser = base_team

                # add matchup to league matchups by week
                self.league.matchups_by_week[str(week)].append(base_matchup)

        for week, rosters in rosters_by_week.items():
            self.league.players_by_week[str(week)] = {}
            for team_id, roster in rosters.items():
                league_team: BaseTeam = self.league.teams_by_week.get(str(week)).get(str(team_id))

                for player in [slot for group in roster.get("groups") for slot in group.get("slots")]:
                    flea_player_position = player.get("position")
                    flea_league_player = player.get("leaguePlayer")

                    # noinspection SpellCheckingInspection
                    if flea_league_player:
                        flea_pro_player = flea_league_player.get("proPlayer")

                        base_player = BasePlayer()

                        base_player.week_for_report = int(week)
                        base_player.player_id = flea_pro_player.get("id")
                        base_player.bye_week = int(flea_pro_player.get("nflByeWeek", 0))
                        base_player.display_position = self.get_mapped_position(flea_pro_player.get("position"))
                        base_player.nfl_team_id = None
                        base_player.nfl_team_abbr = flea_pro_player.get("proTeam", {}).get("abbreviation").upper()
                        base_player.nfl_team_name = (
                            f"{flea_pro_player.get('proTeam', {}).get('location')} "
                            f"{flea_pro_player.get('proTeam', {}).get('name')}"
                        )

                        if flea_player_position.get("label") == "D/ST":
                            base_player.first_name = flea_pro_player.get("nameFull")
                            # use ESPN D/ST team logo (higher resolution) because Fleaflicker does not provide them
                            base_player.headshot_url = (
                                f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{base_player.nfl_team_abbr}.png"
                            )
                        else:
                            base_player.first_name = flea_pro_player.get("nameFirst")
                            base_player.last_name = flea_pro_player.get("nameLast")
                            base_player.headshot_url = flea_pro_player.get("headshotUrl")

                        base_player.full_name = flea_pro_player.get("nameFull")
                        base_player.owner_team_id = flea_league_player.get("owner", {}).get("id")
                        base_player.owner_team_name = flea_league_player.get("owner", {}).get("name")
                        base_player.percent_owned = 0
                        base_player.points = float(flea_league_player.get("viewingActualPoints", {}).get("value", 0))
                        # TODO: get season total points via summation, since this gives the end of season total, not
                        #  the total as of the selected week
                        # base_player.season_points = float(flea_league_player.get("seasonTotal", {}).get("value", 0))
                        # base_player.season_average_points = round(float(
                        #     flea_league_player.get("seasonAverage", {}).get("value", 0)), 2)
                        base_player.projected_points = None

                        base_player.position_type = (
                            "O"
                            if self.get_mapped_position(flea_pro_player.get("position"))
                               in self.league.offensive_positions
                            else "D"
                        )
                        base_player.primary_position = self.get_mapped_position(flea_pro_player.get("position"))

                        eligible_positions = [
                            position for position in
                            flea_league_player.get("proPlayer", {}).get("positionEligibility", [])
                        ]
                        for position in eligible_positions:
                            base_position = self.get_mapped_position(position)
                            base_player.eligible_positions.add(base_position)
                            for flex_position, positions in self.league.get_flex_positions_dict().items():
                                if base_position in positions:
                                    base_player.eligible_positions.add(flex_position)

                        base_player.selected_position = self.get_mapped_position(flea_player_position.get("label"))
                        base_player.selected_position_is_flex = (
                            self.position_mapping.get(flea_pro_player.get("position")).get("is_flex")
                        )

                        # typeAbbreviaition is misspelled in API data
                        # noinspection SpellCheckingInspection
                        base_player.status = flea_pro_player.get("injury", {}).get("typeAbbreviaition")

                        for stat in flea_league_player.get("viewingActualStats"):
                            base_stat = BaseStat()

                            base_stat.stat_id = stat.get("category", {}).get("id")
                            base_stat.name = stat.get("category", {}).get("abbreviation")
                            base_stat.value = stat.get("value", {}).get("value", 0)

                            base_player.stats.append(base_stat)

                        # add player to team roster
                        league_team.roster.append(base_player)

                        # add player to league players by week
                        self.league.players_by_week[str(week)][base_player.player_id] = base_player

        self.league.current_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: x.current_record.rank
        )

        self.league.current_median_standings = sorted(
            self.league.teams_by_week.get(str(self.league.week_for_report)).values(),
            key=lambda x: (
                x.current_median_record.get_wins(),
                -x.current_median_record.get_losses(),
                x.current_median_record.get_ties(),
                x.current_median_record.get_points_for()
            ),
            reverse=True
        )

        return self.league
