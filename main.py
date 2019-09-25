__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import distutils.util as distutils
import getopt
import logging
import os
import re
import sys
import traceback
from configparser import ConfigParser

import pkg_resources
from pkg_resources import DistributionNotFound, VersionConflict

from report.fantasy_football_report_builder import FantasyFootballReport
from utils.slack_messenger import SlackMessenger
from utils.upload_to_google_drive import GoogleDriveUploader

# local config vars
config = ConfigParser()
config.read("config.ini")

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def main(argv):
    dependencies = []
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt"), "r") as reqs:
        for line in reqs.readlines():
            if not line.startswith("#"):
                dependencies.append(line.strip())

    missing_dependency_count = 0
    for dependency in dependencies:
        try:
            pkg_resources.require(dependency)
        except DistributionNotFound as dnfe:
            missing_dependency_count += 1
            logger.error("Error: {}\n{}".format(dnfe, traceback.format_exc()))
            logger.error(
                "MISSING DEPENDENCY: {}. Please run `pip install {}` and retry the report generation.".format(
                    dependency, re.split("\W+", dependency)[0]))
        except VersionConflict as vce:
            missing_dependency_count += 1
            logger.error("Error: {}\n{}".format(vce, traceback.format_exc()))
            logger.error(
                "MISSING DEPENDENCY: {}. Please run `pip install {}` and retry the report generation.".format(
                    dependency, dependency))

    if missing_dependency_count > 0:
        logger.error(
            "MISSING {} ".format(str(missing_dependency_count)) + (
                "DEPENDENCY" if missing_dependency_count == 1 else "DEPENDENCIES") +
            ". Report generation aborted.")
        sys.exit()

    usage_str = \
        "\n" \
        "Yahoo Fantasy Football report application usage:\n\n" \
        "    python main.py [optional_parameters]\n\n" \
        "  Options:\n" \
        "      -h, --help                         Print command line usage message.\n" \
        "    Generate report:\n" \
        "      -l, --league-id <yahoo_league_id>  Yahoo Fantasy Football league ID.\n" \
        "      -w, --week <chosen_week>           Chosen week for which to generate report.\n" \
        "      -g, --game-id <chosen_game_id>     Chosen Yahoo NFL fantasy game id for which to generate report. Defaults to \"nfl\", which Yahoo interprets as the current season.\n" \
        "      -y, --year <chosen_year>           Chosen year (season) of the league for which a report is being generated." \
        "    Configuration:\n" \
        "      -s, --save-data                    Save all retrieved data locally for faster future report generation.\n" \
        "      -p, --playoff-prob-sims            Number of Monte Carlo playoff probability simulations to run." \
        "      -b, --break-ties                   Break ties in metric rankings.\n" \
        "      -q, --disqualify-ce                Automatically disqualify teams ineligible for coaching efficiency metric.\n" \
        "    For Developers:\n" \
        "      -t, --test                         Generate TEST report.\n" \
        "      -d, --dev-offline                  Run OFFLINE for development. Must have previously run report with -s option.\n"

    try:
        opts, args = getopt.getopt(argv, "hl:w:g:y:sp:bqtd")
    except getopt.GetoptError:
        print(usage_str)
        sys.exit(2)

    options_dict = {}
    for opt, arg in opts:
        # help/manual
        if opt in ("-h", "--help"):
            print(usage_str)
            sys.exit()

        # generate report
        elif opt in ("-l", "--league-id"):
            options_dict["league_id"] = arg
        elif opt in ("-w", "--week"):
            if int(arg) < 1 or int(arg) > 17:
                print("\nPlease select a valid week number from 1 to 17.")
                options_dict["week"] = select_week()
            else:
                options_dict["week"] = arg
        elif opt in ("-g", "--game-id"):
            options_dict["game_id"] = arg
        elif opt in ("-y", "--year"):
            options_dict["year"] = arg

        # report configuration
        elif opt in ("-s", "--save-data"):
            options_dict["save_data"] = True
        elif opt in ("-p", "--playoff-prob-sims"):
            options_dict["playoff_prob_sims"] = arg
        elif opt in ("-b", "--break-ties"):
            options_dict["break_ties_bool"] = True
        elif opt in ("-q", "--disqualify-ce"):
            options_dict["dq_ce_bool"] = True

        # for developers
        elif opt in ("-t", "--test"):
            options_dict["test_bool"] = True
        elif opt in ("-d", "--dev-offline"):
            options_dict["dev_offline"] = True

    return options_dict


