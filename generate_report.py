# written by Wren J.R.

import distutils.util as distutils
import getopt
import sys
from configparser import ConfigParser

from fantasy_football_report_builder import FantasyFootballReport
from slack_messenger import SlackMessenger
from upload_to_google_drive import GoogleDriveUploader

# local config vars
config = ConfigParser()
config.read('config.ini')


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "htl:w:")
    except getopt.GetoptError:
        print("\nYahoo Fantasy Football report application usage:\n"
              "     python generate_report.py -t -l <yahoo_league_id> -w <chosen_week>\n")
        sys.exit(2)

    test_bool = False
    league_id = None
    week = None
    for opt, arg in opts:
        if opt == "-h":
            print("\nYahoo Fantasy Football report application usage:\n"
                  "     python generate_report.py -t -l <yahoo_league_id> -w <chosen_week>\n")
            sys.exit()
        elif opt in ("-t", "--test"):
            test_bool = True
        elif opt in ("-l", "--league-id"):
            league_id = arg
        elif opt in ("-w", "--week"):
            week = arg
            if int(week) < 1 or int(week) > 17:
                print("\nPlease select a valid week number between 1 and 17.")
                week = use_chosen_week_function()
    return test_bool, league_id, week


def use_default_league_function(chosen_league_id, chosen_week_arg, test_bool):
    if not chosen_league_id:
        use_default_league = input("Generate report for default league? (y/n) -> ")
    else:
        use_default_league = "selected"

    if use_default_league == "y":
        if not chosen_week_arg:
            chosen_week = use_chosen_week_function()
        else:
            chosen_week = chosen_week_arg
        fantasy_football_report_instance = FantasyFootballReport(user_input_chosen_week=chosen_week,
                                                                 test_bool=test_bool)
        return fantasy_football_report_instance, config.get("Fantasy_Football_Report_Settings", "chosen_league_id")
    elif use_default_league == "n":
        chosen_league_id = input(
            "What is the league ID of the Yahoo league for which you want to generate a report? -> ")
        try:
            fantasy_football_report_instance = FantasyFootballReport(user_input_league_id=chosen_league_id,
                                                                     user_input_chosen_week=use_chosen_week_function(),
                                                                     test_bool=test_bool)
            return fantasy_football_report_instance, str(chosen_league_id)
        except IndexError:
            print("The league ID you have selected is not valid.")
            use_default_league_function(chosen_week_arg, test_bool)
    elif use_default_league == "selected":
        if not chosen_week_arg:
            chosen_week = use_chosen_week_function()
        else:
            chosen_week = chosen_week_arg
        fantasy_football_report_instance = FantasyFootballReport(user_input_league_id=chosen_league_id,
                                                                 user_input_chosen_week=chosen_week,
                                                                 test_bool=test_bool)
        return fantasy_football_report_instance, str(chosen_league_id)
    else:
        print("You must select either 'y' or 'n'.")
        use_default_league_function(chosen_week_arg, test_bool)


def use_chosen_week_function():
    use_default_chosen_week = input("Generate report for default week? (y/n) -> ")
    if use_default_chosen_week == "y":
        return None
    elif use_default_chosen_week == "n":
        chosen_week = input("For which week would you like to generate a report? (1 - 17) -> ")
        if 0 < int(chosen_week) < 18:
            return chosen_week
        else:
            print("Please select a valid week number between 1 and 17.")
            use_chosen_week_function()
    else:
        print("You must select either 'y' or 'n'.")
        use_chosen_week_function()


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == '__main__':

    options = main(sys.argv[1:])
    test_bool_arg = options[0]
    league_id_arg = options[1]
    week_arg = options[2]

    report_info = use_default_league_function(league_id_arg, week_arg, test_bool_arg)
    fantasy_football_report = report_info[0]
    selected_league_id = report_info[1]
    generated_report = fantasy_football_report.create_pdf_report()

    upload_file_to_google_drive_bool = bool(
        distutils.strtobool(config.get("Google_Drive_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        if not test_bool_arg:
            # upload pdf to google drive
            google_drive_uploader = GoogleDriveUploader(generated_report)
            upload_message = google_drive_uploader.upload_file()
            print(upload_message)
        else:
            print("Test report NOT uploaded to Google Drive.")

    post_to_slack_bool = bool(distutils.strtobool(config.get("Slack_Settings", "post_to_slack")))

    if post_to_slack_bool:
        if not test_bool_arg:
            if selected_league_id == config.get("Fantasy_Football_Report_Settings", "humangeo_id"):
                slack_messenger = SlackMessenger()
                # post shareable link to uploaded google drive pdf on slack
                # print(slack_messenger.post_to_hg_fantasy_football_channel(upload_message))

                # upload pdf report directly to slack
                print(slack_messenger.upload_file_to_hg_fantasy_football_channel(generated_report, "fantasyfootball"))
                print("DONE!")

            else:
                print("{}\n".format(upload_message))
                print("DONE!")
        else:
            print("Test report NOT posted to Slack.")
