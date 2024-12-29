import json
from pathlib import Path
from typing import Dict

from colorama import Fore, Style
from discord_webhook import DiscordWebhook
from requests import Response

from ffmwr.integrations.base.integration import BaseIntegration
from ffmwr.utilities.logger import get_logger
from ffmwr.utilities.settings import AppSettings, get_app_settings_from_env_file

logger = get_logger(__name__, propagate=False)


class DiscordIntegration(BaseIntegration):
    def __init__(self, settings: AppSettings, root_directory: Path, week: int):
        self.base_url = "https://discord.com/api/webhooks"
        super().__init__(settings, root_directory, "discord", week)

    def _authenticate(self) -> None:
        if not self.settings.integration_settings.discord_webhook_id:
            self.settings.integration_settings.discord_webhook_id = input(
                f"{Fore.GREEN}What is your Discord webhook ID? -> {Style.RESET_ALL}"
            )
            self.settings.write_settings_to_env_file(self.root_dir / ".env")

        self.webhook_url = f"{self.base_url}/{self.settings.integration_settings.discord_webhook_id}"

        self.client = DiscordWebhook(url=self.webhook_url, allowed_mentions={"parse": ["everyone"]})

    def post_message(self, message: str) -> Dict:
        logger.debug(f"Posting message to Discord: \n{message}")

        if self.settings.integration_settings.discord_channel_notify_bool:
            message = f"@everyone\n\n{message}"

        self.client.set_content(message)

        return self.client.execute().json()

    def upload_file(self, file_path: Path) -> Response:
        logger.debug(f"Uploading file to Discord: \n{file_path}")

        message = self._upload_success_message(file_path.name)

        if self.settings.integration_settings.discord_channel_notify_bool:
            message = f"@everyone\n{message}"

        # discord_embed = DiscordEmbed()
        # discord_embed.set_title(file_path.name)
        # discord_embed.set_description(message)
        # self.client.add_embed(discord_embed)

        self.client.set_content(message)
        self.client.add_file(file_path.read_bytes(), file_path.name)

        return self.client.execute().json()


if __name__ == "__main__":
    local_root_directory = Path(__file__).parent.parent.parent

    local_settings: AppSettings = get_app_settings_from_env_file(local_root_directory / ".env")

    reupload_file = local_root_directory / local_settings.integration_settings.reupload_file_path

    logger.info(f"Re-uploading {reupload_file.name} ({reupload_file}) to Discord...")

    discord_integration = DiscordIntegration(local_settings, local_root_directory, local_settings.week_for_report)

    # logger.info(f"{json.dumps(discord_integration.post_message('test message'), indent=2)}")
    logger.info(f"{json.dumps(discord_integration.upload_file(reupload_file), indent=2)}")
