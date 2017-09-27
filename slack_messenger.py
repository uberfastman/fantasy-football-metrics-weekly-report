# Written by: Wren J. Rudolph

from __future__ import print_function
from slackclient import SlackClient


class SlackMessenger(object):
    def __init__(self):
        with open("./authentication/private.txt", "r") as auth_file:
            auth_data = auth_file.read().split("\n")

            slack_api_token = auth_data[2]
            token = slack_api_token  # found at https://api.slack.com/web#authentication
            self.sc = SlackClient(token)

    def api_test(self):
        return self.sc.api_call("api.test")

    def list_channels(self):
        return self.sc.api_call("channels.list")

    def test_on_hg_slack(self, message):
        print(self.sc.api_call("channels.info", channel="C0A56L9A4"))
        return self.sc.api_call(
            "chat.postMessage", channel="C0A56L9A4", text="<!here|here>:\n" + message,
            username="fantasy_football_report_bot", icon_emoji=":football:"
        )

    def post_to_hg_fantasy_football_channel(self, message):
        return self.sc.api_call(
            "chat.postMessage", channel="C02H4SGPC", text="<!here|here>\n" + message,
            username="fantasy_football_report_bot", icon_emoji=":football:"
        )
