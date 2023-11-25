__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

import datetime
import json
import logging
import os
from asyncio import Future
from pathlib import Path
from typing import Union

from slack.errors import SlackApiError
from slack.web.base_client import SlackResponse
from slack.web.client import WebClient

from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)

# Suppress verbose slack debug logging
logging.getLogger("slack.web.slack_response").setLevel(level=logging.INFO)
logging.getLogger("slack.web.base_client").setLevel(level=logging.INFO)


class SlackMessenger(object):
    def __init__(self):
        logger.debug("Initializing Slack messenger.")

        self.project_dir: Path = Path(__file__).parent.parent

        logger.debug("Authenticating with Slack.")

        auth_token = self.project_dir / settings.integration_settings.slack_auth_token_local_path

        with open(auth_token, "r") as token_file:
            # more information at https://api.slack.com/web#authentication
            slack_api_access_token = json.load(token_file).get("access_token")
            # self.sc = SlackClient(slack_api_access_token)
            self.sc = WebClient(token=slack_api_access_token)

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

    def test_post_to_slack(self, message: str):
        logger.debug("Testing message posting to Slack.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id("apitest")))

            self.sc.chat_postMessage(
                channel=self.get_channel_id("apitest"),
                text="<!here|here>:\n" + message,
                username="ff-report",
                # uncomment the icon_emoji parameter if you wish to choose an icon emoji to be your app icon, otherwise
                # it will default to whatever icon you have set for the app
                # icon_emoji=":football:"
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def test_post_to_private_slack(self, message: str):
        logger.debug("Testing message posting to private Slack channels.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id("apitest-private")))

            self.sc.chat_postMessage(
                channel=self.get_channel_id("apitest-private"),
                text="<!here|here>:\n" + message,
                username="ff-report",
                # uncomment the icon_emoji parameter if you wish to choose an icon emoji to be your app icon, otherwise
                # it will default to whatever icon you have set for the app
                # icon_emoji=":football:"
            )
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def test_file_upload_to_slack(self, upload_file: Path) -> Union[Future, SlackResponse]:
        logger.debug("Testing file uploads to Slack.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id("apitest")))

            with open(upload_file, "rb") as uf:
                file_to_upload = uf.read()

                # noinspection PyTypeChecker
                response = self.sc.files_upload(
                    channels=self.get_channel_id("apitest"),
                    username="ff-report",
                    icon_emoji=":football:",
                    filename=upload_file,
                    filetype="pdf",
                    file=file_to_upload
                )
            return response
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def test_file_upload_to_private_slack(self, upload_file: Path) -> Union[Future, SlackResponse]:
        logger.debug("Testing file uploads to private Slack channels.")

        try:
            logger.info(self.sc.conversations_info(channel=self.get_channel_id("apitest-private")))

            with open(upload_file, "rb") as uf:
                file_to_upload = str(uf.read())

                response = self.sc.files_upload(
                    channels=self.get_channel_id("apitest-private"),
                    username="ff-report",
                    icon_emoji=":football:",
                    filename=upload_file,
                    filetype="pdf",
                    file=file_to_upload
                )
            return response
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")

    def post_to_selected_slack_channel(self, message: str) -> Union[Future, SlackResponse]:
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

    def upload_file_to_selected_slack_channel(self, upload_file: str) -> Union[Future, SlackResponse]:
        logger.debug(f"Uploading file to Slack: \n{upload_file}")

        try:
            report_file_info = upload_file.split(os.sep)
            file_name = report_file_info[-1]
            file_type = file_name.split(".")[-1]
            league_name = report_file_info[-2]
            message = (
                f"\nFantasy Football Report for {league_name}\nGenerated {datetime.datetime.now():%Y-%b-%d %H:%M:%S}\n"
            )

            upload_file = self.project_dir / upload_file
            with open(upload_file, "rb") as uf:

                if settings.integration_settings.slack_channel_notify_bool:
                    # post message with no additional content to trigger @here
                    self.post_to_selected_slack_channel("")

                file_to_upload = uf.read()
                # noinspection PyTypeChecker
                response = self.sc.files_upload(
                    channels=self.get_channel_id(settings.integration_settings.slack_channel),
                    filename=file_name,
                    filetype=file_type,
                    file=file_to_upload,
                    title=file_name,
                    initial_comment=message
                )
            return response
        except SlackApiError as e:
            logger.error(f"Slack client error: {e}")


if __name__ == "__main__":
    repost_file = Path(__file__).parent.parent / settings.integration_settings.slack_repost_file_local_path

    post_to_slack = SlackMessenger()

    # general slack integration testing
    logger.info(f"{json.dumps(post_to_slack.api_test().data, indent=2)}")
    # logger.info(f"{json.dumps(post_to_slack.list_channels().data, indent=2)}")
    # logger.info(f"{json.dumps(post_to_slack.list_channels().get('channels'), indent=2)}")

    # public channel integration testing
    # logger.info(f"{json.dumps(post_to_slack.test_post_to_slack('test'), indent=2)}")
    # logger.info(f"{json.dumps(post_to_slack.test_file_upload_to_slack(repost_file).data, indent=2)}")

    # private channel integration testing
    # logger.info(f"{json.dumps(post_to_slack.test_post_to_private_slack('test'), indent=2)}")
    # logger.info(f"{json.dumps(post_to_slack.test_file_upload_to_private_slack(repost_file).data, indent=2)}")

    # selected channel integration testing
    # logger.info(f"{json.dumps(post_to_slack.post_to_selected_slack_channel('test').data, indent=2)}")
    # logger.info(f"{json.dumps(post_to_slack.upload_file_to_selected_slack_channel(repost_file).data, indent=2)}")
