import os
from typing import List


# Telegram bot token. Set your real token here or via BOT_TOKEN env var.
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8440785815:AAGiy20RkUsJxqdVtqo4Wzpv7QJQLivcwyc")

# List of Telegram user IDs who are bot admins.
ADMIN_IDS: List[int] = [
    # 123456789,
]

# Deposit/contact link used in broadcast messages.
DEPOSIT_LINK: str = "https://t.me/Bravo_Poker"

# Path to SQLite database file.
DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "bot.db"))

# Interval in seconds for the scheduled deletion worker.
SCHEDULE_INTERVAL_SECONDS: int = 30