def select_league(league_id, week, game_id, save_data, playoff_prob_sims, break_ties_bool, dq_ce_bool, test_bool,
                  dev_offline):
    if not league_id:
        default = input("Generate report for default league? (y/n) -> ")
    else:
        default = "selected"

    if default == "y":

        if not week:
            chosen_week = select_week()
        else:
            chosen_week = week

        return FantasyFootballReport(week=chosen_week,
                                     game_id=game_id,
                                     save_data=save_data,
                                     playoff_prob_sims=playoff_prob_sims,
                                     break_ties_bool=break_ties_bool,
                                     dq_ce_bool=dq_ce_bool,
                                     test_bool=test_bool,
                                     dev_offline=dev_offline)
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
                                         game_id=game_id,
                                         save_data=save_data,
                                         playoff_prob_sims=playoff_prob_sims,
                                         break_ties_bool=break_ties_bool,
                                         dq_ce_bool=dq_ce_bool,
                                         test_bool=test_bool,
                                         dev_offline=dev_offline)

        except IndexError:
            print("The league ID you have selected is not valid.")
            select_league(None, week, game_id, save_data, playoff_prob_sims, break_ties_bool, dq_ce_bool, test_bool,
                          dev_offline)
    elif default == "selected":

        if not week:
            chosen_week = select_week()
        else:
            chosen_week = week

        return FantasyFootballReport(league_id=league_id,
                                     week=chosen_week,
                                     game_id=game_id,
                                     save_data=save_data,
                                     playoff_prob_sims=playoff_prob_sims,
                                     break_ties_bool=break_ties_bool,
                                     dq_ce_bool=dq_ce_bool,
                                     test_bool=test_bool,
                                     dev_offline=dev_offline)
    else:
        print("You must select either 'y' or 'n'.")
        select_league(None, week, game_id, save_data, playoff_prob_sims, break_ties_bool, dq_ce_bool, test_bool,
                      dev_offline)


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
                           options.get("game_id", None),
                           options.get("save_data", False),
                           options.get("playoff_prob_sims", None),
                           options.get("break_ties_bool", False),
                           options.get("dq_ce_bool", False),
                           options.get("test_bool", False),
                           options.get("dev_offline", False))
    report_pdf = report.create_pdf_report()

    upload_file_to_google_drive_bool = bool(
        distutils.strtobool(config.get("Google_Drive_Settings", "google_drive_upload")))
    upload_message = ""
    if upload_file_to_google_drive_bool:
        if not options.get("test_bool", False):
            # upload pdf to google drive
            google_drive_uploader = GoogleDriveUploader(report_pdf)
            upload_message = google_drive_uploader.upload_file()
            logger.info(upload_message)
        else:
            logger.info("Test report NOT uploaded to Google Drive.")

    post_to_slack_bool = bool(distutils.strtobool(config.get("Slack_Settings", "post_to_slack")))
    if post_to_slack_bool:
        if not options.get("test_bool", False):
            slack_messenger = SlackMessenger(config)
            # post shareable link to uploaded google drive pdf on slack
            # logger.info(slack_messenger.post_to_selected_slack_channel(upload_message))

            # upload pdf report directly to slack
            logger.info(slack_messenger.upload_file_to_selected_slack_channel(report_pdf))
            logger.info("DONE!")
        else:
            logger.info("Test report NOT posted to Slack.")
