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

from ffmwr.integrations.groupme import GroupMeIntegration
from ffmwr.report.builder import FantasyFootballReport
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file
from ffmwr.utilities.utils import normalize_dependency_package_name

colorama.init()

logger = get_logger()


def create_report(
    settings: AppSettings,
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
    platform = "espn"  # Hardcoded to ESPN

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


def main() -> None:
    # Check if we're in a uv managed project by looking for pyproject.toml
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    if not pyproject_path.exists():
        logger.error(
            "No pyproject.toml found. Please run `uv sync` to install dependencies and retry the report generation."
        )
        sys.exit(1)

    # Import tomllib for Python 3.11+ or tomli for older versions
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            logger.warning(
                "Cannot check dependencies without tomllib/tomli. Continuing..."
            )
            return

    # Read dependencies from pyproject.toml
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        dependencies = pyproject_data.get("project", {}).get("dependencies", [])

        installed_dependencies = sorted(
            [
                f"{normalize_dependency_package_name(x.name)}=={x.version}"
                for x in distributions()
            ]
        )

        missing_dependency_count = 0
        for dep_spec in dependencies:
            # Parse dependency specification (e.g., "colorama==0.4.6")
            if "==" in dep_spec:
                dep_name, dep_version = dep_spec.split("==")
                normalized_dep = (
                    f"{normalize_dependency_package_name(dep_name)}=={dep_version}"
                )
                if normalized_dep not in installed_dependencies:
                    missing_dependency_count += 1
                    logger.error(
                        f"MISSING DEPENDENCY: {normalized_dep}. Please run `uv sync` and retry the report generation."
                    )

        if missing_dependency_count > 0:
            logger.error(
                f"MISSING {missing_dependency_count} "
                + ("DEPENDENCY" if missing_dependency_count == 1 else "DEPENDENCIES")
            )
            logger.info("Run `uv sync` to install all required dependencies.")
            sys.exit(1)

    except Exception as e:
        logger.warning(f"Could not check dependencies: {e}. Continuing...")

    root_directory = Path(__file__).parent

    app_settings: AppSettings = get_app_settings_from_env_file(root_directory / ".env")

    arg_parser = ArgumentParser(
        prog="python main.py",
        description=(
            "The Fantasy Football Metrics Weekly Report application automatically generates a report in the form of a "
            "PDF file that contains a host of metrics and rankings for teams in a given fantasy football league."
        ),
        epilog="The FFWMR is developed and maintained by Wren J. R. (uberfastman).",
        formatter_class=lambda prog: HelpFormatter(
            prog, max_help_position=40, width=120
        ),
        add_help=True,
    )

    report_configuration_group = arg_parser.add_argument_group(
        "report generation (optional)"
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

    f_str_newline = "\n"
    args_display = f"{f_str_newline}".join(
        # [f"{' ' * (len(max(vars(args).keys(), key=len)) - len(k))}{k} = {v}" for k, v in vars(args).items()]
        [
            f"  {k}{'.' * (len(max(vars(args).keys(), key=len)) - len(k))}...{v}"
            for k, v in vars(args).items()
        ]
    )
    # verification output message
    logger.info(
        f"{f_str_newline}"
        f"Generating{' TEST' if args.test else ''} ESPN "
        f"Fantasy Football report on {datetime.now():%b %-d, %Y at %-I:%M%p} with the following command line arguments:"
        f"{f_str_newline * 2}"
        f"{args_display}"
        f"{f_str_newline}"
    )

    report = create_report(
        app_settings,
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

    if app_settings.integration_settings.groupme_post_bool:
        if not args.skip_uploads and not args.test:
            groupme_integration = GroupMeIntegration(
                app_settings, root_directory, report.league.week_for_report
            )

            # upload PDF report directly to GroupMe
            groupme_response = groupme_integration.upload_file(report_pdf)

            if groupme_response == 202 or groupme_response["meta"]["code"] == 201:
                logger.info(f"Report {str(report_pdf)} successfully posted to GroupMe!")
            else:
                logger.error(
                    f"Report {str(report_pdf)} was NOT posted to GroupMe with error: {groupme_response}"
                )
        else:
            logger.info(
                f"Report NOT posted to GroupMe with command line arguments: {args}"
            )


# RUN FANTASY FOOTBALL REPORT PROGRAM
if __name__ == "__main__":
    main()
