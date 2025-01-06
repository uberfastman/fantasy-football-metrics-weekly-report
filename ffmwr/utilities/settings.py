import json
import os
import sys
from datetime import datetime
from inspect import isclass
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from camel_converter import to_snake
from colorama import Fore, Style
from dotenv import dotenv_values
from pydantic import Field, computed_field

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.utils import FFMWRPythonObjectJson

logger = get_logger(__name__, propagate=False)


class CustomSettingsSource(EnvSettingsSource):
    @classmethod
    def convert_env_field_value_to_settings(cls, field_key: str, field_value: Any) -> Any:
        if isinstance(field_value, str):  # check if incoming field value is coming from a .env file or not
            if field_key.endswith("_int"):
                settings_field_value = int(field_value)
            elif field_key.endswith("_bool"):
                settings_field_value = str(field_value).lower() == "true"
            elif field_key.endswith("_list"):
                settings_field_value = field_value.split(",") if field_value else []
            elif field_key.endswith("_json"):
                settings_field_value = json.loads(field_value) if field_value else {}
            elif field_key.endswith("_path"):
                settings_field_value = Path(field_value) if field_value else None
            elif isinstance(field_value, str):
                settings_field_value = field_value or None
            else:
                settings_field_value = json.loads(field_value)
        else:
            settings_field_value = field_value

        return settings_field_value

    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        if value is None:
            settings_field_value = None
        elif field_name == "league_id":
            settings_field_value = str(value)
        elif field_name == "week_for_report":
            try:
                settings_field_value = int(value)
            except (ValueError, TypeError):
                settings_field_value = value
        else:
            settings_field_value = self.__class__.convert_env_field_value_to_settings(field_name, value)

        return settings_field_value


class CustomSettings(BaseSettings, FFMWRPythonObjectJson):
    def __repr__(self):
        properties = ", ".join([f"{k}={v}" for k, v in self.__dict__.items()])
        return f"{self.__class__.__name__}({properties})"

    def __str__(self):
        properties = ", ".join([f"{k}={v}" for k, v in self.__dict__.items()])
        return f"{self.__class__.__name__}({properties})"

    def __setattr__(self, key, value):
        value = CustomSettingsSource.convert_env_field_value_to_settings(key, value)
        super().__setattr__(key, value)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (CustomSettingsSource(settings_cls),)

    @classmethod
    def get_fields(cls, parent_cls=None) -> Set[Tuple[str, str, str]]:
        settings_field_keys = set()
        # noinspection PyUnresolvedReferences
        for k, v in cls.model_fields.items():
            try:
                if issubclass(v.annotation, CustomSettings):
                    field: Tuple[str, str, str]  # noqa: F842
                    settings_field_keys.update(
                        [(str(field[0]).upper(), field[1], field[2]) for field in v.annotation.get_fields(cls.__name__)]
                    )
                else:
                    settings_field_keys.add((str(k).upper(), v.title, parent_cls))
            except TypeError:
                settings_field_keys.add((str(k).upper(), v.title, parent_cls))

        return settings_field_keys

    def get_fields_by_title_group(self) -> Dict[str, Dict[str, Field]]:
        fields_by_title: Dict = {}
        for field_key, field in self.model_fields.items():
            if isclass(field.annotation) and issubclass(field.annotation, CustomSettings):
                settings_field: CustomSettings = getattr(self, field_key)
                fields_by_title.update(**settings_field.get_fields_by_title_group())
            else:
                field_title_key = to_snake(field.title)
                field_value = getattr(self, field_key)
                if not isinstance(field_value, bool) and not field_value:
                    field_value = field.default
                if field_title_key in fields_by_title.keys():
                    fields_by_title[field_title_key][field_key] = (field_value, field.description)
                else:
                    fields_by_title[field_title_key] = {field_key: (field_value, field.description)}

        return fields_by_title

    @staticmethod
    def convert_field_value_to_env(field_value: Any) -> str:
        if isinstance(field_value, int):
            env_field_value = str(field_value)
        elif isinstance(field_value, bool):
            env_field_value = str(field_value)
        elif isinstance(field_value, list):
            env_field_value = ",".join([val for val in field_value])
        elif isinstance(field_value, dict) and field_value:
            # use nested json.dumps() to escape double quotes in output string
            env_field_value = json.dumps(json.dumps(field_value))
        elif isinstance(field_value, Path):
            env_field_value = str(field_value)
        elif field_value:
            env_field_value = str(field_value)
        else:
            env_field_value = ""

        if (
            " " in env_field_value
            and not (env_field_value.startswith('"') or env_field_value.startswith("'"))
            and not (env_field_value.endswith('"') or env_field_value.endswith("'"))
        ):
            env_field_value = f'"{env_field_value}"'

        return env_field_value

    def write_settings_to_env_file(self, env_file_path: Path) -> None:
        with open(env_file_path, "w") as ef:
            for field_type, fields in self.get_fields_by_title_group().items():
                ef.write(f"\n# # # # # {field_type.replace('_', ' ').upper()} # # # # #\n\n")

                for field_key, (field_value, field_description) in fields.items():
                    if field_description:
                        ef.write(f"# {field_description}\n")
                    ef.write(f"{str(field_key).upper()}={self.convert_field_value_to_env(field_value)}\n")

    def replace_field_values_with_default(self):
        for field_key, field in self.model_fields.items():
            setattr(self, field_key, field.default)


