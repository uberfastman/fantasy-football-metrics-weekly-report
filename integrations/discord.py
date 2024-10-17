import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from colorama import Fore, Style
from discord_webhook import DiscordWebhook
from requests import Response

from integrations.base.integration import BaseIntegration
from utilities.logger import get_logger
from utilities.settings import settings

logger = get_logger(__name__, propagate=False)


class DiscordIntegration(BaseIntegration):

    def __init__(self, week):
        self.root_dir = Path(__file__).parent.parent
        self.base_url = f"https://discord.com/api/webhooks"
        super().__init__("discord", week)

    def _authenticate(self) -> None:

        if not settings.integration_settings.discord_webhook_id:
            settings.integration_settings.discord_webhook_id = input(
                f"{Fore.GREEN}What is your Discord webhook ID? -> {Style.RESET_ALL}"
            )
            settings.write_settings_to_env_file(self.root_dir / ".env")

        self.webhook_url = f"{self.base_url}/{settings.integration_settings.discord_webhook_id}"

        self.client = DiscordWebhook(url=self.webhook_url, allowed_mentions={"parse": ["everyone"]})

    def post_message(self, message: str) -> Dict:
        logger.debug(f"Posting message to Discord: \n{message}")

        if settings.integration_settings.discord_channel_notify_bool:
            message = f"@everyone\n\n{message}"

        self.client.set_content(message)

        return self.client.execute().json()

    def upload_file(self, file_path: Path) -> Response:
        logger.debug(f"Uploading file to Discord: \n{file_path}")

        message = self._upload_success_message(file_path.name)

        if settings.integration_settings.discord_channel_notify_bool:
            message = f"@everyone\n{message}"

        # discord_embed = DiscordEmbed()
        # discord_embed.set_title(file_path.name)
        # discord_embed.set_description(message)
        # self.client.add_embed(discord_embed)

        self.client.set_content(message)
        self.client.add_file(file_path.read_bytes(), file_path.name)

        return self.client.execute().json()


if __name__ == "__main__":
    reupload_file = Path(__file__).parent.parent / settings.integration_settings.reupload_file_path

    logger.info(f"Re-uploading {reupload_file.name} ({reupload_file}) to Discord...")

    discord_integration = DiscordIntegration(settings.week_for_report)

    # logger.info(f"{json.dumps(discord_integration.post_message('test message'), indent=2)}")
    logger.info(f"{json.dumps(discord_integration.upload_file(reupload_file), indent=2)}")
