__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import sys

if not sys.warnoptions:
    import warnings

    # suppress SyntaxWarning due to "invalid escape sequence" messages in transitive dependencies: rauth, stringcase
    warnings.filterwarnings("ignore", category=SyntaxWarning)

import os
import time
from argparse import ArgumentParser, HelpFormatter, Namespace
from datetime import datetime
from importlib.metadata import distributions
from pathlib import Path
from typing import Optional, Union

import colorama
from colorama import Fore, Style

from ffmwr.integrations.discord import DiscordIntegration
from ffmwr.integrations.drive import GoogleDriveIntegration
from ffmwr.integrations.groupme import GroupMeIntegration
from ffmwr.integrations.slack import SlackIntegration
from ffmwr.report.builder import FantasyFootballReport
from ffmwr.utilities.app import check_github_for_updates
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file
from ffmwr.utilities.utils import format_platform_display, normalize_dependency_package_name

colorama.init()

logger = get_logger()


def select_league(
    settings: AppSettings,
    use_default: bool,
    platform: str,
    game_id: Union[int, str],
    league_id: Union[str, None],
    season: int,
    start_week: int,
    week_for_report: int,
    break_ties: bool,
    playoff_prob_sims: int,
    dq_ce: bool,
    save_data: bool,
    refresh_feature_web_data: bool,
    offline: bool,
    test: bool,
) -> FantasyFootballReport:
    # set "use default" environment variable for access by fantasy football platforms
    if use_default:
        os.environ["USE_DEFAULT"] = "1"

    if not platform:
        platform = select_platform(settings, use_default=use_default)

    if not week_for_report:
        week_for_report = select_week(settings, use_default=use_default)

    if not league_id:
        if not use_default:
            time.sleep(0.25)
            selection = input(
                f"{Fore.YELLOW}Generate report for default league? "
                f"({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
            ).lower()
        else:
            logger.info('Use-default is set to "true". Automatically running the report for the default league.')
            selection = "y"
    else:
        selection = "selected"

    if selection == "y":
        return FantasyFootballReport(
            settings=settings,
            week_for_report=week_for_report,
            platform=platform,
            game_id=game_id,
            season=season,
            start_week=start_week,
            playoff_prob_sims=playoff_prob_sims,
            break_ties=break_ties,
            dq_ce=dq_ce,
            save_data=save_data,
            refresh_feature_web_data=refresh_feature_web_data,
            offline=offline,
            test=test,
        )
    elif selection == "n":
        league_id = input(
            f"{Fore.YELLOW}What is the league ID of the league for which you want to generate a report? "
            f"-> {Style.RESET_ALL}"
        )
        try:
            return FantasyFootballReport(
                settings=settings,
                week_for_report=week_for_report,
                platform=platform,
                league_id=league_id,
                game_id=game_id,
                season=season,
                start_week=start_week,
                playoff_prob_sims=playoff_prob_sims,
                break_ties=break_ties,
                dq_ce=dq_ce,
                save_data=save_data,
                refresh_feature_web_data=refresh_feature_web_data,
                offline=offline,
                test=test,
            )
        except IndexError:
            logger.error("The league ID you have selected is not valid.")
            select_league(
                settings,
                use_default,
                platform,
                game_id,
                None,
                season,
                start_week,
                week_for_report,
                break_ties,
                playoff_prob_sims,
                dq_ce,
                save_data,
                refresh_feature_web_data,
                offline,
                test,
            )
    elif selection == "selected":
        return FantasyFootballReport(
            settings=settings,
            week_for_report=week_for_report,
            platform=platform,
            league_id=league_id,
            game_id=game_id,
            season=season,
            start_week=start_week,
            playoff_prob_sims=playoff_prob_sims,
            break_ties=break_ties,
            dq_ce=dq_ce,
            save_data=save_data,
            refresh_feature_web_data=refresh_feature_web_data,
            offline=offline,
            test=test,
        )
    else:
        logger.warning('You must select either "y" or "n".')
        time.sleep(0.25)
        select_league(
            settings,
            use_default,
            platform,
            game_id,
            None,
            season,
            start_week,
            week_for_report,
            break_ties,
            playoff_prob_sims,
            dq_ce,
            save_data,
            refresh_feature_web_data,
            offline,
            test,
        )