class PlatformSettings(CustomSettings):
    # yahoo
    yahoo_consumer_key: Optional[str] = Field(None, title=__qualname__)
    yahoo_consumer_secret: Optional[str] = Field(None, title=__qualname__)
    yahoo_access_token_json: Optional[Dict[str, Any]] = Field(None, title=__qualname__)
    yahoo_game_id: Optional[Union[str, int]] = Field(
        "nfl",
        title=__qualname__,
        description=(
            "YAHOO LEAGUES ONLY: game_id can be either `nfl`, in which case Yahoo defaults to using the current "
            "season, or it can be a specific Yahoo game id for a specific season, such as 331 (2014 NFL season), 380 "
            "(2018 NFL season), or 390 (2019 nfl season)"
        ),
    )
    yahoo_initial_faab_budget: Optional[int] = Field(
        100,
        title=__qualname__,
        description="YAHOO LEAGUES ONLY: default FAAB since the initial/starting FAAB is not exposed in the API",
    )

    # espn
    espn_username: Optional[str] = Field(None, title=__qualname__)
    espn_password: Optional[str] = Field(None, title=__qualname__)
    espn_chrome_user_profile_path: Optional[Path] = Field(None, title=__qualname__)

    @computed_field
    @property
    def espn_chrome_user_data_dir(self) -> str:
        return str(self.espn_chrome_user_profile_path.parent)

    @computed_field
    @property
    def espn_chrome_user_profile(self) -> str:
        return self.espn_chrome_user_profile_path.name

    espn_cookie_swid: Optional[str] = Field(None, title=__qualname__)
    espn_cookie_espn_s2: Optional[str] = Field(None, title=__qualname__)

    # cbs
    cbs_username: Optional[str] = Field(None, title=__qualname__)
    cbs_password: Optional[str] = Field(None, title=__qualname__)
    cbs_auth_token: Optional[str] = Field(None, title=__qualname__)


class ReportSettings(CustomSettings):
    league_standings_bool: bool = Field(True, title=__qualname__)
    league_playoff_probs_bool: bool = Field(True, title=__qualname__)
    league_median_standings_bool: bool = Field(True, title=__qualname__)
    league_power_rankings_bool: bool = Field(True, title=__qualname__)
    league_z_score_rankings_bool: bool = Field(True, title=__qualname__)
    league_score_rankings_bool: bool = Field(True, title=__qualname__)
    league_coaching_efficiency_rankings_bool: bool = Field(True, title=__qualname__)
    league_luck_rankings_bool: bool = Field(True, title=__qualname__)
    league_optimal_score_rankings_bool: bool = Field(True, title=__qualname__)
    league_bad_boy_rankings_bool: bool = Field(True, title=__qualname__)
    league_beef_rankings_bool: bool = Field(True, title=__qualname__)
    league_high_roller_rankings_bool: bool = Field(True, title=__qualname__)
    league_weekly_top_scorers_bool: bool = Field(True, title=__qualname__)
    league_weekly_low_scorers_bool: bool = Field(True, title=__qualname__)
    league_weekly_highest_ce_bool: bool = Field(True, title=__qualname__)
    league_time_series_charts_bool: bool = Field(True, title=__qualname__)
    team_points_by_position_charts_bool: bool = Field(True, title=__qualname__)
    team_bad_boy_stats_bool: bool = Field(True, title=__qualname__)
    team_beef_stats_bool: bool = Field(True, title=__qualname__)
    team_high_roller_stats_bool: bool = Field(True, title=__qualname__)
    team_boom_or_bust_bool: bool = Field(True, title=__qualname__)

    font: str = Field("helvetica", title=__qualname__, description="set font for report (defaults to Helvetica)")
    supported_fonts_list: List[str] = Field(
        ["helvetica", "times", "symbola", "opensansemoji", "sketchcollege", "leaguegothic"],
        title=__qualname__,
        description="supported fonts (comma-delimited list with no spaces between items)",
    )
    font_size: int = Field(
        12,
        ge=10,
        le=14,
        title=__qualname__,
        description="set base font size so report element fonts resize dynamically (min: 10, max: 14)",
    )
    image_quality: int = Field(
        75,
        le=100,
        title=__qualname__,
        description=(
            "specify player headshot image quality in percent (default: 75%), where higher quality (up to 100%) "
            "results in a larger file size for the PDF report"
        ),
    )
    max_data_chars: int = Field(
        20,
        title=__qualname__,
        description="specify max number of characters to display for any given data cell in the report tables",
    )


