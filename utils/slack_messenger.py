# written by Wren J.R.
import datetime

from slackclient import SlackClient


class SlackMessenger(object):
    def __init__(self, config):
        self.config = config
        with open("./authentication/private.txt", "r") as auth_file:
            auth_data = auth_file.read().split("\n")

            slack_api_token = auth_data[2]
            token = slack_api_token  # found at https://api.slack.com/web#authentication
            self.sc = SlackClient(token)

    def api_test(self):
        return self.sc.api_call("api.test")

    def list_channels(self):
        return self.sc.api_call("channels.list")

    def test_post_to_slack(self, message):
        print(self.sc.api_call("channels.info", channel="C0A56L9A4"))
        return self.sc.api_call(
            "chat.postMessage", channel="#apitests", text="<!here|here>:\n" + message,
            username="fantasy_football_report_bot", icon_emoji=":football:"
        )

    def test_file_upload_to_slack(self, upload_file):
        print(self.sc.api_call("channels.info", channel="C0A56L9A4"))
        with open(upload_file, "r") as uf:
            file_to_upload = uf.read()
            response = self.sc.api_call(
                "files.upload",
                channels="#apitests",
                username="fantasy_football_report_bot",
                icon_emoji=":football:",
                filename="test_file.pdf",
                filetype="pdf",
                file=file_to_upload
            )
        if "ok" not in response or not response["ok"]:
            # error
            print("fileUpload failed %s", response["error"])
        return response

    def post_to_selected_slack_channel(self, message):
        return self.sc.api_call(
            "chat.postMessage", channel="#" + self.config.get("Slack_Settings", "slack_channel"),
            text="<!here|here>\n" + message, username="fantasy_football_report_bot", icon_emoji=":football:"
        )

    def upload_file_to_selected_slack_channel(self, upload_file):
        file_name = upload_file.split("/")[-1]
        file_type = file_name.split(".")[-1]
        league_name = file_name.split(".")[-2].split("_")[0]
        message = "\nFantasy Football Report for %s\nGenerated %s\n" % (league_name,
                                                                        "{:%Y-%b-%d %H:%M:%S}".format(
                                                                            datetime.datetime.now()))
        with open(upload_file, "rb") as uf:
            file_to_upload = uf.read()
            response = self.sc.api_call(
                "files.upload",
                channels="#" + self.config.get("Slack_Settings", "slack_channel"),
                filename=file_name,
                filetype=file_type,
                file=file_to_upload,
                title=file_name,
                initial_comment=message
            )
        if "ok" not in response or not response["ok"]:
            # error
            print("fileUpload failed %s", response["error"])
        return response
