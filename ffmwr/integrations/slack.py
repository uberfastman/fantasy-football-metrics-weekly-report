__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import json
import logging
from asyncio import Future
from pathlib import Path
from typing import Union

from colorama import Fore, Style
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.base_client import SlackResponse

from ffmwr.integrations.base.integration import BaseIntegration
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file

logger = get_logger(__name__, propagate=False)

# Suppress verbose slack debug logging
logging.getLogger("slack.web.slack_response").setLevel(level=logging.INFO)
logging.getLogger("slack.web.base_client").setLevel(level=logging.INFO)


class SlackIntegration(BaseIntegration):
    def __init__(self, settings: AppSettings, root_directory: Path, week: int):
        super().__init__(settings, root_directory, "slack", week)

    def _authenticate(self) -> None:
        if not self.settings.integration_settings.slack_auth_token:
            self.settings.integration_settings.slack_auth_token = input(
                f"{Fore.GREEN}What is your Slack authentication token? -> {Style.RESET_ALL}"
            )
            self.settings.write_settings_to_env_file(self.root_dir / ".env")

        self.client = WebClient(token=self.settings.integration_settings.slack_auth_token)

    def api_test(self):
        logger.debug("Testing Slack API.")
        try:
            return self.client.api_test()
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def _list_channels(self) -> Union[Future, SlackResponse]:
        """Required Slack app scopes: channels:read, groups:read, mpim:read, im:read"""
        logger.debug("Listing Slack channels.")
        try:
            return self.client.conversations_list(types="public_channel,private_channel")
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def _get_channel_id(self, channel_name: str) -> str:
        for channel in self._list_channels().get("channels"):
            if channel.get("name") == channel_name:
                return channel.get("id")
        raise ValueError(f"Channel {channel_name} not found.")

    def post_message(self, message: str) -> Union[Future, SlackResponse]:
        logger.debug(f"Posting message to Slack: \n{message}")

        try:
            return self.client.chat_postMessage(
                channel=self._get_channel_id(self.settings.integration_settings.slack_channel),
                text=f"<!here>:\n{message}",
                username="ff-report",
                # uncomment the icon_emoji parameter if you wish to choose an icon emoji to be your app icon, otherwise
                # it will default to whatever icon you have set for the app
                # icon_emoji=":football:"
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def upload_file(self, file_path: Path) -> Union[Future, SlackResponse]:
        logger.debug(f"Uploading file to Slack: \n{file_path}")

        try:
            message = self._upload_success_message(file_path.name)

            if self.settings.integration_settings.slack_channel_notify_bool:
                message = f"<!here>\n{message}"

            file_for_upload: Path = self.root_dir / file_path
            with open(file_for_upload, "rb") as uf:
                response = self.client.files_upload_v2(
                    channel=self._get_channel_id(self.settings.integration_settings.slack_channel),
                    filename=file_for_upload.name,
                    file=uf.read(),
                    initial_comment=message,
                )

            return response
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    reupload_file = local_root_directory / local_settings.integration_settings.reupload_file_path

    logger.info(f"Re-uploading {reupload_file.name} ({reupload_file}) to Slack...")

    slack_integration = SlackIntegration(local_settings, local_root_directory, local_settings.week_for_report)

    # logger.info(f"\n{json.dumps(slack_integration.api_test().data, indent=2)}")
    # logger.info(f"{json.dumps(slack_integration.post_message('test message').data, indent=2)}")
    logger.info(f"{json.dumps(slack_integration.upload_file(reupload_file).data, indent=2)}")
