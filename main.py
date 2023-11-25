__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import getopt
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Union

import colorama
from colorama import Fore, Style

from integrations.drive_integration import GoogleDriveUploader
from integrations.slack_integration import SlackMessenger
from report.builder import FantasyFootballReport
from utilities.app import check_for_updates
from utilities.logger import get_logger
from utilities.settings import settings

colorama.init()

logger = get_logger()

NFL_SEASON_LENGTH = 18


def main(argv):
    logger.debug(f"Running fantasy football metrics weekly report app with arguments:\n{argv}")

    dependencies = []
    with open(Path(__file__).parent / "requirements.txt", "r") as reqs:
        for line in reqs.readlines():
            if not line.startswith("#"):
                dependencies.append(line.strip())

    installed_dependencies = subprocess.check_output(["pip", "freeze"]).decode("utf-8")
    missing_dependency_count = 0
    for dependency in dependencies:
        dependency_is_installed = installed_dependencies.find(dependency) != -1
        if not dependency_is_installed:
            missing_dependency_count += 1
            dependency_package = re.split("\\W+", dependency)[0]
            logger.error(
                f"MISSING DEPENDENCY: {dependency_package}. Please run `pip install {dependency_package}` and retry "
                f"the report generation."
            )

    if missing_dependency_count > 0:
        logger.error(
            f"MISSING {missing_dependency_count} " + ("DEPENDENCY" if missing_dependency_count == 1 else "DEPENDENCIES")
        )
        sys.exit(1)

    usage_str = (
        "\n"
        "Fantasy Football Report application usage:\n"
        "\n"
        "    python main.py [optional_parameters]\n"
        "\n"
        "    Options:\n"
        "      -h, --help                            Print command line usage message.\n"
        "      -d, --use-default                     Run the report using the default settings without user input prompts.\n"
        "\n"
        "    Generate report:\n"
        "      -f, --fantasy-platform <platform>     Fantasy football platform on which league for report is hosted. Currently supports: \"yahoo\", \"fleaflicker\" \n"
        "      -l, --league-id <league_id>           Fantasy Football league ID.\n"
        "      -w, --week <chosen_week>              Chosen week for which to generate report.\n"
        "      -k, --start-week <league_start_week>  League start week (if league started later than week 1).\n"
        "      -g, --game-id <chosen_game_id>        Chosen fantasy game id for which to generate report. Defaults to \"nfl\", which is interpreted as the current season if using Yahoo.\n"
        "      -y, --year <chosen_year>              Chosen year (season) of the league for which a report is being generated.\n"
        "\n"
        "    Settings:\n"
        "      -s, --save-data                       Save all retrieved data locally for faster future report generation.\n"
        "      -r, --refresh-web-data                Refresh all web data from external APIs (such as bad boy and beef data).\n"
        "      -p, --playoff-prob-sims               Number of Monte Carlo playoff probability simulations to run.\n"
        "      -b, --break-ties                      Break ties in metric rankings.\n"
        "      -q, --disqualify-ce                   Automatically disqualify teams ineligible for coaching efficiency metric.\n"
        "\n"
        "    For Developers:\n"
        "      -o, --offline                         Run OFFLINE for development. Must have previously run report with -s option.\n"
        "      -t, --test                            Generate TEST report.\n"
    )

    try:
        opts, args = getopt.getopt(argv, "hdf:l:w:k:g:y:srp:bqot")
    except getopt.GetoptError:
        print(usage_str)
        sys.exit(2)

    options_dict = {}
    for opt, arg in opts:
        # help/manual
        if opt in ("-h", "--help"):
            print(usage_str)
            sys.exit(0)

        # automatically run the report using the default settings without user input prompts
        elif opt in ("-d", "--use-default"):
            options_dict["use_default"] = True

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
                options_dict["week"] = int(arg)
        elif opt in ("-k", "--start-week"):
            options_dict["start_week"] = int(arg)
        elif opt in ("-g", "--game-id"):
            options_dict["game_id"] = arg
        elif opt in ("-y", "--year"):
            options_dict["year"] = int(arg)

        # report settings
        elif opt in ("-s", "--save-data"):
            options_dict["save_data"] = True
        elif opt in ("-r", "--refresh-web-data"):
            options_dict["refresh_web_data"] = True
        elif opt in ("-p", "--playoff-prob-sims"):
            options_dict["playoff_prob_sims"] = int(arg)
        elif opt in ("-b", "--break-ties"):
            options_dict["break_ties"] = True
        elif opt in ("-q", "--disqualify-ce"):
            options_dict["dq_ce"] = True

        # for developers
        elif opt in ("-t", "--test"):
            options_dict["test"] = True
        elif opt in ("-o", "--offline"):
            options_dict["offline"] = True

    return options_dict