class IntegrationSettings(CustomSettings):
    reupload_file_path: Optional[Path] = Field(
        "resources/files/example_report.pdf",
        title=__qualname__,
        description="file to reupload to third-party integrations",
    )

    # google drive
    google_drive_upload_bool: bool = Field(
        False,
        title=__qualname__,
        description=(
            "change GOOGLE_DRIVE_UPLOAD_BOOL to True/False to turn on/off uploading of the report to Google Drive"
        ),
    )
    google_drive_client_id: Optional[str] = Field(None, title=__qualname__)
    google_drive_client_secret: Optional[str] = Field(None, title=__qualname__)
    google_drive_auth_token_json: Optional[Dict[str, Any]] = Field(None, title=__qualname__)
    google_drive_default_folder: str = Field("Fantasy_Football", title=__qualname__)
    google_drive_folder: Optional[str] = Field(None, title=__qualname__)

    # slack
    slack_post_bool: bool = Field(
        False,
        title=__qualname__,
        description="change SLACK_POST_BOOL to True/False to turn on/off posting of the report to Slack",
    )
    slack_post_or_file: str = Field(
        "file",
        title=__qualname__,
        description=(
            "options for SLACK_POST_OR_FILE: post (if you wish to post a link to the report), file (if you wish to "
            "post the report PDF)"
        ),
    )
    slack_auth_token: Optional[str] = Field(None, title=__qualname__)
    slack_channel: Optional[str] = Field(None, title=__qualname__)
    slack_channel_notify_bool: bool = Field(False, title=__qualname__)

    # groupme
    groupme_post_bool: bool = Field(
        False,
        title=__qualname__,
        description="change GROUPME_POST_BOOL to True/False to turn on/off posting of the report to GroupMe",
    )
    groupme_post_or_file: str = Field(
        "file",
        title=__qualname__,
        description=(
            "options for GROUPME_POST_OR_FILE: post (if you wish to post a link to the report), file (if you wish to "
            "post the report PDF)"
        ),
    )
    groupme_bot_or_user: str = Field(
        "bot",
        title=__qualname__,
        description=(
            "options for GROUPME_BOT_OR_USER: bot (if you wish to post as a bot account), user (if you with to post as "
            "your user account)"
        ),
    )
    groupme_access_token: Optional[str] = Field(None, title=__qualname__)
    groupme_bot_id: Optional[str] = Field(None, title=__qualname__)
    groupme_group: Optional[str] = Field(None, title=__qualname__)

    # discord
    discord_post_bool: bool = Field(
        False,
        title=__qualname__,
        description="change DISCORD_POST_BOOL to True/False to turn on/off posting of the report to Discord",
    )
    discord_post_or_file: str = Field(
        "file",
        title=__qualname__,
        description=(
            "options for DISCORD_POST_OR_FILE: post (if you wish to post a link to the report), file (if you wish to "
            "post the report PDF)"
        ),
    )
    discord_webhook_id: Optional[str] = Field(None, title=__qualname__)
    discord_channel_notify_bool: bool = Field(False, title=__qualname__)


