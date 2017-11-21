import unittest

from slack_messenger import SlackMessenger
from upload_to_google_drive import GoogleDriveUploader


class TestServices(unittest.TestCase):
    @unittest.skip
    def test_slack_post(self):
        messenger = SlackMessenger()
        print(messenger.test_post_on_hg_slack("testing..."))

    @unittest.skip
    def test_slack_upload(self):
        messenger = SlackMessenger()
        print(messenger.upload_file_to_hg_fantasy_football_channel("reports/test_report.pdf", "apitests"))

    @unittest.skip
    def test_google_drive_upload(self):
        google_drive_uploader = GoogleDriveUploader("reports/test_report.pdf")
        upload_message = google_drive_uploader.upload_file(test_bool=True)
        print(upload_message)


if __name__ == "__main__":
    unittest.main()