def select_league(use_default: bool, week: int, start_week: int, platform: str,
                  league_id: Union[str, None], game_id: Union[int, str], season: int, refresh_web_data: bool,
                  playoff_prob_sims: int, break_ties: bool, dq_ce: bool, save_data: bool,
                  offline: bool, test: bool) -> FantasyFootballReport:
    # set "use default" environment variable for access by fantasy football platforms
    if use_default:
        os.environ["USE_DEFAULT"] = "1"

    if not league_id:
        if not use_default:
            time.sleep(0.25)
            selection = input(
                f"{Fore.YELLOW}Generate report for default league? "
                f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
            ).lower()
        else:
            logger.info("Use-default is set to \"true\". Automatically running the report for the default league.")
            selection = "y"
    else:
        selection = "selected"

    if selection == "y":

        if not week:
            week_for_report = select_week(use_default)
        else:
            week_for_report = week

        return FantasyFootballReport(
            week_for_report=week_for_report,
            platform=platform,
            game_id=game_id,
            season=season,
            start_week=start_week,
            refresh_web_data=refresh_web_data,
            playoff_prob_sims=playoff_prob_sims,
            break_ties=break_ties,
            dq_ce=dq_ce,
            save_data=save_data,
            offline=offline,
            test=test
        )
    elif selection == "n":
        league_id = input(
            f"{Fore.YELLOW}What is the league ID of the league for which you want to generate a report? "
            f"-> {Style.RESET_ALL}"
        )

        if not week:
            week_for_report = select_week()
        else:
            week_for_report = week

        try:
            return FantasyFootballReport(
                week_for_report=week_for_report,
                platform=platform,
                league_id=league_id,
                game_id=game_id,
                season=season,
                start_week=start_week,
                refresh_web_data=refresh_web_data,
                playoff_prob_sims=playoff_prob_sims,
                break_ties=break_ties,
                dq_ce=dq_ce,
                save_data=save_data,
                offline=offline,
                test=test
            )
        except IndexError:
            logger.error("The league ID you have selected is not valid.")
            select_league(
                use_default, week, start_week, platform, None, game_id, season, refresh_web_data,
                playoff_prob_sims, break_ties, dq_ce, save_data, offline, test
            )
    elif selection == "selected":

        if not week:
            week_for_report = select_week(use_default)
        else:
            week_for_report = week

        return FantasyFootballReport(
            week_for_report=week_for_report,
            platform=platform,
            league_id=league_id,
            game_id=game_id,
            season=season,
            start_week=start_week,
            refresh_web_data=refresh_web_data,
            playoff_prob_sims=playoff_prob_sims,
            break_ties=break_ties,
            dq_ce=dq_ce,
            save_data=save_data,
            offline=offline,
            test=test
        )
    else:
        logger.warning("You must select either \"y\" or \"n\".")
        time.sleep(0.25)
        select_league(
            use_default, week, start_week, platform, None, game_id, season, refresh_web_data,
            playoff_prob_sims, break_ties, dq_ce, save_data, offline, test
        )


def select_week(use_default: bool = False) -> Union[int, None]:
    if not use_default:
        time.sleep(0.25)
        selection = input(
            f"{Fore.YELLOW}Generate report for default week? ({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) "
            f"-> {Style.RESET_ALL}"
        ).lower()
    else:
        logger.info(
            "Use-default is set to \"true\". Automatically running the report for the default (most recent) week."
        )
        selection = "y"

    if selection == "y":
        return None
    elif selection == "n":
        chosen_week = int(input(
            f"{Fore.YELLOW}For which week would you like to generate a report? "
            f"({Fore.GREEN}1{Fore.YELLOW} - {Fore.GREEN}{NFL_SEASON_LENGTH}{Fore.YELLOW}) -> {Style.RESET_ALL}"
        ).lower())
        if 0 < chosen_week <= NFL_SEASON_LENGTH:
            return chosen_week
        else:
            logger.warning(f"Please select a valid week number between 1 and {NFL_SEASON_LENGTH}.")
            time.sleep(0.25)
            select_week(use_default)
    else:
        logger.warning("You must select either \"y\" or \"n\".")
        time.sleep(0.25)
        select_week(use_default)


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == "__main__":

    options = main(sys.argv[1:])
    logger.debug(f"Fantasy football metrics weekly report app settings options:\n{options}")

    # check to see if the current app is behind any commits, and provide option to update and re-run if behind
    up_to_date = check_for_updates(options.get("use_default", False))

    report = select_league(
        options.get("use_default", False),
        options.get("week", None),
        options.get("start_week", None),
        options.get("platform", None),
        options.get("league_id", None),
        options.get("game_id", None),
        options.get("year", None),
        options.get("refresh_web_data", False),
        options.get("playoff_prob_sims", None),
        options.get("break_ties", False),
        options.get("dq_ce", False),
        options.get("save_data", False),
        options.get("offline", False),
        options.get("test", False))
    report_pdf = report.create_pdf_report()

    upload_file_to_google_drive = settings.integration_settings.google_drive_upload_bool
    upload_message = ""
    if upload_file_to_google_drive:
        if not options.get("test", False):
            # upload pdf to google drive
            google_drive_uploader = GoogleDriveUploader(report_pdf)
            upload_message = google_drive_uploader.upload_file()
            logger.info(upload_message)
        else:
            logger.info("Test report NOT uploaded to Google Drive.")

    post_to_slack = settings.integration_settings.slack_post_bool
    if post_to_slack:
        if not options.get("test", False):
            # post pdf or link to pdf to slack
            slack_messenger = SlackMessenger()
            post_or_file = settings.integration_settings.slack_post_or_file

            if post_or_file == "post":
                # post shareable link to uploaded Google Drive pdf on slack
                slack_response = slack_messenger.post_to_selected_slack_channel(upload_message)
            elif post_or_file == "file":
                # upload pdf report directly to slack
                slack_response = slack_messenger.upload_file_to_selected_slack_channel(report_pdf)
            else:
                logger.warning(
                    f"The \".env\" file contains unsupported Slack setting: "
                    f"SLACK_POST_OR_FILE={post_or_file}. Please choose \"post\" or \"file\" and try again."
                )
                sys.exit(1)
            if slack_response.get("ok"):
                logger.info(f"Report {report_pdf} successfully posted to Slack!")
            else:
                logger.error(f"Report {report_pdf} was NOT posted to Slack with error: {slack_response.get('error')}")
        else:
            logger.info("Test report NOT posted to Slack.")
