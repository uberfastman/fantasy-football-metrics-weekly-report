# Written by: Wren J. Rudolph
# Code snippets taken from: http://stackoverflow.com/questions/24419188/automating-pydrive-verification-process

import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


class GoogleDriveUploader(object):
    def __init__(self, filename):
        self.filename = filename

        self.gauth = GoogleAuth()

        # Try to load saved client credentials
        self.gauth.LoadCredentialsFile("./authentication/mycreds.txt")
        if self.gauth.credentials is None:
            # Authenticate if they're not there
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            # Refresh them if expired
            self.gauth.Refresh()
        else:
            # Initialize the saved creds
            self.gauth.Authorize()
        # Save the current credentials to a file
        self.gauth.SaveCredentialsFile("./authentication/mycreds.txt")

    def upload_file(self):

        # Create GoogleDrive instance with authenticated GoogleAuth instance.
        drive = GoogleDrive(self.gauth)

        # Create GoogleDriveFile instance.
        upload_file = drive.CreateFile({'title': self.filename.split("/")[-1], 'mimeType': 'application/pdf'})

        upload_file.SetContentFile(self.filename)

        # Upload the file.
        upload_file.Upload()

        upload_file.InsertPermission(
            {
                'type': 'anyone',
                'role': 'reader',
                'withLink': True
            }
        )

        return "\nFantasy Football Report\nGenerated %s\n*%s*\n\n_Google Drive Link:_\n%s" % (
        "{:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()), upload_file['title'], upload_file["alternateLink"])
