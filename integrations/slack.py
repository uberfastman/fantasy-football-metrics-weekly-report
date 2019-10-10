__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"

import datetime
import json
import logging
import os
from configparser import ConfigParser

from slackclient import SlackClient

logger = logging.getLogger(__name__)


class SlackMessenger(object):
    def __init__(self, config):

        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.config = config

        auth_token = os.path.join(self.project_dir, self.config.get("Slack", "slack_auth_token"))

        with open(auth_token, "r") as token_file:
            # more information at https://api.slack.com/web#authentication
            slack_api_access_token = json.load(token_file).get("access_token")
            self.sc = SlackClient(slack_api_access_token)

    def api_test(self):
        return self.sc.api_call("api.test")

    def list_channels(self):
        """Required Slack app scopes: channels:read, groups:read, mpim:read, im:read
        """
        return self.sc.api_call("conversations.list")

    def test_post_to_slack(self, message):
        logger.info(self.sc.api_call("channels.info", channel="#apitest"))
        return self.sc.api_call(
            "chat.postMessage",
            channel="#apitest",
            text="<!here|here>:\n" + message,
            username="ff-report",
            # uncomment the icon_emoji parameter if you wish to choose an icon emoji to be your app icon, otherwise it
            # will default to whatever icon you have set for the app
            # icon_emoji=":football:"
        )

    def test_file_upload_to_slack(self, upload_file):
        logger.info(self.sc.api_call("channels.info", channel="#apitest"))
        with open(upload_file, "rb") as uf:
            file_to_upload = uf.read()
            response = self.sc.api_call(
                "files.upload",
                channels="#apitest",
                username="ff-report",
                icon_emoji=":football:",
                filename=upload_file,
                filetype="pdf",
                file=file_to_upload
            )
        if "ok" not in response or not response["ok"]:
            # error
            logger.error("fileUpload failed %s", response["error"])
        return response

    def post_to_selected_slack_channel(self, message):
        return self.sc.api_call(
            "chat.postMessage",
            channel="#" + self.config.get("Slack", "slack_channel"),
            text="<!here|here>\n" + message,
            username="ff-report",
            # icon_emoji=":football:"
        )

    def upload_file_to_selected_slack_channel(self, upload_file):

        report_file_info = upload_file.split(os.sep)
        file_name = report_file_info[-1]
        file_type = file_name.split(".")[-1]
        league_name = report_file_info[-2]
        message = "\nFantasy Football Report for %s\nGenerated %s\n" % (league_name,
                                                                        "{:%Y-%b-%d %H:%M:%S}".format(
                                                                            datetime.datetime.now()))

        upload_file = os.path.join(self.project_dir, upload_file)
        with open(upload_file, "rb") as uf:
            # post message with no additional content to trigger @here
            self.post_to_selected_slack_channel("")

            file_to_upload = uf.read()
            response = self.sc.api_call(
                "files.upload",
                channels="#" + self.config.get("Slack", "slack_channel"),
                filename=file_name,
                filetype=file_type,
                file=file_to_upload,
                title=file_name,
                initial_comment=message
            )
        if "ok" not in response or not response["ok"]:
            # error
            logger.error("fileUpload failed %s", response["error"])
        return response


if __name__ == '__main__':
    local_config = ConfigParser()
    local_config.read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"))
    repost_file = local_config.get("Slack", "repost_file")

    post_to_slack = SlackMessenger(local_config)
    print(post_to_slack.upload_file_to_selected_slack_channel(repost_file))
