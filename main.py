__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import getopt
import os
import re
import time
import sys
import traceback
import colorama
from colorama import Fore, Style

import pkg_resources
from pkg_resources import DistributionNotFound, VersionConflict

from integrations.drive_integration import GoogleDriveUploader
from integrations.slack_integration import SlackMessenger
from report.builder import FantasyFootballReport
from report.logger import get_logger
from utils.report_tools import check_for_updates, get_valid_config

colorama.init()

logger = get_logger()

NFL_SEASON_LENGTH = 18


def main(argv):
    logger.debug("Running fantasy football metrics weekly report app with arguments:\n{0}".format(argv))

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
            logger.error("Error: {0}\n{1}".format(dnfe, traceback.format_exc()))
            logger.error(
                "MISSING DEPENDENCY: {0}. Please run `pip install {1}` and retry the report generation.".format(
                    dependency, re.split("\\W+", dependency)[0]))
        except VersionConflict as vce:
            missing_dependency_count += 1
            logger.error("Error: {0}\n{1}".format(vce, traceback.format_exc()))
            logger.error(
                "MISSING DEPENDENCY: {0}. Please run `pip install {1}` and retry the report generation.".format(
                    dependency, dependency))

    if missing_dependency_count > 0:
        logger.error(
            "MISSING {0} ".format(str(missing_dependency_count)) + (
                "DEPENDENCY" if missing_dependency_count == 1 else "DEPENDENCIES"))
        sys.exit("...run aborted.")

    usage_str = \
        "\n" \
        "Fantasy Football Report application usage:\n" \
        "\n" \
        "    python main.py [optional_parameters]\n" \
        "\n" \
        "  Options:\n" \
        "      -h, --help                            Print command line usage message.\n" \
        "      -a, --auto-run                        Automatically run the report using the default week.\n" \
        "\n" \
        "    Generate report:\n" \
        "      -f, --fantasy-platform <platform>     Fantasy football platform on which league for report is hosted. Currently supports: \"yahoo\", \"fleaflicker\" \n" \
        "      -l, --league-id <league_id>           Fantasy Football league ID.\n" \
        "      -w, --week <chosen_week>              Chosen week for which to generate report.\n" \
        "      -g, --game-id <chosen_game_id>        Chosen fantasy game id for which to generate report. Defaults to \"nfl\", which is interpreted as the current season if using Yahoo.\n" \
        "      -y, --year <chosen_year>              Chosen year (season) of the league for which a report is being generated.\n" \
        "\n" \
        "    Configuration:\n" \
        "      -c, --config-file <config_file_path>  System file path (including file name) for .ini file to be used for configuration.\n" \
        "      -s, --save-data                       Save all retrieved data locally for faster future report generation.\n" \
        "      -r, --refresh-web-data                Refresh all web data from external APIs (such as bad boy and beef data).\n" \
        "      -p, --playoff-prob-sims               Number of Monte Carlo playoff probability simulations to run.\n" \
        "      -b, --break-ties                      Break ties in metric rankings.\n" \
        "      -q, --disqualify-ce                   Automatically disqualify teams ineligible for coaching efficiency metric.\n" \
        "\n" \
        "    For Developers:\n" \
        "      -d, --dev-offline                     Run OFFLINE for development. Must have previously run report with -s option.\n" \
        "      -t, --test                            Generate TEST report.\n"

    try:
        opts, args = getopt.getopt(argv, "hac:f:l:w:g:y:srp:bqtd")
    except getopt.GetoptError:
        print(usage_str)
        sys.exit(2)

    options_dict = {}
    for opt, arg in opts:
        # help/manual
        if opt in ("-h", "--help"):
            print(usage_str)
            sys.exit(0)

        # automatically run the report using the default week
        elif opt in ("-a", "--auto-run"):
            options_dict["auto_run"] = True

        # generate report
        elif opt in ("-f", "--fantasy-platform"):
            options_dict["platform"] = arg
        elif opt in ("-l", "--league-id"):
            options_dict["league_id"] = arg
        elif opt in ("-w", "--week"):
            if int(arg) < 1 or int(arg) > NFL_SEASON_LENGTH:
                logger.error(f"Please select a valid week number from 1 to {NFL_SEASON_LENGTH}.")
                options_dict["week"] = select_week()
            else:
                options_dict["week"] = arg
        elif opt in ("-g", "--game-id"):
            options_dict["game_id"] = arg
        elif opt in ("-y", "--year"):
            options_dict["year"] = arg

        # report configuration
        elif opt in ("-c", "--config-file"):
            options_dict["config_file"] = arg
        elif opt in ("-s", "--save-data"):
            options_dict["save_data"] = True
        elif opt in ("-r", "--refresh-web-data"):
            options_dict["refresh_web_data"] = True
        elif opt in ("-p", "--playoff-prob-sims"):
            options_dict["playoff_prob_sims"] = arg
        elif opt in ("-b", "--break-ties"):
            options_dict["break_ties"] = True
        elif opt in ("-q", "--disqualify-ce"):
            options_dict["dq_ce"] = True

        # for developers
        elif opt in ("-t", "--test"):
            options_dict["test"] = True
        elif opt in ("-d", "--dev-offline"):
            options_dict["dev_offline"] = True

    return options_dict