def select_platform(settings: AppSettings, use_default: bool = False) -> str:
    if not use_default:
        time.sleep(0.25)
        selection = input(
            f"{Fore.YELLOW}Generate report for default platform? ({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) "
            f"-> {Style.RESET_ALL}"
        ).lower()
    else:
        logger.info('Use-default is set to "true". Automatically running the report for the default platform.')
        selection = "y"

    if selection == "y":
        if settings.platform in settings.supported_platforms_list:
            return settings.platform
        else:
            logger.warning(
                f'Generating fantasy football reports for the "{format_platform_display(settings.platform)}" fantasy '
                f"football platform is not currently supported. Please change the settings in your .env file and try "
                f"again."
            )
            sys.exit(1)
    elif selection == "n":
        chosen_platform = input(
            f"{Fore.YELLOW}For which platform would you like to generate a report ? "
            f"({Fore.GREEN}{f'{Fore.YELLOW}/{Fore.GREEN}'.join(settings.supported_platforms_list)}{Fore.YELLOW}) "
            f"-> {Style.RESET_ALL}"
        ).lower()

        if chosen_platform in settings.supported_platforms_list:
            return chosen_platform
        else:
            logger.warning(
                f'Generating fantasy football reports for the "{format_platform_display(chosen_platform)}" fantasy '
                f'football platform is not currently supported. Please select a valid platform from '
                f'{"/".join(settings.supported_platforms_list)}. '
                f'-> {Style.RESET_ALL}'
            )
            time.sleep(0.25)
            return select_platform(settings, use_default=use_default)
    else:
        logger.warning('You must select either "y" or "n".')
        time.sleep(0.25)
        return select_platform(settings, use_default=use_default)


def select_week(settings: AppSettings, use_default: bool = False) -> Optional[int]:
    if not use_default:
        time.sleep(0.25)
        selection = input(
            f"{Fore.YELLOW}Generate report for default week? ({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) "
            f"-> {Style.RESET_ALL}"
        ).lower()
    else:
        logger.info(
            'Use-default is set to "true". Automatically running the report for the default (most recent) week.'
        )
        selection = "y"

    if selection == "y":
        return None
    elif selection == "n":
        chosen_week = int(
            input(
                f"{Fore.YELLOW}For which week would you like to generate a report? "
                f"({Fore.GREEN}1{Fore.YELLOW} - {Fore.GREEN}{settings.nfl_season_length}{Fore.YELLOW}) -> "
                f"{Style.RESET_ALL}"
            ).lower()
        )
        if 0 < chosen_week <= settings.nfl_season_length:
            return chosen_week
        else:
            logger.warning(f"Please select a valid week number between 1 and {settings.nfl_season_length}.")
            time.sleep(0.25)
            return select_week(settings, use_default=use_default)
    else:
        logger.warning('You must select either "y" or "n".')
        time.sleep(0.25)
        return select_week(settings, use_default=use_default)