class AppSettings(CustomSettings):
    model_config = SettingsConfigDict(
        # env_file=".env",
        # env_file_encoding="utf-8",
        validate_default=False,
        extra="ignore",  # allow, forbid, or ignore
    )

    log_level: str = Field(
        "info", title=__qualname__, description="logger output level: notset, debug, info, warning, error, critical"
    )
    check_for_updates: bool = Field(
        True,
        title=__qualname__,
        description=(
            "automatically check GitHub for app updates and prompt user to update if local installation is out of date"
        ),
    )
    data_dir_path: Path = Field(
        Path("output/data"),
        title=__qualname__,
        description="output directory can be set to store your saved data wherever you want",
    )
    output_dir_path: Path = Field(
        Path("output/reports"),
        title=__qualname__,
        description="output directory can be set to store your generated reports wherever you want",
    )

    platform: Optional[str] = Field(
        None,
        validate_default=False,
        title=__qualname__,
        description="fantasy football platform for which you are running the report",
    )
    supported_platforms_list: List[str] = Field(
        ["yahoo", "espn", "sleeper", "fleaflicker", "cbs"],
        validate_default=False,
        title=__qualname__,
        description="supported fantasy football platforms (comma-delimited list with no spaces between items)",
    )
    league_id: Optional[str] = Field(
        None,
        title=__qualname__,
        description=(
            "example Yahoo public league archive for reference: https://archive.fantasysports.yahoo.com/nfl/2014/729259"
        ),
    )
    season: Optional[int] = Field(None, title=__qualname__)
    nfl_season_length: int = Field(18, title=__qualname__)
    current_nfl_week: Optional[int] = Field(None, title=__qualname__)
    week_for_report: Union[int, str, None] = Field(
        "default",
        title=__qualname__,
        description='value can be "default" or an integer between 1 and 18 defining the chosen week',
    )
    num_playoff_simulations: int = Field(
        10000,
        title=__qualname__,
        description=(
            "select how many Monte Carlo simulations are used for playoff predictions, keeping in mind that while more "
            "simulations improves the quality of the playoff predictions, it also makes this step of the report "
            "generation take longer to complete"
        ),
    )
    num_playoff_slots: int = Field(
        6, title=__qualname__, description="FLEAFLICKER: default if number of playoff slots cannot be scraped"
    )
    num_playoff_slots_per_division: int = Field(
        1,
        title=__qualname__,
        description="number of top ranked teams that make the playoffs from each division (for leagues with divisions)",
    )
    num_regular_season_weeks: int = Field(
        14,
        title=__qualname__,
        description="SLEEPER/FLEAFLICKER: default if number of regular season weeks cannot be scraped/retrieved",
    )
    coaching_efficiency_disqualified_teams_list: List[str] = Field(
        [],
        title=__qualname__,
        description=(
            "multiple teams can be manually disqualified from coaching efficiency eligibility (comma-delimited list "
            "with no spaces between items and surrounded by quotes), for example: "
            'COACHING_EFFICIENCY_DISQUALIFIED_TEAMS_LIST="Team One,Team Two"'
        ),
    )

    platform_settings: PlatformSettings = PlatformSettings()
    report_settings: ReportSettings = ReportSettings()
    integration_settings: IntegrationSettings = IntegrationSettings()


def get_app_settings_from_env_file(env_file_path: Path) -> AppSettings:
    env_fields = AppSettings.get_fields()

    # set local .env file (check for existence and access, stop app if it does not exist or cannot access)
    if env_file_path.is_file():
        if os.access(env_file_path, mode=os.R_OK):
            env_vars_from_file = set(dotenv_values(env_file_path).keys())
            missing_env_vars = set([field[0] for field in env_fields]).difference(env_vars_from_file)

            if missing_env_vars:
                logger.error(
                    f"Your local \".env\" file is missing the following variables:\n\n"
                    f"{', '.join(missing_env_vars)}\n\n"
                    f"Please update your \".env\" file and try again."
                )
                sys.exit(1)
            else:
                logger.debug('All required local ".env" file variables present.')

            logger.debug('The ".env" file is available. Running Fantasy Football Metrics Weekly Report app...')

            return AppSettings(_env_file=env_file_path, _env_file_encoding="utf-8")
        else:
            logger.error('Unable to access ".env" file. Please check that file permissions are properly set.')
            sys.exit(1)

    else:
        logger.debug('Local ".env" file not found.')
        create_env_file = input(
            f'{Fore.RED}Local ".env" file not found. {Fore.GREEN}Do you wish to create one? '
            f"{Fore.YELLOW}({Fore.GREEN}y{Fore.YELLOW}/{Fore.RED}n{Fore.YELLOW}) -> {Style.RESET_ALL}"
        ).lower()
        if create_env_file == "y":
            return create_env_file_from_settings(env_fields, env_file_path)
        elif create_env_file == "n":
            logger.error('Local ".env" not found. Please make sure that it exists in project root directory.')
            sys.exit(1)
        else:
            logger.warning('Please only select "y" or "n".')
            sleep(0.25)
            return get_app_settings_from_env_file(env_file_path)