def select_league(config, auto_run, week, platform, league_id, game_id, season, refresh_web_data, playoff_prob_sims,
                  break_ties, dq_ce,save_data, dev_offline, test):
    if not league_id:
        time.sleep(0.25)
        default = input("{0}Generate report for default league? ({1}y{0}/{2}n{0}) -> {3}".format(
            Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
        ))
    else:
        default = "selected"

    if default == "y":

        if not week:
            week_for_report = select_week(auto_run)
        else:
            week_for_report = week

        return FantasyFootballReport(week_for_report=week_for_report,
                                     platform=platform,
                                     game_id=game_id,
                                     season=season,
                                     config=config,
                                     refresh_web_data=refresh_web_data,
                                     playoff_prob_sims=playoff_prob_sims,
                                     break_ties=break_ties,
                                     dq_ce=dq_ce,
                                     save_data=save_data,
                                     dev_offline=dev_offline,
                                     test=test)
    elif default == "n":
        league_id = input(
            "{0}What is the league ID of the league for which you want to generate a report? -> {3}".format(
                Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
            ))

        if not week:
            week_for_report = select_week(auto_run)
        else:
            week_for_report = week

        try:
            return FantasyFootballReport(week_for_report=week_for_report,
                                         platform=platform,
                                         league_id=league_id,
                                         game_id=game_id,
                                         season=season,
                                         config=config,
                                         refresh_web_data=refresh_web_data,
                                         playoff_prob_sims=playoff_prob_sims,
                                         break_ties=break_ties,
                                         dq_ce=dq_ce,
                                         save_data=save_data,
                                         dev_offline=dev_offline,
                                         test=test)
        except IndexError:
            logger.error("The league ID you have selected is not valid.")
            select_league(config, auto_run, week, platform, None, game_id, season, refresh_web_data, playoff_prob_sims,
                          break_ties, dq_ce, save_data, dev_offline, test)
    elif default == "selected":

        if not week:
            week_for_report = select_week(auto_run)
        else:
            week_for_report = week

        return FantasyFootballReport(week_for_report=week_for_report,
                                     platform=platform,
                                     league_id=league_id,
                                     game_id=game_id,
                                     season=season,
                                     config=config,
                                     refresh_web_data=refresh_web_data,
                                     playoff_prob_sims=playoff_prob_sims,
                                     break_ties=break_ties,
                                     dq_ce=dq_ce,
                                     save_data=save_data,
                                     dev_offline=dev_offline,
                                     test=test)
    else:
        logger.warning("You must select either \"y\" or \"n\".")
        time.sleep(0.25)
        select_league(config, auto_run, week, platform, None, game_id, season, refresh_web_data, playoff_prob_sims,
                      break_ties, dq_ce, save_data, dev_offline, test)


