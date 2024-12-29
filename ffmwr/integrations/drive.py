__author__ = "Wren J. R. (uberfastman)"
__email__ = "uberfastman@uberfastman.dev"

# code snippets taken from: http://stackoverflow.com/questions/24419188/automating-pydrive-verification-process

import json
import logging
from pathlib import Path
from time import sleep
from typing import List, Union

from colorama import Fore, Style
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile

from ffmwr.integrations.base.integration import BaseIntegration
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file

logger = get_logger(__name__, propagate=False)

# Suppress verbose googleapiclient info/warning logging
logging.getLogger("googleapiclient").setLevel(level=logging.ERROR)
logging.getLogger("googleapiclient.discovery").setLevel(level=logging.ERROR)
logging.getLogger("googleapiclient.discovery_cache").setLevel(level=logging.ERROR)
logging.getLogger("googleapiclient.discovery_cache.file_cache").setLevel(level=logging.ERROR)


class GoogleDriveIntegration(BaseIntegration):
    def __init__(self, settings: AppSettings, root_directory: Path, week: int):
        super().__init__(settings, root_directory, "google_drive", week)

    def _authenticate(self) -> None:
        sleep(0.25)

        if not self.settings.integration_settings.google_drive_client_id:
            self.settings.integration_settings.google_drive_client_id = input(
                f"{Fore.GREEN}What is your Google Drive client ID? -> {Style.RESET_ALL}"
            )
            self.settings.write_settings_to_env_file(self.root_dir / ".env")

        if not self.settings.integration_settings.google_drive_client_secret:
            self.settings.integration_settings.google_drive_client_secret = input(
                f"{Fore.GREEN}What is your Google Drive client secret? -> {Style.RESET_ALL}"
            )
            self.settings.write_settings_to_env_file(self.root_dir / ".env")

        if self.settings.integration_settings.google_drive_auth_token_json:
            credentials = json.dumps(self.settings.integration_settings.google_drive_auth_token_json)
        else:
            credentials = None

        google_auth: GoogleAuth = GoogleAuth(
            settings={
                "client_config_backend": "settings",
                "client_config": {
                    "client_id": self.settings.integration_settings.google_drive_client_id,
                    "client_secret": self.settings.integration_settings.google_drive_client_secret,
                },
                "save_credentials": True,
                "save_credentials_backend": "dictionary",
                "save_credentials_dict": {
                    "creds": credentials,
                },
                "save_credentials_key": "creds",
                "get_refresh_token": True,
                "oauth_scope": ["https://www.googleapis.com/auth/drive"],
            }
        )

        google_auth.LoadCredentials(backend="dictionary")

        if google_auth.credentials is None:
            google_auth.LocalWebserverAuth()
        elif google_auth.access_token_expired:
            google_auth.Refresh()
        else:
            google_auth.Authorize()

        google_auth.SaveCredentials(backend="dictionary")
        self.settings.integration_settings.google_drive_auth_token_json = google_auth.credentials.to_json()
        self.settings.write_settings_to_env_file(self.root_dir / ".env")

        # Create GoogleDrive instance with authenticated GoogleAuth instance.
        self.client = GoogleDrive(google_auth)

    @staticmethod
    def _check_file_existence(file_name: str, file_list: List[GoogleDriveFile], parent_id: str) -> GoogleDriveFile:
        drive_file_name = file_name
        google_drive_file = None

        for drive_file in file_list:
            if drive_file["title"] == drive_file_name:
                for parent_folder in drive_file["parents"]:
                    if parent_folder["id"] == parent_id or parent_folder["isRoot"]:
                        google_drive_file = drive_file

        return google_drive_file

    def _make_root_folder(self, folder: GoogleDriveFile, folder_name: str) -> str:
        if not folder:
            new_root_folder = self.client.CreateFile(
                {
                    "title": folder_name,
                    "parents": [{"kind": "drive#fileLink", "isRoot": True, "id": "root"}],
                    "mimeType": "application/vnd.google-apps.folder",
                }
            )
            new_root_folder.Upload()
            root_folder_id = new_root_folder["id"]
        else:
            root_folder_id = folder["id"]

        return root_folder_id

    def _make_parent_folder(self, folder: GoogleDriveFile, folder_name: str, parent_folder_id: str) -> str:
        if not folder:
            new_parent_folder = self.client.CreateFile(
                {
                    "title": folder_name,
                    "parents": [{"kind": "drive#fileLink", "id": parent_folder_id}],
                    "mimeType": "application/vnd.google-apps.folder",
                }
            )
            new_parent_folder.Upload()
            parent_folder_id = new_parent_folder["id"]
        else:
            parent_folder_id = folder["id"]

        return parent_folder_id

    def upload_file(self, file_path: Union[str, Path], test: bool = False) -> str:
        logger.debug("Uploading file to Google Drive.")

        file_for_upload: Path = self.root_dir / file_path

        # Get lists of folders
        root_folders = self.client.ListFile(
            {"q": "'root' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"}
        ).GetList()

        google_drive_folder_path_default = self.settings.integration_settings.google_drive_default_folder
        google_drive_folder_path = Path(
            self.settings.integration_settings.google_drive_folder or google_drive_folder_path_default
        ).parts

        google_drive_root_folder_id = self._make_root_folder(
            self._check_file_existence(google_drive_folder_path[0], root_folders, "root"), google_drive_folder_path[0]
        )

        if not test:
            parent_folder_id = google_drive_root_folder_id
            parent_folder_content_folders = self.client.ListFile(
                {
                    "q": (
                        f"'{parent_folder_id}' in parents and "
                        f"mimeType='application/vnd.google-apps.folder' and "
                        f"trashed=false"
                    )
                }
            ).GetList()
            for folder in google_drive_folder_path[1:]:
                # create folder chain in Google Drive
                parent_folder_id = self._make_parent_folder(
                    self._check_file_existence(folder, parent_folder_content_folders, parent_folder_id),
                    folder,
                    parent_folder_id,
                )

                parent_folder_content_folders = self.client.ListFile(
                    {
                        "q": (
                            f"'{parent_folder_id}' in parents and "
                            f"mimeType='application/vnd.google-apps.folder' and "
                            f"trashed=false"
                        )
                    }
                ).GetList()

            # Check for season folder and create it if it does not exist
            season_folder_name = file_for_upload.parts[-3]

            season_folder_id = self._make_parent_folder(
                self._check_file_existence(season_folder_name, parent_folder_content_folders, parent_folder_id),
                season_folder_name,
                parent_folder_id,
            )
            season_folder_content_folders = self.client.ListFile(
                {
                    "q": (
                        f"'{season_folder_id}' in parents and "
                        f"mimeType='application/vnd.google-apps.folder' and "
                        f"trashed=false"
                    )
                }
            ).GetList()

            # Check for league folder and create it if it does not exist
            league_folder_name = file_for_upload.parts[-2].replace("-", "_")
            league_folder_id = self._make_parent_folder(
                self._check_file_existence(league_folder_name, season_folder_content_folders, season_folder_id),
                league_folder_name,
                season_folder_id,
            )
            league_folder_content_pdfs = self.client.ListFile(
                {"q": f"'{league_folder_id}' in parents and " f"mimeType='application/pdf' and " f"trashed=false"}
            ).GetList()

            # Check for league report and create it if it does not exist
            report_file_name = file_for_upload.parts[-1]
            report_file = self._check_file_existence(report_file_name, league_folder_content_pdfs, league_folder_id)
        else:
            all_pdfs = self.client.ListFile({"q": "mimeType='application/pdf' and trashed=false"}).GetList()

            report_file_name = file_for_upload.name
            report_file = self._check_file_existence(report_file_name, all_pdfs, "root")
            league_folder_id = "root"

        if report_file:
            report_file.Delete()

        upload_file = self.client.CreateFile(
            {
                "title": report_file_name,
                "mimeType": "application/pdf",
                "parents": [{"kind": "drive#fileLink", "id": league_folder_id}],
            }
        )
        upload_file.SetContentFile(file_for_upload)

        # Upload the file.
        upload_file.Upload()

        upload_file.InsertPermission({"type": "anyone", "role": "reader", "withLink": True})

        return self._upload_success_message(upload_file["title"], drive_link=upload_file["alternateLink"])


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    reupload_file = local_root_directory / local_settings.integration_settings.reupload_file_path

    logger.info(f"Re-uploading {reupload_file.name} ({reupload_file}) to Google Drive...")

    google_drive_integration = GoogleDriveIntegration(
        local_settings, local_root_directory, local_settings.week_for_report
    )

    upload_message = google_drive_integration.upload_file(reupload_file)
    logger.info(upload_message)
