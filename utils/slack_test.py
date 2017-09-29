from slack_messenger import SlackMessenger


if __name__ == '__main__':

    slack_messenger = SlackMessenger()
    print(slack_messenger.test_on_hg_slack("testing..."))
