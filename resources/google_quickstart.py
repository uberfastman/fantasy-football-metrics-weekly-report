import os
from pathlib import Path

# noinspection PyPackageRequirements
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

from utilities.logger import get_logger

logger = get_logger(__file__)

# If modifying these scopes, delete the file token.json.
# this scope allows the reading and writing of files to Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    """Shows basic usage of the Drive v3 API.
    Outputs the names and ids of the first 10 files the user has access to.
    """

    google_auth_dir = Path(__file__).parent.parent / "auth" / "google"
    if not Path(google_auth_dir).exists():
        os.makedirs(google_auth_dir)
    token_file_path = Path(google_auth_dir) / "token.json"

    store = file.Storage(token_file_path)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(Path(google_auth_dir) / "credentials.json", SCOPES)
        creds = tools.run_flow(flow, store)
    service = build("drive", "v3", http=creds.authorize(Http()))

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get("files", [])

    if not items:
        logger.info("No files found.")
    else:
        logger.info(f"\nFiles:\n" + "\n".join([f"{item['name']} ({item['id']})" for item in items]))


if __name__ == "__main__":
    main()
