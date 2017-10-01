from slack_messenger import SlackMessenger


if __name__ == '__main__':

    slack_messenger = SlackMessenger()
    # print(slack_messenger.test_post_on_hg_slack("testing..."))
    print(slack_messenger.upload_file_to_hg_fantasy_football_channel("reports/Things-Won't-Change(363515)/Things-Won't-Change(363515)_week-1_report.pdf"))
