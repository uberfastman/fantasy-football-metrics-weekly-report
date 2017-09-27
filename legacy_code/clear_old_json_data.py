# Written by: Wren J. Rudolph
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
import distutils.util as distutils
from ConfigParser import ConfigParser

import simplejson

# local config vars
config = ConfigParser()
config.read('config.ini')
clear_all_time_series_data_bool = bool(distutils.strtobool(config.get("Data_Settings", "clear_all_time_series_data")))
clear_last_week_time_series_data_bool = bool(distutils.strtobool(config.get("Data_Settings", "clear_last_week_time_series_data")))

# Adjust current week for proper performance
current_week = 8


def delete_all_file_content(filename):
    with open(filename, "w"):
        pass


def delete_last_week_content(filename):

    with open(filename, "a+") as json_data:

        json_data.seek(0)
        data = json_data.read(1)
        json_data.seek(0)

        if data:
            content_list = simplejson.load(json_data)
        else:
            print("No data in {}\n".format(filename))
            return

        if len(content_list[0]) < 2:
            # delete_all_file_content(filename)
            return

        for player_time_series_info in content_list:
            # del player_time_series_info[-1]

            if int(player_time_series_info[-1][0]) == current_week:
                del player_time_series_info[-1]

    with open(filename, "w+") as json_data:

        simplejson.dump(content_list, json_data)


if __name__ == '__main__':

    files_to_clear = []

    if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "league_of_emperors_id"):

        files_to_clear = [
            "time_series_points_data_5521_json.txt",
            "time_series_efficiency_data_5521_json.txt",
            "time_series_luck_data_5521_json.txt"
        ]

    elif config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get("Fantasy_Football_Report_Settings", "making_football_orange_id"):

        files_to_clear = [
            "time_series_points_data_806145_json.txt",
            "time_series_efficiency_data_806145_json.txt",
            "time_series_luck_data_806145_json.txt"
        ]

    for data_file in files_to_clear:

        if clear_all_time_series_data_bool and not clear_last_week_time_series_data_bool:
            delete_all_file_content(data_file)

        elif not clear_all_time_series_data_bool and clear_last_week_time_series_data_bool:
            delete_last_week_content(data_file)

        else:
            print("Please check config.ini for proper data clearing settings!")

    print("Cleared content from files: {}".format(files_to_clear))
