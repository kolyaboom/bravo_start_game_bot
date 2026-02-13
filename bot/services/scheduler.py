import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from bot import db
from bot.config import SCHEDULE_INTERVAL_SECONDS


logger = logging.getLogger(__name__)


async def _scheduled_deletion_worker(bot: Bot) -> None:
    while True:
        now_ts = int(time.time())
        try:
            deletions = await db.get_due_scheduled_deletions(now_ts)
            if deletions:
                ids_to_delete = []
                for item in deletions:
                    chat_id = item["chat_id"]
                    message_id = item["message_id"]
                    try:
                        await bot.delete_message(chat_id, message_id)
                    except TelegramBadRequest:
                        # Message might already be deleted or not found
                        pass
                    except TelegramAPIError as e:
                        logger.exception(
                            "Failed to delete message %s in chat %s: %s",
                            message_id,
                            chat_id,
                            e,
                        )
                    ids_to_delete.append(item["id"])
                if ids_to_delete:
                    await db.delete_scheduled_deletions(ids_to_delete)
        except Exception as e:  # noqa: BLE001
            logger.exception("Error in scheduled deletion worker: %s", e)

        await asyncio.sleep(SCHEDULE_INTERVAL_SECONDS)


def start_scheduled_deletion_worker(bot: Bot) -> None:
    asyncio.create_task(_scheduled_deletion_worker(bot))

