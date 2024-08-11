import logging
import logging.config
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

from .config import Conifg, LoggingConfig

# Load environment variables
if Conifg.ENV == "development":
    load_dotenv()
else:
    load_dotenv(dotenv_path=Path.home() / ".env")


# Define custom logging levels with emojis
DEBUG_EMOJI = "🐛🔍"
INFO_EMOJI = "ℹ️"
WARNING_EMOJI = "⚠️"
ERROR_EMOJI = "❌"
CRITICAL_EMOJI = "🚨"

DEFAULT_LOG_PATH = (
    Path("app.log")
    if Conifg.ENV == "development"
    else Path.home() / "termux-monitor.log"
)


class TelegramHandler(logging.Handler):
    def __init__(
        self, bot_token: Optional[str], chat_id: Optional[str], level=logging.NOTSET
    ):
        if not bot_token or not chat_id:
            raise ValueError("bot_token and chat_id must be set")
        super().__init__(level)
        self.bot_token = bot_token
        self.chat_id = chat_id

    def emit(self, record):
        func_name = getattr(record, "funcName", "")
        if func_name in ("<module>", ""):
            setattr(record, "funcName", record.module)
        log_entry = self.format(record)
        emoji_log_entry = self.prefix_message_with_emoji(record.levelname, log_entry)
        self.send_telegram_message(emoji_log_entry)

    def prefix_message_with_emoji(self, levelname, message):
        emoji = {
            "DEBUG": DEBUG_EMOJI,
            "INFO": INFO_EMOJI,
            "WARNING": WARNING_EMOJI,
            "ERROR": ERROR_EMOJI,
            "CRITICAL": CRITICAL_EMOJI,
        }.get(levelname, "")
        return f"{emoji} {message}"

    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "html",
            "disable_web_page_preview": True,
        }
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Failed to send log to Telegram: {e}")


class LoggerFactory:
    _LOG = None

    @staticmethod
    def __createlogger(name: str):
        """
        A private method that interacts with the python logging module.
        """

        # Define a basic logging configuration programmatically
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "telegram": {
                    "format": "<b>%(levelname)s</b>\n<em>🧩 %(name)s.%(funcName)s</em>\n\n<code>%(message)s</code>\n\n🕒 <code>%(asctime)s</code>"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "level": "DEBUG",
                    "formatter": "standard",
                    "filename": DEFAULT_LOG_PATH,
                },
                "telegram": {
                    "()": TelegramHandler,
                    "level": LoggingConfig.TELEGRAM_LOGGING_LEVEL,
                    "formatter": "telegram",
                    "bot_token": LoggingConfig.TELEGRAM_BOT_TOKEN,
                    "chat_id": LoggingConfig.TELEGRAM_CHAT_ID,
                },
            },
            "loggers": {
                "": {  # root logger
                    "level": "DEBUG",
                    "handlers": ["console", "file", "telegram"],
                },
                "urllib3": {  # Suppress urllib3 debug logs
                    "handlers": ["console"],
                    "level": "WARNING",
                },
            },
        }

        logging.config.dictConfig(logging_config)
        LoggerFactory._LOG = logging.getLogger(name)

        return LoggerFactory._LOG

    @staticmethod
    def get_logger(name: str):
        """
        A static method called by other modules to initialize logger in their own modules.

        Args:
            name (str): Name of the logger.
        """
        logger = LoggerFactory.__createlogger(name)
        return logger
