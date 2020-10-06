from flask import Flask
from flask_executor import Executor
from flask_shell2http import Shell2HTTP
import os

from main import main

from utils.app_config_parser import AppConfigParser
# noinspection PyUnresolvedReferences
from utils.api_logger import get_logger

logger = get_logger(__name__, propagate=False)

root_project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config_file_path = os.path.join(root_project_path, "config.ini")

config = AppConfigParser()
config.read(config_file_path)

# Flask application instance
app = Flask(__name__)
# redis = Redis(host="redis", port=6379)

executor = Executor(app)
shell2http = Shell2HTTP(app=app, executor=executor, base_url_prefix="/report/")


def run_report(context, future):
    """ Requires the below context structure:
        {
            "configuration": ["-l", <league_id>, "-f", <platform>, "-p", <playoff_sims>, "-y", <season>, "-w", <week_for_report>, etc.]
        }
    """
    # user-defined callback function
    """
    Will be invoked on every process completion
    
    """
    logger.info(context, future.result())

    run_configuration = context.get("configuration")

    platform = None
    league_id = None
    season = None
    week_for_report = None

    ndx = 0
    for arg in run_configuration:
        if arg == "-f":
            platform = run_configuration[ndx + 1]
        if arg == "-l":
            league_id = run_configuration[ndx + 1]
        if arg == "-y":
            season = run_configuration[ndx + 1]
        if arg == "-w":
            week_for_report = run_configuration[ndx + 1]
        ndx += 1

    output_dir = os.path.join(root_project_path, config.get("Configuration", "output_dir"))

    league_file_identifier = "{0}_league({1})".format(str(platform).lower(), str(league_id))

    report_save_dir = os.path.join(
        output_dir,
        str(season),
        league_file_identifier
    )
    filename = "{0}_week-{1}_report.pdf".format(league_file_identifier, str(week_for_report))

    report_file_path = os.path.join(report_save_dir, filename)

    logger.info("Report will be available at \"{0}\"".format(report_file_path))
    main(run_configuration)


shell2http.register_command(endpoint="run", command_name="python", callback_fn=run_report, decorators=[])

