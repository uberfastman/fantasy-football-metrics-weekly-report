# written by Wren J.R.

import distutils.util as distutils
import getopt
import sys
from configparser import ConfigParser

from report.fantasy_football_report_builder import FantasyFootballReport
from utils.slack_messenger import SlackMessenger
from utils.upload_to_google_drive import GoogleDriveUploader

# local config vars
config = ConfigParser()
config.read("config.ini")


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hl:w:qbtds")
    except getopt.GetoptError:
        print("\nYahoo Fantasy Football report application usage:\n"
              "     python main.py -t -l <yahoo_league_id> -w <chosen_week>\n")
        sys.exit(2)

    options_dict = {}
    for opt, arg in opts:
        if opt == "-h":
            print("\nYahoo Fantasy Football report application usage:\n"
                  "     python main.py -t -l <yahoo_league_id> -w <chosen_week>\n")
            sys.exit()
        elif opt in ("-l", "--league-id"):
            options_dict["league_id"] = arg
        elif opt in ("-w", "--week"):
            if int(arg) < 1 or int(arg) > 17:
                print("\nPlease select a valid week number between 1 and 17.")
                options_dict["week"] = select_week()
            else:
                options_dict["week"] = arg
        elif opt in ("-q", "--disqualify-ce"):
            options_dict["dq_ce_bool"] = True
        elif opt in ("-b", "--break-ties"):
            options_dict["break_ties_bool"] = True
        elif opt in ("-t", "--test"):
            options_dict["test_bool"] = True
        elif opt in ("-d", "--dev"):
            options_dict["dev_bool"] = True
        elif opt in ("-s", "--save"):
            options_dict["save_bool"] = True

    return options_dict


def select_league(league_id, week, dq_ce_bool, break_ties_bool, test_bool, dev_bool, save_bool):

    if not league_id:
        default = input("Generate report for default league? (y/n) -> ")
    else:
        default = None

    if default == "y":

        if not week:
            chosen_week = select_week()
        else:
            chosen_week = week

        return FantasyFootballReport(week=chosen_week,
                                     dq_ce_bool=dq_ce_bool,
                                     break_ties_bool=break_ties_bool,
                                     test_bool=test_bool,
                                     dev_bool=dev_bool,
                                     save_bool=save_bool)
    elif default == "n":
        league_id = input(
            "What is the league ID of the Yahoo league for which you want to generate a report? -> ")

        if not week:
            chosen_week = select_week()
        else:
            chosen_week = week

        try:
            return FantasyFootballReport(league_id=league_id,
                                         week=chosen_week,
                                         dq_ce_bool=dq_ce_bool,
                                         break_ties_bool=break_ties_bool,
                                         test_bool=test_bool,
                                         dev_bool=dev_bool,
                                         save_bool=save_bool)

        except IndexError:
            print("The league ID you have selected is not valid.")
            select_league(week, dq_ce_bool, break_ties_bool, test_bool, dev_bool, save_bool)

    else:
        print("You must select either 'y' or 'n'.")
        select_league(week, dq_ce_bool, break_ties_bool, test_bool, dev_bool, save_bool)


def select_week():
    default = input("Generate report for default week? (y/n) -> ")
    if default == "y":
        return None
    elif default == "n":
        chosen_week = input("For which week would you like to generate a report? (1 - 17) -> ")
        if 0 < int(chosen_week) < 18:
            return chosen_week
        else:
            print("Please select a valid week number between 1 and 17.")
            select_week()
    else:
        print("You must select either 'y' or 'n'.")
        select_week()


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == '__main__':

    options = main(sys.argv[1:])

    report = select_league(options.get("league_id", None),
                           options.get("week", None),
                           options.get("dq_ce_bool", False),
                           options.get("break_ties_bool", False),
                           options.get("test_bool", False),
                           options.get("dev_bool", False),
                           options.get("save_bool", False))
    report_pdf = report.create_pdf_report()

    upload_file_to_google_drive_bool = bool(
        distutils.strtobool(config.get("Google_Drive_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        if not options.get("test_bool", False):
            # upload pdf to google drive
            google_drive_uploader = GoogleDriveUploader(report_pdf)
            upload_message = google_drive_uploader.upload_file()
            print(upload_message)
        else:
            print("Test report NOT uploaded to Google Drive.")

    post_to_slack_bool = bool(distutils.strtobool(config.get("Slack_Settings", "post_to_slack")))
    if post_to_slack_bool:
        if not options.get("test_bool", False):
            slack_messenger = SlackMessenger(config)
            # post shareable link to uploaded google drive pdf on slack
            # print(slack_messenger.post_to_selected_slack_channel(upload_message))

            # upload pdf report directly to slack
            print(slack_messenger.upload_file_to_selected_slack_channel(report_pdf))
            print("DONE!")
        else:
            print("Test report NOT posted to Slack.")
