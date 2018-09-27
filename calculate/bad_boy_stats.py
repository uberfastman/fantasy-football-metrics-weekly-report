import csv
import pickle

import requests
from bs4 import BeautifulSoup


class BadBoyStats(object):

    def __init__(self, dev_bool, save_bool, league_test_dir):
        """ Initialize class, load data from USA Today NFL Arrest DB. Combine defensive player data
        """

        self.rankings = {}
        # Load the scoring based on crime categories
        with open("resources/crime_category_scoring.csv", mode="r", encoding="utf-8-sig") as infile:
            reader = csv.reader(infile)
            for rows in reader:
                crime_category = rows[0].upper().strip()
                if crime_category.startswith('"') and crime_category.endswith('"'):
                    crime_category = crime_category[1:-1]
                rank = int(rows[1])
                self.rankings[crime_category] = rank

        if not dev_bool:
            url = "https://www.usatoday.com/sports/nfl/arrests/"
            r = requests.get(url)
            data = r.text
            soup = BeautifulSoup(data, "html.parser")
            self.bad_boy_data = {}

            # Scrape USA Today NFL crime database site
            for row in soup.findAll("tr"):
                cells = row.findAll("td")
                if len(cells) > 0:
                    name = cells[2].text
                    team = cells[1].text
                    date = cells[0].text
                    pos = cells[3].text
                    case = cells[4].text.upper()
                    temp_category = cells[5].text.upper()

                    for item in temp_category.strip().split(","):
                        category = item.strip()
                        if category in self.rankings:
                            score = self.rankings.get(category)
                        else:
                            score = 0
                            print("Crime ranking not found: %s\nAssigning score of 0." % category)

                        if name not in self.bad_boy_data:
                            self.bad_boy_data[name] = {
                                "team": team,
                                "date": date,
                                "pos": pos,
                                "case": case,
                                "category": category,
                                "points": score
                            }
                        else:
                            points = self.bad_boy_data[name].get("points") + score
                            self.bad_boy_data[name]["points"] = points

                        if pos in ["CB", "LB", "DE", "DT", "S"]:
                            if team not in self.bad_boy_data:
                                self.bad_boy_data[team] = {
                                    "team": team,
                                    "date": date,
                                    "pos": pos,
                                    "case": case,
                                    "category": category,
                                    "points": score
                                }
                            else:
                                points = self.bad_boy_data[name].get("points") + score
                                self.bad_boy_data[name]["points"] = points
            if save_bool:
                with open(league_test_dir +
                          "/" +
                          "bad_boy_data.pkl", "wb") as bb_out:
                    pickle.dump(self.bad_boy_data, bb_out, pickle.HIGHEST_PROTOCOL)
        else:
            with open(league_test_dir +
                      "/" +
                      "bad_boy_data.pkl", "rb") as bb_in:
                self.bad_boy_data = pickle.load(bb_in)

        if len(self.bad_boy_data) == 0:
            print("NO bad boy records were loaded, please check your internet connection or the availability of "
                  "'https://www.usatoday.com/sports/nfl/arrests/' and try generating a new report.")
        else:
            print("{} bad boy records loaded".format(len(self.bad_boy_data)))

    def check_bad_boy_status(self, name, team, pos):
        """ Looks up given player and returns number of 'bad boy' points based on scoring.

        TODO: maybe limit for years and adjust defensive players rolling up to DEF team as it skews DEF scores high
        :param name: Player name to look up
        :param team: Player's team (maybe later limit to only crimes while on that team...or for DEF players)
        :param pos: Player's position
        :return: Integer number of bad boy points, crime recorded
        """
        total = 0
        category = ""
        if pos == "DEF":
            name = team
        if name in self.bad_boy_data:
            crime = self.bad_boy_data.get(name)
            total = crime.get("points")
            category = crime.get("category")
        return total, category
