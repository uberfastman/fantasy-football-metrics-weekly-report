# Written by: Wren J. Rudolph
import os
from ConfigParser import ConfigParser
from shutil import copyfile

# local config vars
config = ConfigParser()
config.read('config.ini')
time_series_data_dir_path = config.get("Data_Clearing_Settings", "data_dir_path")
time_series_data_backup_dir_path = config.get("Data_Clearing_Settings", "data_backup_dir_path")

# Edit this variable to backup the current week's time series data
current_week = 1
week_str = "week_" + str(current_week)

weekly_backup_dir = time_series_data_backup_dir_path + "/" + week_str
if not os.path.isdir(weekly_backup_dir):
    os.makedirs(weekly_backup_dir)

files_to_backup = []
for filename in os.listdir(time_series_data_dir_path):
    if "_json.txt" in filename:
        files_to_backup.append(filename)

for filename in files_to_backup:

    file_to_copy = time_series_data_dir_path + "/" + filename
    copy_of_file = weekly_backup_dir + "/" + filename
    copyfile(file_to_copy, copy_of_file)
    print "Copied {} to {}\n".format(filename, weekly_backup_dir)
