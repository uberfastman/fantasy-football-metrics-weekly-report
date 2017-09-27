# Written by: Wren J. Rudolph
import distutils.util as distutils
from ConfigParser import ConfigParser

from google_drive_uploader import GoogleDriveUploader
from fantasy_football_report_builder import FantasyFootballReport
from slack_messenger import SlackMessenger

# local config vars
config = ConfigParser()
config.read('config.ini')

# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == '__main__':

    fantasy_football_report = FantasyFootballReport()
    fantasy_football_report.create_pdf_report()

    upload_file_to_google_drive_bool = bool(distutils.strtobool(config.get("Data_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        # upload pdf to google drive
        google_drive_uploader = GoogleDriveUploader(fantasy_football_report.create_pdf_report())
        upload_message = google_drive_uploader.upload_file()

    post_to_slack_bool = bool(distutils.strtobool(config.get("Data_Settings", "post_to_slack")))

    if post_to_slack_bool:
        # post shareable link to uploaded google drive pdf on slack
        if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get(
                "Fantasy_Football_Report_Settings", "making_football_orange_id"):
            slack_messenger = SlackMessenger()
            print(slack_messenger.post_to_hg_fantasy_football_channel(upload_message))
            # print slack_messenger.test_on_hg_slack(upload_message)
            print("DONE!")

        else:
            print("{}\n".format(upload_message))
            print("DONE!")