def select_week(auto_run=False):
    if not auto_run:
        time.sleep(0.25)
        default = input("{0}Generate report for default week? ({1}y{0}/{2}n{0}) -> {3}".format(
            Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL
        ))
    else:
        logger.info("Auto-run is set to \"true\". Automatically running the report for the default (most recent) week.")
        default = "y"

    if default == "y":
        return None
    elif default == "n":
        chosen_week = input(
            "{0}For which week would you like to generate a report? ({1}1{0} - {1}{4}{0}) -> {3}".format(
                Fore.YELLOW, Fore.GREEN, Fore.RED, Style.RESET_ALL, NFL_SEASON_LENGTH
            )
        )
        if 0 < int(chosen_week) <= NFL_SEASON_LENGTH:
            return chosen_week
        else:
            logger.warning(f"Please select a valid week number between 1 and {NFL_SEASON_LENGTH}.")
            time.sleep(0.25)
            select_week(auto_run)
    else:
        logger.warning("You must select either \"y\" or \"n\".")
        time.sleep(0.25)
        select_week(auto_run)


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == "__main__":

    options = main(sys.argv[1:])
    logger.debug(f"Fantasy football metrics weekly report app run configuration options:\n{options}")

    # set local config (check for existence and access, create config.ini if does not exist or stop app if inaccessible)
    if options.get("config_file"):
        configuration = get_valid_config(options.get("config_file"))
    else:
        configuration = get_valid_config()

    # check to see if the current app is behind any commits, and provide option to update and re-run if behind
    up_to_date = check_for_updates(options.get("auto_run", False))

    report = select_league(
        configuration,
        options.get("auto_run", False),
        options.get("week", None),
        options.get("platform", None),
        options.get("league_id", None),
        options.get("game_id", None),
        options.get("year", None),
        options.get("refresh_web_data", False),
        options.get("playoff_prob_sims", None),
        options.get("break_ties", False),
        options.get("dq_ce", False),
        options.get("save_data", False),
        options.get("dev_offline", False),
        options.get("test", False))
    report_pdf = report.create_pdf_report()

    upload_file_to_google_drive = configuration.getboolean("Drive", "google_drive_upload")
    upload_message = ""
    if upload_file_to_google_drive:
        if not options.get("test", False):
            # upload pdf to google drive
            google_drive_uploader = GoogleDriveUploader(report_pdf, configuration)
            upload_message = google_drive_uploader.upload_file()
            logger.info(upload_message)
        else:
            logger.info("Test report NOT uploaded to Google Drive.")

    post_to_slack = configuration.getboolean("Slack", "post_to_slack")
    if post_to_slack:
        if not options.get("test", False):
            # post pdf or link to pdf to slack
            slack_messenger = SlackMessenger(configuration)
            post_or_file = configuration.get("Slack", "post_or_file")

            if post_or_file == "post":
                # post shareable link to uploaded google drive pdf on slack
                slack_response = slack_messenger.post_to_selected_slack_channel(upload_message)
            elif post_or_file == "file":
                # upload pdf report directly to slack
                slack_response = slack_messenger.upload_file_to_selected_slack_channel(report_pdf)
            else:
                logger.warning(
                    "You have configured \"config.ini\" with unsupported Slack setting: post_or_file = {0}. "
                    "Please choose \"post\" or \"file\" and try again.".format(post_or_file))
                sys.exit("...run aborted.")
            if slack_response.get("ok"):
                logger.info("Report {0} successfully posted to Slack!".format(report_pdf))
            else:
                logger.error("Report {0} was NOT posted to Slack with error: {1}".format(
                    report_pdf, slack_response.get("error")))
        else:
            logger.info("Test report NOT posted to Slack.")
