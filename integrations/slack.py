__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import datetime
import json
import logging
from asyncio import Future
from pathlib import Path
from typing import Union

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.base_client import SlackResponse

from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)

# Suppress verbose slack debug logging
logging.getLogger("slack.web.slack_response").setLevel(level=logging.INFO)
logging.getLogger("slack.web.base_client").setLevel(level=logging.INFO)


class SlackIntegration(object):

    def __init__(self):
        logger.debug("Initializing Slack integration.")

        self.project_dir: Path = Path(__file__).parent.parent

        logger.debug("Authenticating with Slack.")

        self.sc = WebClient(token=settings.integration_settings.slack_auth_token)

    def api_test(self):
        logger.debug("Testing Slack API.")
        try:
            return self.sc.api_test()
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def list_channels(self) -> Union[Future, SlackResponse]:
        """Required Slack app scopes: channels:read, groups:read, mpim:read, im:read
        """
        logger.debug("Listing Slack channels.")
        try:
            return self.sc.conversations_list(types="public_channel,private_channel")
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def get_channel_id(self, channel_name: str) -> str:
        for channel in self.list_channels().get("channels"):
            if channel.get("name") == channel_name:
                return channel.get("id")

    def test_post_to_slack_channel(self, message: str, channel_name: str):
        logger.debug("Testing message posting to Slack.")

        try:
            # logger.info(self.sc.conversations_info(channel=self.get_channel_id("dev-test")))

            return self.sc.chat_postMessage(
                channel=self.get_channel_id(channel_name),
                text="<!here>:\n" + message,
                username="ff-report",
                # uncomment the icon_emoji parameter if you wish to choose an icon emoji to be your app icon, otherwise
                # it will default to whatever icon you have set for the app
                # icon_emoji=":football:"
            ).data
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def test_post_to_private_slack_channel(self, message: str, channel_name: str):
        logger.debug("Testing message posting to private Slack channels.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id("dev-test")))

            self.sc.chat_postMessage(
                channel=self.get_channel_id(channel_name),
                text="<!here>:\n" + message,
                username="ff-report",
                # uncomment the icon_emoji parameter if you wish to choose an icon emoji to be your app icon, otherwise
                # it will default to whatever icon you have set for the app
                # icon_emoji=":football:"
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def test_file_upload_to_slack_channel(self, upload_file: Path, channel_name: str) -> Union[Future, SlackResponse]:
        logger.debug("Testing file uploads to Slack.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id("dev-test")))

            return self.sc.files_upload_v2(
                channel=self.get_channel_id(channel_name),
                username="ff-report",
                icon_emoji=":football:",
                filename=upload_file.name,
                file=str(upload_file)
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def test_file_upload_to_private_slack_channel(self, upload_file: Path, channel_name: str) -> Union[Future, SlackResponse]:
        logger.debug("Testing file uploads to private Slack channels.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id(channel_name)))

            return self.sc.files_upload_v2(
                channel=self.get_channel_id(channel_name),
                username="ff-report",
                icon_emoji=":football:",
                filename=upload_file.name,
                file=str(upload_file)
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def post_to_configured_slack_channel(self, message: str) -> Union[Future, SlackResponse]:
        logger.debug(f"Posting message to Slack: \n{message}")

        try:
            return self.sc.chat_postMessage(
                channel=self.get_channel_id(settings.integration_settings.slack_channel),
                text="<!here|here>\n" + message,
                username="ff-report",
                # icon_emoji=":football:"
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def upload_file_to_configured_slack_channel(self, upload_file: Path) -> Union[Future, SlackResponse]:
        logger.debug(f"Uploading file to Slack: \n{upload_file}")

        try:
            message = (
                f"\nFantasy Football Report for {upload_file.name}\nGenerated {datetime.datetime.now():%Y-%b-%d %H:%M:%S}\n"
            )

            upload_file: Path = self.project_dir / upload_file
            with open(upload_file, "rb") as uf:

                if settings.integration_settings.slack_channel_notify_bool:
                    # post message with no additional content to trigger @here
                    self.post_to_configured_slack_channel("")

                response = self.sc.files_upload_v2(
                    channel=self.get_channel_id(settings.integration_settings.slack_channel),
                    filename=upload_file.name,
                    file=uf.read(),
                    initial_comment=message
                )

            return response
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")


if __name__ == "__main__":

    test_channel = "dev-test"
    repost_file = Path(__file__).parent.parent / settings.integration_settings.slack_repost_file_path

    slack_integration = SlackIntegration()

    # general slack integration testing
    logger.info(f"{json.dumps(slack_integration.api_test().data, indent=2)}")
    logger.info(f"{json.dumps(slack_integration.list_channels().data, indent=2)}")
    logger.info(f"{json.dumps(slack_integration.list_channels().get('channels'), indent=2)}")

    # public channel integration testing
    logger.info(f"{json.dumps(slack_integration.test_post_to_slack_channel('test message', test_channel), indent=2)}")
    logger.info(f"{json.dumps(slack_integration.test_file_upload_to_slack_channel(repost_file, test_channel).data, indent=2)}")

    # private channel integration testing
    logger.info(f"{json.dumps(slack_integration.test_post_to_private_slack_channel('test message', test_channel), indent=2)}")
    logger.info(f"{json.dumps(slack_integration.test_file_upload_to_private_slack_channel(repost_file, test_channel).data, indent=2)}")

    # selected channel integration testing
    logger.info(f"{json.dumps(slack_integration.post_to_configured_slack_channel('test').data, indent=2)}")
    logger.info(f"{json.dumps(slack_integration.upload_file_to_configured_slack_channel(repost_file).data, indent=2)}")
