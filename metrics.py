from operator import itemgetter
<<<<<<< HEAD
from collections import defaultdict
=======
import collections
>>>>>>> develop


class CoachingEfficiency(object):
    # prohibited statuses to check team coaching efficiency eligibility
    prohibited_status_list = ["PUP-P", "SUSP", "O", "IR"]

    def __init__(self, roster_settings):
        self.flex_positions = roster_settings["flex_positions"]
        self.roster_slots = roster_settings["slots"]

        self.flex_positions = {
            'FLEX': roster_settings['flex_positions'],
            'DB': ["S", "CB"],
            'DL': ["DT", "DE"],
            'D': ["DB", "DL", "LB", "DT", "DE", "S", "CB"]
        }

    def check_eligible_positions(self, player):
        eligible = []

        for position in self.roster_slots:
            if position in player['eligible_positions']:
                # special case
                if position != 'D':
                    eligible.append(position)

                for flex_position, base_positions in self.flex_positions.items():
                    if position in base_positions:
                        eligible.append(flex_position)

        return eligible
            
    def check_eligible_players_by_position(self, position_str, player, position_list):
        if position_str in player['eligible_positions']:
            position_list.append([player['name'], player['fantasy_points']])
            return True
        return False

    def check_eligible_players_by_position_with_flex(self, position_str, player, position_list,
                                                     flex_player_candidates):
        if self.check_eligible_players_by_position(position_str, player, position_list):
            if position_str in self.flex_positions['FLEX']:
                flex_player_candidates.append([player['name'], player['fantasy_points']])

    def get_optimal_players(self, player_list, position, optimal_players_list):
        if player_list:
            player_list = sorted(player_list, key=itemgetter(1))[::-1]

            player_index = 0
            optimal_players_at_position = []
            temp_position_slots = self.roster_slots[position]
            while temp_position_slots > 0:
                try:
                    optimal_players_at_position.append(player_list[player_index])
                except IndexError:
                    pass
                player_index += 1
                temp_position_slots -= 1

            optimal_players_list.append(optimal_players_at_position)
            return optimal_players_at_position

    def is_player_eligible(self, player, week):
        return player["status"] in self.prohibited_status_list or player["bye_week"] == week

    def execute(self, team_name, team_info, week, league_roster_active_slots, disqualification_eligible=False):

        quarterbacks = []
        wide_receivers = []
        running_backs = []
        tight_ends = []
        kickers = []
        team_defenses = []
        individual_defenders = []
        flex_candidates = []
        flex_d_candidates = []

        positions = defaultdict(list)

        defensive_positions = {
            'DB': [],
            'LB': [],
            'CB': [],
            'S': [],
            'DE': [],
            'DT': []
        }
        flex_defensive_positions = []
        
        
        active_slots = sum(v for (k, v) in self.roster_slots.items())

        players = team['players']

        active_players = [p for p in players if p['selected_position'] != 'BN']
        bench_players = [p for p in players if p['selected_position'] == 'BN']

        players = team_info["players"]
        positions_filled_active = team_info["positions_filled_active"]

        bench_players = [p for p in players if p["selected_position"] == "BN"]
        ineligible_efficiency_player_count = len([p for p in bench_players if self.is_player_eligible(p, week)])

        for player in players:
            #print('{0} - {1}'.format(player.get('eligible_positions'),player.get('name')))

            eligible = self.check_eligible_positions(player)
            for position in eligible:
                positions[position].append(player)

            self.check_eligible_players_by_position("QB", player, quarterbacks)
            self.check_eligible_players_by_position_with_flex("WR", player, wide_receivers, flex_candidates)
            self.check_eligible_players_by_position_with_flex("RB", player, running_backs, flex_candidates)
            self.check_eligible_players_by_position_with_flex("TE", player, tight_ends, flex_candidates)
            self.check_eligible_players_by_position("K", player, kickers)
            self.check_eligible_players_by_position("DEF", player, team_defenses)

            for position, eligible in defensive_positions.items():
                self.check_eligible_players_by_position_with_flex(position, player, eligible, flex_defensive_positions)

            eligible_positions = player['eligible_positions']
            if "D" in eligible_positions and "DEF" not in eligible_positions:
                individual_defenders.append([player["name"], player["fantasy_points"]])

        import json
        for position, players in positions.items():
            print('{0}: {1}'.format(position, [p['name'] for p in players]))
        #print(json.dumps(positions, indent=2))
        # print(json.dumps(defensive_positions, indent=2))
        # print(json.dumps(flex_defensive_positions))

        optimal_players = []

        self.get_optimal_players(quarterbacks, "QB", optimal_players)
        optimal_wrs = self.get_optimal_players(wide_receivers, "WR", optimal_players)
        optimal_rbs = self.get_optimal_players(running_backs, "RB", optimal_players)
        optimal_tes = self.get_optimal_players(tight_ends, "TE", optimal_players)
        self.get_optimal_players(kickers, "K", optimal_players)
        self.get_optimal_players(team_defenses, "DEF", optimal_players)
        self.get_optimal_players(individual_defenders, "D", optimal_players)

        optimal_flexes = []
        if flex_candidates:
            flex_set = set(map(tuple, flex_candidates))
            wr_set = set(map(tuple, optimal_wrs))
            rb_set = set(map(tuple, optimal_rbs))
            te_set = set(map(tuple, optimal_tes))
            flex_set = flex_set - wr_set
            flex_set = flex_set - rb_set
            flex_set = flex_set - te_set

            flex_list = sorted(list(flex_set), key=itemgetter(1))[::-1]
            index = 0
            temp_slots = self.roster_slots["FLEX"]
            while temp_slots > 0:
                try:
                    optimal_flexes.append(flex_list[index])
                except IndexError:
                    pass
                index += 1
                temp_slots -= 1

            optimal_players.append(optimal_flexes)

        optimal_lineup = [item for sublist in optimal_players for item in sublist]

        # calculate optimal score
        optimal_score = 0.0
        for player in optimal_lineup:
            optimal_score += player[1]

        # calculate coaching efficiency
        actual_weekly_score = team_info["weekly_score"]
        coaching_efficiency = (actual_weekly_score / optimal_score) * 100

        # apply coaching efficiency eligibility requirements for League of Emperors
        if disqualification_eligible:
            if collections.Counter(league_roster_active_slots) == collections.Counter(positions_filled_active):
                if ineligible_efficiency_player_count <= 4:
                    efficiency_disqualification = False
                else:
                    print("ROSTER INVALID! There are %d inactive players on the bench of %s in week %s!" % (
                        ineligible_efficiency_player_count, team_name, week))
                    efficiency_disqualification = True

            else:
                print(
                    "ROSTER INVALID! There is not a full squad of active players starting on %s in week %s!" % (
                        team_name,
                        week))
                efficiency_disqualification = True

            if efficiency_disqualification:
                coaching_efficiency = 0.0

        return coaching_efficiency
