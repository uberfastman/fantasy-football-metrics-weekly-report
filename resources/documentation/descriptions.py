__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

league_standings = "Overall standings for the chosen week. Dynamically adjusts information based on whether a league " \
                   "uses only waivers or has a FAAB (free agent acquisition budget). Data marked with an " \
                   "asterisk (\"<b>*</b>\") means that due to limitations of whichever fantasy platform API is being " \
                   "used, the available information is incomplete in some way."

league_median_matchup_standings = "Overall \"against the median\" league standings. Every week the median score is " \
                                  "calculated across all teams, and every team plays an extra matchup versus the " \
                                  "league median score. Teams earn an additional win/loss/tie based on how " \
                                  "their score matches up against the league median. Median standings are ranked by " \
                                  "\"Combined Record\" (most wins, then fewest losses, then most ties), and use " \
                                  " \"Season +/- Median\" (how many total points over/under the median teams have " \
                                  "scored on the season) as the tie-breaker."

playoff_probabilities = "Predicts each team's likelihood of making the playoffs, as well as of finishing in any " \
                        "given place. These predictions are created using Monte Carlo simulations to simulate the " \
                        "rest of the season over and over, and then averaging out each team's performance across all " \
                        "performed simulations. Currently these predictions are not aware of special playoff " \
                        "eligibility for leagues with divisions or other custom playoff settings."

team_power_rankings = "The power rankings are calculated by taking a weekly average of each team's score, coaching " \
                      "efficiency, and luck."

team_z_score_rankings = "Measure of standard deviations away from mean for a score. Shows teams performing above or " \
                        "below their normal scores for the current week. See <a href=\"https://en.wikipedia.org/wiki/" \
                        "Standard_score\" color=blue>Standard Score</a>. This metric shows which teams " \
                        "over-performed or underperformed compared to how those teams usually do."

team_score_rankings = "Teams ranked by highest score. If tie-breaks are turned on, highest bench points will be used " \
                      "to break score ties."

team_coaching_efficiency_rankings = "Coaching efficiency is calculated by dividing the total points scored by each " \
                                    "team this week by the highest possible points they could have scored (optimal " \
                                    "points) this week. This metric is designed to quantify whether manager made " \
                                    "good sit/start decisions, regardless of how high their team scored or whether " \
                                    "their team won or lost.<br/>&nbsp;&nbsp;&nbsp;&nbsp;If tie-breaks are turned " \
                                    "on, the team with the most starting players that exceeded their weekly average " \
                                    "points is awarded a higher ranking, and if that is still tied, the team whose " \
                                    "starting players exceeded their weekly average points by the highest cumulative " \
                                    "percentage points is awarded a higher ranking."

team_luck_rankings = "Luck is calculated by matching up each team against every other team that week to get a total " \
                     "record against the whole league, then if that team won, the formula is:<br/>" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" \
                     "<div style=\"text-align:center;\"><i>luck = (losses + ties) / (number of teams excluding that " \
                     "team) * 100</i></div><br/>" \
                     "and if that team lost, the formula is:<br/>" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" \
                     "<div style=\"text-align:center;\"><i>luck = 0 - (wins + ties) / (number of teams excluding " \
                     "that team) * 100</i></div><br/>" \
                     "&nbsp;&nbsp;&nbsp;&nbsp;This metric is designed to show whether your team was very \"lucky\" " \
                     "or \"unlucky\", since a team that would have beaten all but one team this week (second highest " \
                     "score) but lost played the only other team they could have lost to, and a team that would have " \
                     "lost to all but one team this week (second lowest score) but won played the only other team " \
                     "that they could have beaten."

team_optimal_score_rankings = "Teams ranked by highest optimal score."

bad_boy_rankings = "The Bad Boy ranking is a \"just-for-fun\" metric that pulls NFL player arrest history from the " \
                   "<a href=\"https://www.usatoday.com/sports/nfl/arrests/\" color=blue><u>USA Today NFL player " \
                   "arrest database</u></a>, and then assigns points to all crimes committed by players on each " \
                   "team's starting lineup to give the team a total bad boy score. The points assigned to each " \
                   "crime can be found <a href=\"https://raw.githubusercontent.com/uberfastman/fantasy-football-" \
                   "metrics-weekly-report/main/resources/files/crime_categories.json\" color=blue><u>here</u></a>."

beef_rankings = "The Beef ranking is a \"just-for-fun\" metric with a made-up unit of measurement, the " \
                "\"<b>TABBU</b>\", which stands for \"<b>T</b>rimmed <b>A</b>nd <b>B</b>oneless <b>B</b>eef " \
                "<b>U</b>nit(s)\". The TABBU was derived from the amount of trimmed and boneless beef is produced by " \
                "one beef cow, based on academic research done for the beef industry found " \
                "<a href=\"https://extension.tennessee.edu/publications/Documents/PB1822.pdf\" color=blue>here</a>, " \
                "and is set as equivalent to 500 lbs. The app pulls player weight data from the Sleeper API, an " \
                "example of which can be found <a href=\"https://api.sleeper.app/v1/players/nfl\" color=blue>" \
                "<u>here</u></a>, and uses the total weight of each team's starting lineup, including the rolled-up " \
                "weights of starting defenses, to give each team a total TABBU score."

weekly_top_scorers = "Running list of each week's highest scoring team. Can be used for weekly highest points payouts."

weekly_highest_coaching_efficiency = "Running list of each week's team with the highest coaching efficiency. Can be " \
                                     "used for weekly highest coaching efficiency payouts."
