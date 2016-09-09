# Written by: Wren J. Rudolph


def delete_file_content(filename):
    with open(filename, "w"):
        pass

if __name__ == '__main__':

    files_to_clear = [
        "time_series_points_data_5521_json.txt",
        "time_series_efficiency_data_5521_json.txt",
        "time_series_luck_data_5521_json.txt",
        "time_series_points_data_806145_json.txt",
        "time_series_efficiency_data_806145_json.txt",
        "time_series_luck_data_806145_json.txt"
    ]

    for data_file in files_to_clear:
        delete_file_content(data_file)

    print "Cleared content from files: {}".format(files_to_clear)
