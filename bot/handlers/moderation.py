import logging
import time

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hlink

from bot import db, texts
from bot.config import ADMIN_IDS, DEPOSIT_LINK
from bot.keyboards import main_menu_kb, moderation_keyboard


logger = logging.getLogger(__name__)

router = Router(name="moderation")
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def send_request_to_admins(bot, request_id: int) -> None:
    request = await db.get_request_by_id(request_id)
    if not request:
        return
    player = await db.get_player_by_internal_id(int(request["player_id"]))
    if not player:
        return
    fmt = await db.get_format_by_id(int(request["format_id"]))
    lim = await db.get_limit_by_id(int(request["limit_id"]))
    if not fmt or not lim:
        return

    nick_safe = texts.html_safe(player.get("nick") or "")
    fmt_safe = texts.html_safe(fmt["name"])
    lim_safe = texts.html_safe(lim["name"])

    if player.get("username"):
        link = f"https://t.me/{player['username']}"
    else:
        link = hlink("профиль", f"tg://user?id={player['tg_id']}")

    text = texts.REQUEST_TO_ADMIN_TEMPLATE.format(
        nick=nick_safe,
        format=fmt_safe,
        limit=lim_safe,
        link=link,
    )

    kb = moderation_keyboard(request_id)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to send moderation request to admin %s: %s", admin_id, e)


@router.callback_query(F.data.startswith("mod:"))
async def on_moderation_action(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет прав для этого действия.", show_alert=True)
        return

    data = callback.data or ""
    try:
        _, action, request_id_str = data.split(":", maxsplit=2)
        request_id = int(request_id_str)
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    request = await db.get_request_by_id(request_id)
    if not request:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    player = await db.get_player_by_internal_id(int(request["player_id"]))
    fmt = await db.get_format_by_id(int(request["format_id"]))
    lim = await db.get_limit_by_id(int(request["limit_id"]))
    if not player or not fmt or not lim:
        await callback.answer("Ошибка данных заявки.", show_alert=True)
        await db.delete_request(request_id)
        return

    nick_safe = texts.html_safe(player.get("nick") or "")
    fmt_safe = texts.html_safe(fmt["name"])
    lim_safe = texts.html_safe(lim["name"])

    if action == "approve":
        logger.info("Approving request_id=%s, format_id=%s, limit_id=%s", request_id, request["format_id"], request["limit_id"])
        segment = await db.get_segment_by_pair(int(request["format_id"]), int(request["limit_id"]))
        if not segment:
            logger.warning("Segment not found for format_id=%s, limit_id=%s", request["format_id"], request["limit_id"])
            await callback.message.answer(
                "Сегмент для этого формата и лимита не найден. Создайте его через /segment.",
                reply_markup=main_menu_kb,
            )
            await callback.answer()
            await db.delete_request(request_id)
            return

        segment_id = int(segment["id"])
        logger.info("Found segment_id=%s, getting players...", segment_id)
        players = await db.get_players_for_segment(segment_id, exclude_player_id=int(player["internal_id"]))
        logger.info("Found %d players in segment %s (excluding creator internal_id=%s)", len(players), segment_id, player["internal_id"])

        if not players:
            logger.warning("No players found in segment %s (excluding creator)", segment_id)
            await callback.answer("В этом сегменте нет других игроков для рассылки.", show_alert=True)
            await db.delete_request(request_id)
            return

        text = texts.BROADCAST_TEMPLATE.format(
            nick=nick_safe,
            format=fmt_safe,
            limit=lim_safe,
            deposit_link=DEPOSIT_LINK,
        )

        delete_at = int(time.time()) + 6 * 60 * 60
        sent_count = 0
        bot = callback.bot
        for p in players:
            try:
                logger.info("Sending broadcast to tg_id=%s (internal_id=%s)", p.get("tg_id"), p.get("internal_id"))
                msg = await bot.send_message(p["tg_id"], text)
                await db.schedule_deletion(msg.chat.id, msg.message_id, delete_at)
                sent_count += 1
            except Exception as e:  # noqa: BLE001
                logger.exception("Failed to send broadcast to %s: %s", p.get("tg_id"), e)

        logger.info("Broadcast completed: sent %d/%d messages", sent_count, len(players))
        await db.delete_request(request_id)
        await callback.answer("Заявка одобрена.")

    elif action == "reject":
        delete_at = int(time.time()) + 60 * 60
        bot = callback.bot
        try:
            msg = await bot.send_message(player["tg_id"], texts.REJECT_PLAYER_TEXT)
            await db.schedule_deletion(msg.chat.id, msg.message_id, delete_at)
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to send rejection to %s: %s", player.get("tg_id"), e)

        await db.delete_request(request_id)
        await callback.answer("Заявка отклонена.")

    else:
        await callback.answer("Неизвестное действие.", show_alert=True)

