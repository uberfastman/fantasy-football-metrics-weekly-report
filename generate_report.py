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
              "     python generate_report.py -t -l <yahoo_league_id> -w <chosen_week>\n")
        sys.exit(2)

    options_dict = {}
    for opt, arg in opts:
        if opt == "-h":
            print("\nYahoo Fantasy Football report application usage:\n"
                  "     python generate_report.py -t -l <yahoo_league_id> -w <chosen_week>\n")
            sys.exit()
        elif opt in ("-l", "--league-id"):
            options_dict["league_id"] = arg
        elif opt in ("-w", "--week"):
            if int(arg) < 1 or int(arg) > 17:
                print("\nPlease select a valid week number between 1 and 17.")
                options_dict["week"] = use_chosen_week_function()
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


def use_default_league_function(league_id, chosen_week_arg, dq_ce_bool, break_ties_bool, test_bool, dev_bool,
                                save_bool):
    if not league_id:
        use_default_league = input("Generate report for default league? (y/n) -> ")
    else:
        use_default_league = "selected"

    if use_default_league == "y":
        if not chosen_week_arg:
            chosen_week = use_chosen_week_function()
        else:
            chosen_week = chosen_week_arg
        fantasy_football_report_instance = FantasyFootballReport(user_input_chosen_week=chosen_week,
                                                                 dq_ce_bool=dq_ce_bool,
                                                                 break_ties_bool=break_ties_bool,
                                                                 test_bool=test_bool,
                                                                 dev_bool=dev_bool,
                                                                 save_bool=save_bool)
        return fantasy_football_report_instance, config.get("Fantasy_Football_Report_Settings", "league_id")
    elif use_default_league == "n":
        league_id = input(
            "What is the league ID of the Yahoo league for which you want to generate a report? -> ")
        try:
            fantasy_football_report_instance = FantasyFootballReport(user_input_league_id=league_id,
                                                                     user_input_chosen_week=use_chosen_week_function(),
                                                                     dq_ce_bool=dq_ce_bool,
                                                                     break_ties_bool=break_ties_bool,
                                                                     test_bool=test_bool,
                                                                     dev_bool=dev_bool,
                                                                     save_bool=save_bool)
            return fantasy_football_report_instance, str(league_id)
        except IndexError:
            print("The league ID you have selected is not valid.")
            use_default_league_function(chosen_week_arg, dq_ce_bool, break_ties_bool, test_bool, dev_bool, save_bool)
    elif use_default_league == "selected":
        if not chosen_week_arg:
            chosen_week = use_chosen_week_function()
        else:
            chosen_week = chosen_week_arg
        fantasy_football_report_instance = FantasyFootballReport(user_input_league_id=league_id,
                                                                 user_input_chosen_week=chosen_week,
                                                                 dq_ce_bool=dq_ce_bool,
                                                                 break_ties_bool=break_ties_bool,
                                                                 test_bool=test_bool,
                                                                 dev_bool=dev_bool,
                                                                 save_bool=save_bool)
        return fantasy_football_report_instance, str(league_id)
    else:
        print("You must select either 'y' or 'n'.")
        use_default_league_function(chosen_week_arg, dq_ce_bool, break_ties_bool, test_bool, dev_bool, save_bool)


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

    report_info = use_default_league_function(options.get("league_id", None),
                                              options.get("week", None),
                                              options.get("dq_ce_bool", False),
                                              options.get("break_ties_bool", False),
                                              options.get("test_bool", False),
                                              options.get("dev_bool", False),
                                              options.get("save_bool", False))
    fantasy_football_report = report_info[0]
    selected_league_id = report_info[1]
    generated_report = fantasy_football_report.create_pdf_report()

    upload_file_to_google_drive_bool = bool(
        distutils.strtobool(config.get("Google_Drive_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        if not options.get("test_bool", False):
            # upload pdf to google drive
            google_drive_uploader = GoogleDriveUploader(generated_report)
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
            print(slack_messenger.upload_file_to_selected_slack_channel(generated_report))
            print("DONE!")

        else:
            print("Test report NOT posted to Slack.")
