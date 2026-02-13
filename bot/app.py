import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot import db
from bot.config import BOT_TOKEN
from bot.handlers import admin, moderation, user
from bot.services.scheduler import start_scheduled_deletion_worker


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        logging.error("BOT_TOKEN is not set. Please set it in config.py or via BOT_TOKEN env var.")
        return

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(moderation.router)

    # Init database
    await db.init_db()

    # Start scheduled deletion worker
    start_scheduled_deletion_worker(bot)

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

