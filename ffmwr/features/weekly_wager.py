from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ffmwr.models.base.model import BaseLeague, BasePlayer, BaseTeam
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import WeeklyWagerSettings
from ffmwr.utilities.utils import FFMWRPythonObjectJson

logger = get_logger(__name__, propagate=False)


@dataclass
class WagerResult(FFMWRPythonObjectJson):
    """Represents the result of a weekly wager."""
    
    winning_players: List[Dict]
    winning_teams: List[str] 
    target_value: float
    total_participants: int
    is_tie: bool
    wager_description: str


class WeeklyWager:
    """Calculate weekly wager results based on configurable criteria."""
    
    VALID_POSITIONS = {'QB', 'RB', 'WR', 'TE', 'K', 'D/ST', 'DEF'}
    VALID_FILTERS = {'starter', 'bench', 'all'}
    VALID_TARGETS = {
        'points', 'touchdowns', 'yards', 'receptions',
        'interceptions', 'fumbles', 'fumbles_lost', 'completions', 
        'attempts', 'rushing_attempts', 'receiving_yards', 'rushing_yards'
    }
    VALID_DIRECTIONS = {'most', 'least'}
    
    def __init__(self, settings: WeeklyWagerSettings):
        self.settings = settings
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate wager settings configuration."""
        # Validate position(s)
        if self.settings.position:
            if isinstance(self.settings.position, str):
                positions = [self.settings.position]
            elif isinstance(self.settings.position, list):
                positions = self.settings.position
            else:
                raise ValueError(f"Invalid position type: {type(self.settings.position)}. Must be string, list, or None")
            
            for pos in positions:
                if pos.upper() not in self.VALID_POSITIONS:
                    raise ValueError(f"Invalid position: {pos}. Must be one of: {self.VALID_POSITIONS}")
        
        if self.settings.filter not in self.VALID_FILTERS:
            raise ValueError(f"Invalid filter: {self.settings.filter}. Must be one of: {self.VALID_FILTERS}")
        
        if self.settings.target not in self.VALID_TARGETS:
            raise ValueError(f"Invalid target: {self.settings.target}. Must be one of: {self.VALID_TARGETS}")
        
        if self.settings.direction not in self.VALID_DIRECTIONS:
            raise ValueError(f"Invalid direction: {self.settings.direction}. Must be one of: {self.VALID_DIRECTIONS}")
    
    def calculate_wager_result(self, league: BaseLeague, week_for_report: int) -> Optional[WagerResult]:
        """Calculate the wager result for the specified week."""
        if not self.settings.enabled:
            return None
            
        logger.info(f"Calculating weekly wager for week {week_for_report}")
        
        # Get all eligible players
        eligible_players = self._get_eligible_players(league, week_for_report)
        
        if not eligible_players:
            logger.warning("No eligible players found for weekly wager")
            return None
        
        # Calculate target values for all players
        player_values = []
        for player_data in eligible_players:
            player = player_data['player']
            target_value = self._get_target_value(player)
            if target_value >= 0:  # Include players with 0 or positive values
                player_values.append({
                    'player': player,
                    'team': player_data['team'],
                    'value': target_value
                })
        
        if not player_values:
            logger.warning("No eligible players found for weekly wager")
            return None
        
        # Sort all players by target value (direction determines order)
        reverse_sort = self.settings.direction == 'most'
        player_values.sort(key=lambda x: x['value'], reverse=reverse_sort)
        
        # Find the winning value and all players who achieved it (for tie detection)
        winning_value = player_values[0]['value'] if player_values else 0
        winners = [p for p in player_values if p['value'] == winning_value]
        
        # Get best player per team for team-vs-team comparison (direction-aware)
        team_best_players = {}
        for player_data in player_values:
            team_name = player_data['team'].name
            if team_name not in team_best_players:
                team_best_players[team_name] = player_data
            else:
                current_best = team_best_players[team_name]['value']
                player_value = player_data['value']
                # For "most": higher is better, for "least": lower is better
                if ((self.settings.direction == 'most' and player_value > current_best) or
                    (self.settings.direction == 'least' and player_value < current_best)):
                    team_best_players[team_name] = player_data
        
        # Convert to list and sort by value (direction-aware)
        team_rankings = list(team_best_players.values())
        team_rankings.sort(key=lambda x: x['value'], reverse=reverse_sort)
        
        # Build team comparison list
        all_players = []
        winning_teams = []
        
        for i, player_data in enumerate(team_rankings):
            player = player_data['player']
            team = player_data['team']
            
            # Determine rank (handle ties)
            rank = i + 1
            if i > 0 and team_rankings[i]['value'] == team_rankings[i-1]['value']:
                # This player is tied with the previous player
                rank = next(j for j, p in enumerate(team_rankings, 1) if p['value'] == player_data['value'])
            
            all_players.append({
                'rank': rank,
                'name': player.full_name,
                'position': player.display_position or player.primary_position,
                'team_abbr': player.nfl_team_abbr,
                'owner_team': team.name,
                'value': player_data['value'],
                'is_winner': player_data['value'] == winning_value
            })
            
            # Track winning teams
            if player_data['value'] == winning_value and team.name not in winning_teams:
                winning_teams.append(team.name)
        
        description = self._generate_description()
        
        return WagerResult(
            winning_players=all_players,  # Now contains top player per team with ranking info
            winning_teams=winning_teams,
            target_value=winning_value,
            total_participants=len(team_rankings),
            is_tie=len(winners) > 1,
            wager_description=description
        )
    
    def _get_eligible_players(self, league: BaseLeague, week_for_report: int) -> List[Dict]:
        """Get all players eligible for the wager based on position and filter settings."""
        eligible_players = []
        
        teams = league.teams_by_week.get(str(week_for_report), {})
        
        for team in teams.values():
            if not hasattr(team, 'roster') or not team.roster:
                continue
                
            for player in team.roster:
                # Filter by position(s) if specified
                if self.settings.position:
                    if isinstance(self.settings.position, str):
                        positions = [self.settings.position.upper()]
                    else:
                        positions = [pos.upper() for pos in self.settings.position]
                    
                    position_match = False
                    for pos in positions:
                        if (player.display_position == pos or
                            player.primary_position == pos or
                            (pos == 'DEF' and player.primary_position == 'D/ST')):
                            position_match = True
                            break
                    
                    if not position_match:
                        continue
                
                # Filter by roster status
                if not self._matches_filter(player, team):
                    continue
                
                eligible_players.append({
                    'player': player,
                    'team': team
                })
        
        logger.info(f"Found {len(eligible_players)} eligible players")
        return eligible_players
    
    def _matches_filter(self, player: BasePlayer, team: BaseTeam) -> bool:
        """Check if player matches the filter criteria (starter/bench/all)."""
        if self.settings.filter == 'all':
            return True
        
        # Determine if player is a starter
        is_starter = False
        
        # Check if player has a selected position that's not bench
        if hasattr(player, 'selected_position') and player.selected_position:
            is_starter = player.selected_position.upper() not in ['BN', 'BENCH', 'BE']
        
        # Alternative check: if player is in starting lineup based on position
        elif hasattr(player, 'primary_position') and player.primary_position:
            # This is a simplified check - in a real implementation, you'd check against
            # the league's roster settings to determine starting positions
            starting_positions = {'QB', 'RB', 'WR', 'TE', 'FLEX', 'K', 'D/ST', 'DEF'}
            is_starter = player.primary_position in starting_positions
        
        if self.settings.filter == 'starter':
            return is_starter
        elif self.settings.filter == 'bench':
            return not is_starter
        
        return True
    
    def _get_target_value(self, player: BasePlayer) -> float:
        """Extract the target metric value from the player."""
        if self.settings.target == 'points':
            return player.points
        
        # For other targets, we need to look at player stats
        if not hasattr(player, 'stats') or not player.stats:
            return 0.0
        
        for stat in player.stats:
            if not hasattr(stat, 'stat_id'):
                continue
                
            if self.settings.target == 'touchdowns':
                # Look for touchdown stats (passing, rushing, receiving TDs)
                if stat.stat_id in ['passTD', 'rushTD', 'recTD', 'TD', '25', '44']:  # 25=rushTD, 44=recTD
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'yards':
                # Look for yardage stats (passing, rushing, receiving yards)
                if stat.stat_id in ['passYds', 'rushYds', 'recYds', 'yards', '24', '43']:  # 24=rushYds, 43=recYds
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'receptions':
                # Look for reception stats
                if stat.stat_id in ['rec', 'receptions', '42']:  # 42=receptions
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'interceptions':
                # Look for interceptions thrown (negative stat for QBs)
                if stat.stat_id in ['18']:  # 18=interceptions
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'fumbles':
                # Look for fumbles
                if stat.stat_id in ['67']:  # 67=fumbles
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'fumbles_lost':
                # Look for fumbles lost (negative stat)
                if stat.stat_id in ['68']:  # 68=fumbles lost
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'completions':
                # Look for passing completions (QB stat)
                if stat.stat_id in ['1']:  # 1=completions
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'attempts':
                # Look for passing attempts (QB stat)
                if stat.stat_id in ['0']:  # 0=passing attempts
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'rushing_attempts':
                # Look for rushing attempts
                if stat.stat_id in ['23']:  # 23=rushing attempts
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'receiving_yards':
                # Look for receiving yards specifically
                if stat.stat_id in ['43']:  # 43=receiving yards
                    return float(getattr(stat, 'value', 0))
            elif self.settings.target == 'rushing_yards':
                # Look for rushing yards specifically
                if stat.stat_id in ['24']:  # 24=rushing yards
                    return float(getattr(stat, 'value', 0))
        
        return 0.0
    
    def _generate_description(self) -> str:
        """Generate a human-readable description of the wager."""
        if self.settings.description:
            return self.settings.description
        
        # Generate automatic description
        position_text = ""
        if self.settings.position:
            if isinstance(self.settings.position, str):
                position_text = f" {self.settings.position}"
            elif isinstance(self.settings.position, list):
                if len(self.settings.position) == 1:
                    position_text = f" {self.settings.position[0]}"
                else:
                    position_text = f" {'/'.join(self.settings.position)}"
        
        filter_text = {
            'starter': 'starting',
            'bench': 'bench', 
            'all': ''
        }.get(self.settings.filter, '')
        
        target_text = {
            'points': 'fantasy points',
            'touchdowns': 'touchdowns',
            'yards': 'yards',
            'receptions': 'receptions',
            'interceptions': 'interceptions thrown',
            'fumbles': 'fumbles',
            'fumbles_lost': 'fumbles lost',
            'completions': 'pass completions',
            'attempts': 'pass attempts',
            'rushing_attempts': 'rushing attempts',
            'receiving_yards': 'receiving yards',
            'rushing_yards': 'rushing yards'
        }.get(self.settings.target, self.settings.target)
        
        parts = []
        if filter_text:
            parts.append(filter_text)
        if position_text:
            parts.append(position_text.strip())
        
        player_desc = " ".join(parts).strip() if parts else "player"
        
        return f"{player_desc} with the {self.settings.direction} {target_text}".strip()