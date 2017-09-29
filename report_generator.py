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

    def use_default_league_function():
        use_default_league = raw_input("Generate report for default league? (y/n) -> ")
        if use_default_league == "y":
            fantasy_football_report_instance = FantasyFootballReport(user_input_chosen_week=use_chosen_week_function())
            return fantasy_football_report_instance
        elif use_default_league == "n":
            chosen_league_id = raw_input("What is the league ID of the Yahoo league for which you want to generate a report? -> ")
            try:
                fantasy_football_report_instance = FantasyFootballReport(chosen_league_id, use_chosen_week_function())
                return fantasy_football_report_instance
            except IndexError:
                print("The league ID you have selected is not valid.")
                use_default_league_function()

        else:
            print("You must select either 'y' or 'n'.")
            use_default_league_function()

    def use_chosen_week_function():
        use_default_chosen_week = raw_input("Generate report for default week? (y/n) -> ")
        if use_default_chosen_week == "y":
            return None
        elif use_default_chosen_week == "n":
            chosen_week = raw_input("For which week would you like to generate a report? (1 - 17) -> ")
            if 0 < int(chosen_week) < 18:
                return chosen_week
            else:
                print("Please select a valid week number between 1 and 17.")
                use_chosen_week_function()
        else:
            print("You must select either 'y' or 'n'.")
            use_chosen_week_function()

    fantasy_football_report = use_default_league_function()
    generated_report = fantasy_football_report.create_pdf_report()

    upload_file_to_google_drive_bool = bool(distutils.strtobool(config.get("Google_Drive_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        # upload pdf to google drive
        google_drive_uploader = GoogleDriveUploader(generated_report)
        upload_message = google_drive_uploader.upload_file()
        print(upload_message)

    post_to_slack_bool = bool(distutils.strtobool(config.get("Slack_Settings", "post_to_slack")))

    if post_to_slack_bool:
        # post shareable link to uploaded google drive pdf on slack
        if config.get("Fantasy_Football_Report_Settings", "chosen_league_id") == config.get(
                "Fantasy_Football_Report_Settings", "humangeo_id"):
            slack_messenger = SlackMessenger()
            print(slack_messenger.post_to_hg_fantasy_football_channel(upload_message))
            # print slack_messenger.test_on_hg_slack(upload_message)
            print("DONE!")

        else:
            print("{}\n".format(upload_message))
            print("DONE!")