def main() -> None:
    dependencies = []
    with open(Path(__file__).parent / "requirements.txt", "r") as reqs:
        for line in reqs.readlines():
            if not line.startswith("#"):
                dep, dep_version = line.strip().split("==")
                dependencies.append(f"{normalize_dependency_package_name(dep)}=={dep_version}")

    installed_dependencies = sorted(
        [f"{normalize_dependency_package_name(x.name)}=={x.version}" for x in distributions()]
    )

    missing_dependency_count = 0
    for dependency in dependencies:
        if dependency not in installed_dependencies:
            missing_dependency_count += 1
            logger.error(
                f"MISSING DEPENDENCY: {dependency}. Please run `uv add {dependency}` and retry the report generation."
            )

    if missing_dependency_count > 0:
        logger.error(
            f"MISSING {missing_dependency_count} " + ("DEPENDENCY" if missing_dependency_count == 1 else "DEPENDENCIES")
        )
        sys.exit(1)

    root_directory = Path(__file__).parent

    app_settings: AppSettings = get_app_settings_from_env_file(root_directory / ".env")

    arg_parser = ArgumentParser(
        prog="python main.py",
        description=(
            "The Fantasy Football Metrics Weekly Report application automatically generates a report in the form of a "
            "PDF file that contains a host of metrics and rankings for teams in a given fantasy football league."
        ),
        epilog="The FFWMR is developed and maintained by Wren J. R. (uberfastman).",
        formatter_class=lambda prog: HelpFormatter(prog, max_help_position=40, width=120),
        add_help=True,
    )

    report_configuration_group = arg_parser.add_argument_group("report generation (optional)")
    report_configuration_group.add_argument(
        "-p",
        "--fantasy-platform",
        metavar="<platform>",
        type=str,
        required=False,
        help=(
            f"Fantasy football platform on which league for report is hosted. "
            f"Currently supports: {', '.join(app_settings.supported_platforms_list)}"
        ),
    )
    report_configuration_group.add_argument(
        "-l",
        "--league-id",
        metavar="<league_id>",
        type=str,
        required=False,
        help="Fantasy Football league ID",
    )
    report_configuration_group.add_argument(
        "-g",
        "--yahoo-game-id",
        metavar="<yahoo_game_id>",
        type=str,
        required=False,
        help=(
            "(Yahoo only) Chosen fantasy game id for which to generate report. Defaults to "
            '"nfl", which is interpreted as the current season on Yahoo'
        ),
    )
    report_configuration_group.add_argument(
        "-y",
        "--year",
        metavar="<YYYY>",
        type=int,
        required=False,
        help="Chosen year (season) of the league for which a report is being generated",
    )
    report_configuration_group.add_argument(
        "-k",
        "--start-week",
        metavar="<league_start_week>",
        type=int,
        required=False,
        help="League start week (if league started later than week 1)",
    )
    report_configuration_group.add_argument(
        "-w",
        "--week",
        metavar="<week>",
        type=int,
        required=False,
        help="Chosen week for which to generate report",
    )
    report_configuration_group.add_argument(
        "-d",
        "--use-default",
        action="store_true",
        required=False,
        help="Run the report using the default settings (in .env file) without user input",
    )

    report_run_group = arg_parser.add_argument_group("report run (optional)")
    report_run_group.add_argument(
        "-s",
        "--save-data",
        action="store_true",
        required=False,
        help="Save all fantasy league data for faster future report generation",
    )
    report_run_group.add_argument(
        "-r",
        "--refresh-feature-web-data",
        action="store_true",
        required=False,
        help="Refresh all feature web data",
    )
    report_run_group.add_argument(
        "-m",
        "--playoff-prob-sims",
        metavar="<num_sims>",
        type=int,
        required=False,
        help="Number of Monte Carlo playoff probability simulations to run",
    )
    report_run_group.add_argument(
        "-b",
        "--break-ties",
        action="store_true",
        required=False,
        help="Break ties in metric rankings",
    )
    report_run_group.add_argument(
        "-q",
        "--disqualify-coaching-efficiency",
        action="store_true",
        required=False,
        help="Automatically disqualify teams ineligible for coaching efficiency metric",
    )

    development_group = arg_parser.add_argument_group("development (optional)")
    development_group.add_argument(
        "-o",
        "--offline",
        action="store_true",
        required=False,
        help="Run OFFLINE for development (must have previously run report with -s option)",
    )
    development_group.add_argument(
        "-u",
        "--skip-uploads",
        action="store_true",
        required=False,
        help="Skip all integration uploads regardless of the configured settings",
    )
    development_group.add_argument(
        "-t",
        "--test",
        action="store_true",
        required=False,
        help="Generate TEST report",
    )

    args: Namespace = arg_parser.parse_args()

    if app_settings.check_for_updates:
        # check to see if the current app is behind any commits, and provide option to update and re-run if behind
        check_github_for_updates(args.use_default)

    f_str_newline = "\n"
    args_display = f"{f_str_newline}".join(
        # [f"{' ' * (len(max(vars(args).keys(), key=len)) - len(k))}{k} = {v}" for k, v in vars(args).items()]
        [f"  {k}{'.' * (len(max(vars(args).keys(), key=len)) - len(k))}...{v}" for k, v in vars(args).items()]
    )
    # verification output message
    logger.info(
        f"{f_str_newline}"
        f"Generating{' TEST' if args.test else ''} "
        f"{format_platform_display(args.fantasy_platform if args.fantasy_platform else app_settings.platform)} "
        f"Fantasy Football report on {datetime.now():%b %-d, %Y at %-I:%M%p} with the following command line arguments:"
        f"{f_str_newline * 2}"
        f"{args_display}"
        f"{f_str_newline}"
    )

    report = select_league(
        app_settings,
        args.use_default,
        args.fantasy_platform,
        args.yahoo_game_id,
        args.league_id,
        args.year,
        args.start_week,
        args.week,
        args.break_ties,
        args.playoff_prob_sims,
        args.disqualify_coaching_efficiency,
        args.save_data,
        args.refresh_feature_web_data,
        args.offline,
        args.test,
    )
    report_pdf: Path = report.create_pdf_report()

    upload_message = ""
    if app_settings.integration_settings.google_drive_upload_bool:
        if not args.skip_uploads and not args.test:
            google_drive_integration = GoogleDriveIntegration(
                app_settings, root_directory, report.league.week_for_report
            )

            # upload PDF to Google Drive
            upload_message = google_drive_integration.upload_file(report_pdf)
            logger.info(upload_message)
        else:
            logger.info(f"Report NOT uploaded to Google Drive with command line arguments: {args}")

    if app_settings.integration_settings.slack_post_bool:
        if not args.skip_uploads and not args.test:
            slack_integration = SlackIntegration(app_settings, root_directory, report.league.week_for_report)

            # post PDF or link to PDF to Slack
            slack_response = None
            post_or_file = app_settings.integration_settings.slack_post_or_file
            if post_or_file == "post":
                if app_settings.integration_settings.google_drive_upload_bool:
                    # post shareable link to uploaded Google Drive PDF on Slack
                    slack_response = slack_integration.post_message(upload_message)
                else:
                    logger.warning("Unable to post Google Drive link to Slack when GOOGLE_DRIVE_UPLOAD_BOOL=False.")
            elif post_or_file == "file":
                # upload PDF report directly to Slack
                slack_response = slack_integration.upload_file(report_pdf)
            else:
                logger.warning(
                    f'The ".env" file contains unsupported Slack setting: '
                    f'SLACK_POST_OR_FILE={post_or_file}. Please choose "post" or "file" and try again.'
                )
                sys.exit(1)

            if slack_response and slack_response.get("ok"):
                logger.info(f"Report {str(report_pdf)} successfully posted to Slack!")
            else:
                logger.error(f"Report {str(report_pdf)} was NOT posted to Slack with error: {slack_response}")
        else:
            logger.info(f"Report NOT posted to Slack with command line arguments: {args}")

    if app_settings.integration_settings.groupme_post_bool:
        if not args.skip_uploads and not args.test:
            groupme_integration = GroupMeIntegration(app_settings, root_directory, report.league.week_for_report)

            # post PDF or link to PDF to GroupMe
            groupme_response = None
            post_or_file = app_settings.integration_settings.groupme_post_or_file
            if post_or_file == "post":
                if app_settings.integration_settings.google_drive_upload_bool:
                    # post shareable link to uploaded Google Drive PDF on GroupMe
                    groupme_response = groupme_integration.post_message(upload_message)
                else:
                    logger.warning("Unable to post Google Drive link to GroupMe when GOOGLE_DRIVE_UPLOAD_BOOL=False.")
            elif post_or_file == "file":
                # upload PDF report directly to GroupMe
                groupme_response = groupme_integration.upload_file(report_pdf)
            else:
                logger.warning(
                    f'The ".env" file contains unsupported GroupMe setting: '
                    f'GROUPME_POST_OR_FILE={post_or_file}. Please choose "post" or "file" and try again.'
                )
                sys.exit(1)

            if groupme_response == 202 or groupme_response["meta"]["code"] == 201:
                logger.info(f"Report {str(report_pdf)} successfully posted to GroupMe!")
            else:
                logger.error(f"Report {str(report_pdf)} was NOT posted to GroupMe with error: {groupme_response}")
        else:
            logger.info(f"Report NOT posted to GroupMe with command line arguments: {args}")

    if app_settings.integration_settings.discord_post_bool:
        if not args.skip_uploads and not args.test:
            discord_integration = DiscordIntegration(app_settings, root_directory, report.league.week_for_report)

            # post PDF or link to PDF to Discord
            discord_response = None
            post_or_file = app_settings.integration_settings.discord_post_or_file
            if post_or_file == "post":
                if app_settings.integration_settings.google_drive_upload_bool:
                    # post shareable link to uploaded Google Drive PDF on Discord
                    discord_response = discord_integration.post_message(upload_message)
                else:
                    logger.warning("Unable to post Google Drive link to Discord when GOOGLE_DRIVE_UPLOAD_BOOL=False.")

            elif post_or_file == "file":
                # upload PDF report directly to Discord
                discord_response = discord_integration.upload_file(report_pdf)
            else:
                logger.warning(
                    f'The ".env" file contains unsupported Discord setting: '
                    f'DISCORD_POST_OR_FILE={post_or_file}. Please choose "post" or "file" and try again.'
                )
                sys.exit(1)

            if discord_response and discord_response.get("type") == 0:
                logger.info(f"Report {str(report_pdf)} successfully posted to Discord!")
            else:
                logger.error(f"Report {str(report_pdf)} was NOT posted to Discord with error: {discord_response}")
        else:
            logger.info(f"Report NOT posted to Discord with command line arguments: {args}")


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == "__main__":
    main()