def create_env_file_from_settings(
    env_fields: Set[Tuple[str, str, str]],
    env_file_path: Path,
    platform: str = None,
    league_id: str = None,
    season: int = None,
    current_week: int = None,
) -> AppSettings:
    logger.debug('Creating ".env" file from settings.')

    app_settings = AppSettings(_env_file=env_file_path, _env_file_encoding="utf-8")
    app_settings.replace_field_values_with_default()

    if not platform:
        supported_platforms_list = app_settings.supported_platforms_list
        platform = input(
            f"{Fore.GREEN}For which fantasy football platform are you generating a report? "
            f"({'/'.join(supported_platforms_list)}) -> {Style.RESET_ALL}"
        ).lower()
        if platform not in supported_platforms_list:
            logger.warning(
                f"Please only select one of the following platforms: "
                f"{', or '.join([', '.join(supported_platforms_list[:-1]), supported_platforms_list[-1]])}"
            )
            sleep(0.25)
            create_env_file_from_settings(env_fields, env_file_path)

        logger.debug(f'Retrieved fantasy football platform for ".env" file: {platform}')

    app_settings.platform = platform

    if not league_id:
        league_id = input(f"{Fore.GREEN}What is your league ID? -> {Style.RESET_ALL}")
        logger.debug(f'Retrieved fantasy football league ID for ".env" file: {league_id}')

    app_settings.league_id = league_id

    if not season:
        season = input(
            f"{Fore.GREEN}For which NFL season (starting year of season) are you generating reports? -> "
            f"{Style.RESET_ALL}"
        )
        try:
            if int(season) > datetime.today().year:
                logger.warning("This report cannot predict the future. Please only input a current or past NFL season.")
                sleep(0.25)
                return create_env_file_from_settings(env_fields, env_file_path, platform=platform, league_id=league_id)
            elif int(season) < 2019 and platform == "espn":
                logger.warning("ESPN leagues prior to 2019 are not supported. Please select a later NFL season.")
                sleep(0.25)
                return create_env_file_from_settings(env_fields, env_file_path, platform=platform, league_id=league_id)

        except ValueError:
            logger.warning("You must input a valid year in the format YYYY.")
            sleep(0.25)
            return create_env_file_from_settings(env_fields, env_file_path, platform=platform, league_id=league_id)

        logger.debug(f'Retrieved fantasy football season for ".env" file: {season}')

    app_settings.season = int(season)

    if not current_week:
        current_week = input(
            f"{Fore.GREEN}What is the current week of the NFL season? (week following the last complete week) -> "
            f"{Style.RESET_ALL}"
        )
        try:
            if int(current_week) < 0 or int(current_week) > app_settings.nfl_season_length:
                logger.warning(
                    f"Week {current_week} is not a valid NFL week. Please select a week from 1 to "
                    f"{app_settings.nfl_season_length}."
                )
                sleep(0.25)
                return create_env_file_from_settings(
                    env_fields, env_file_path, platform=platform, league_id=league_id, season=season
                )
        except ValueError:
            logger.warning("You must input a valid integer to represent the current NFL week.")
            sleep(0.25)
            return create_env_file_from_settings(
                env_fields, env_file_path, platform=platform, league_id=league_id, season=season
            )

        logger.debug(f'Retrieved current NFL week for ".env" file: {current_week}')

    app_settings.current_nfl_week = int(current_week)

    app_settings.write_settings_to_env_file(env_file_path)

    return app_settings


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    logger.info(local_settings)
