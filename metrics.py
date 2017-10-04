from operator import itemgetter

class CoachingEfficiency():
    # prohibited statuses to check team coaching efficiency eligibility
    prohibited_status_list = ["PUP-P", "SUSP", "O", "IR"]

    @staticmethod
    def check_eligible_players_by_position(position_str, player, position_list):
        if position_str in player['eligible_positions']:
            position_list.append([player['name'], player['fantasy_points']])
            return True
        return False

    @staticmethod
    def check_eligible_players_by_position_with_flex(position_str, player, flex_option_positions, position_list,
                                                     flex_player_candidates):
        if CoachingEfficiency.check_eligible_players_by_position(position_str, player, position_list):
            if position_str in flex_option_positions:
                flex_player_candidates.append([player['name'], player['fantasy_points']])

    @staticmethod
    def get_optimal_players(player_list, position_slots, optimal_players_list):
        if player_list:
            player_list = sorted(player_list, key=itemgetter(1))[::-1]

            player_index = 0
            optimal_players_at_position = []
            temp_position_slots = position_slots
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
        return player['status'] in self.prohibited_status_list \
            or player['bye_week'] == week

    def execute(self, team, week, disqualification_eligible=False):
        positions_filled_active = []
        positions_filled_bench = []
        ineligible_efficiency_player_count = 0

        quarterbacks = []
        wide_receivers = []
        running_backs = []
        tight_ends = []
        kickers = []
        team_defenses = []
        individual_defenders = []
        flex_candidates = []
        flex_positions = team['roster']['flex_positions']

        active_slots = sum(v for (k, v) in team['roster']['slots'].items())

        players = team['players']

        active_players = [p for p in players if p['selected_position'] != 'BN']
        bench_players = [p for p in players if p['selected_position'] == 'BN']

        actual_weekly_score = team['weekly_score']
        actual_bench_score = sum([p['fantasy_points'] for p in bench_players])

        positions_filled_active = len(active_players)
        positions_filled_bench = len(bench_players)

        ineligible_efficiency_player_count = len([p for p in bench_players if self.is_player_eligible(p, week)])

        for player in players:
            self.check_eligible_players_by_position("QB", player, quarterbacks)
            self.check_eligible_players_by_position_with_flex("WR", player, flex_positions, wide_receivers, flex_candidates)
            self.check_eligible_players_by_position_with_flex("RB", player, flex_positions, running_backs, flex_candidates)
            self.check_eligible_players_by_position_with_flex("TE", player, flex_positions, tight_ends, flex_candidates)
            self.check_eligible_players_by_position("K", player, kickers)
            self.check_eligible_players_by_position("DEF", player, team_defenses)

            eligible_positions = player['eligible_positions']
            if "D" in eligible_positions and "DEF" not in eligible_positions:
                individual_defenders.append([player['name'], player['fantasy_points']])

        optimal_players = []

        slots = team['roster']['slots']

        self.get_optimal_players(quarterbacks, slots['QB'], optimal_players)
        optimal_wrs = self.get_optimal_players(wide_receivers, slots['WR'], optimal_players)
        optimal_rbs = self.get_optimal_players(running_backs, slots['RB'], optimal_players)
        optimal_tes = self.get_optimal_players(tight_ends, slots['TE'], optimal_players)
        self.get_optimal_players(kickers, slots['K'], optimal_players)
        self.get_optimal_players(team_defenses, slots['DEF'], optimal_players)
        self.get_optimal_players(individual_defenders, slots['D'], optimal_players)

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
            temp_slots = slots["FLEX"]
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
        coaching_efficiency = (actual_weekly_score / optimal_score) * 100

        # apply coaching efficiency eligibility requirements for League of Emperors
        if disqualification_eligible:
            if collections.Counter(active_slots) == collections.Counter(positions_filled_active):
                if ineligible_efficiency_player_count <= 4:
                    efficiency_disqualification = False
                else:
                    print("ROSTER INVALID! There are %d inactive players on the bench of %s in week %s!" % (
                        ineligible_efficiency_player_count, team_name, chosen_week))
                    efficiency_disqualification = True

            else:
                print(
                    "ROSTER INVALID! There is not a full squad of active players starting on %s in week %s!" % (
                        team_name,
                        chosen_week))
                efficiency_disqualification = True

            if efficiency_disqualification:
                coaching_efficiency = 0.0

        return coaching_efficiency