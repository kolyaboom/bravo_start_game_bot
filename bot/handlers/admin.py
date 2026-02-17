import logging
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from bot import db, texts
from bot.config import ADMIN_IDS
from bot.keyboards import main_menu_kb


logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(F.chat.type == ChatType.PRIVATE)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _ensure_admin(message: Message) -> bool:
    if not _is_admin(message.from_user.id):
        await message.answer(texts.ADMIN_ONLY_TEXT, reply_markup=main_menu_kb)
        return False
    return True


async def _resolve_player(identifier: int, create_if_missing: bool = False) -> Optional[dict]:
    player = await db.get_player_by_internal_id(identifier)
    if player:
        return player
    player = await db.get_player_by_tg_id(identifier)
    if player:
        return player
    if create_if_missing:
        player = await db.get_or_create_player(identifier, None)
        return player
    return None


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    text = (
        "Доступные команды:\n"
        "/ban tg_id|internal_id\n"
        "/unban tg_id|internal_id\n"
        "/setnick tg_id|internal_id new_nick\n"
        "/addformat name\n"
        "/addlimit name\n"
        "/linklimit format_id limit_id\n"
        "/segment format_id limit_id\n"
        "/assign tg_id|internal_id segment_id\n"
        "/unassign tg_id|internal_id segment_id\n"
        "/user tg_id|internal_id\n"
        "/segments"
    )
    await message.answer(text, reply_markup=main_menu_kb)


@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        ident = int(parts[1])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    player = await _resolve_player(ident, create_if_missing=True)
    internal_id = int(player["internal_id"])
    await db.set_player_ban(internal_id, True)
    await message.answer(texts.BAN_OK, reply_markup=main_menu_kb)


@router.message(Command("unban"))
async def cmd_unban(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        ident = int(parts[1])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    player = await _resolve_player(ident, create_if_missing=False)
    if not player:
        await message.answer(texts.USER_NOT_FOUND_TEXT, reply_markup=main_menu_kb)
        return
    internal_id = int(player["internal_id"])
    await db.set_player_ban(internal_id, False)
    await message.answer(texts.UNBAN_OK, reply_markup=main_menu_kb)


@router.message(Command("setnick"))
async def cmd_setnick(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        ident = int(parts[1])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    new_nick = parts[2].strip()
    player = await _resolve_player(ident, create_if_missing=False)
    if not player:
        await message.answer(texts.USER_NOT_FOUND_TEXT, reply_markup=main_menu_kb)
        return
    internal_id = int(player["internal_id"])
    await db.set_player_nick(internal_id, new_nick)
    await message.answer(texts.SETNICK_OK, reply_markup=main_menu_kb)


@router.message(Command("addformat"))
async def cmd_addformat(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    name = parts[1].strip()
    fmt_id = await db.add_format(name)
    await message.answer(texts.FORMAT_ADDED_TEXT.format(id=fmt_id), reply_markup=main_menu_kb)


@router.message(Command("addlimit"))
async def cmd_addlimit(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    name = parts[1].strip()
    lim_id = await db.add_limit(name)
    await message.answer(texts.LIMIT_ADDED_TEXT.format(id=lim_id), reply_markup=main_menu_kb)


@router.message(Command("linklimit"))
async def cmd_linklimit(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        format_id = int(parts[1])
        limit_id = int(parts[2])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    await db.link_format_limit(format_id, limit_id)
    await message.answer(texts.LINK_ADDED_TEXT, reply_markup=main_menu_kb)


@router.message(Command("segment"))
async def cmd_segment(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        format_id = int(parts[1])
        limit_id = int(parts[2])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    segment_id = await db.get_or_create_segment(format_id, limit_id)
    await message.answer(
        texts.SEGMENT_CREATED_TEXT.format(
            id=segment_id, format_id=format_id, limit_id=limit_id
        ),
        reply_markup=main_menu_kb,
    )


@router.message(Command("assign"))
async def cmd_assign(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        ident = int(parts[1])
        segment_id = int(parts[2])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    player = await _resolve_player(ident, create_if_missing=False)
    if not player:
        await message.answer(texts.USER_NOT_FOUND_TEXT, reply_markup=main_menu_kb)
        return
    internal_id = int(player["internal_id"])
    await db.assign_segment(internal_id, segment_id)
    await message.answer(
        texts.ASSIGNED_TEXT.format(segment_id=segment_id),
        reply_markup=main_menu_kb,
    )


@router.message(Command("unassign"))
async def cmd_unassign(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        ident = int(parts[1])
        segment_id = int(parts[2])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    player = await _resolve_player(ident, create_if_missing=False)
    if not player:
        await message.answer(texts.USER_NOT_FOUND_TEXT, reply_markup=main_menu_kb)
        return
    internal_id = int(player["internal_id"])
    await db.unassign_segment(internal_id, segment_id)
    await message.answer(
        texts.UNASSIGNED_TEXT.format(segment_id=segment_id),
        reply_markup=main_menu_kb,
    )


@router.message(Command("user"))
async def cmd_user(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    try:
        ident = int(parts[1])
    except ValueError:
        await message.answer(texts.PARSING_ERROR, reply_markup=main_menu_kb)
        return
    player = await _resolve_player(ident, create_if_missing=False)
    if not player:
        await message.answer(texts.USER_NOT_FOUND_TEXT, reply_markup=main_menu_kb)
        return
    segments = await db.get_segments_for_player(int(player["internal_id"]))
    text = texts.USER_INFO_TEMPLATE.format(
        internal_id=player["internal_id"],
        tg_id=player["tg_id"],
        username=player.get("username") or "-",
        nick=player.get("nick") or "-",
        is_banned=player.get("is_banned", 0),
        segments=", ".join(str(s) for s in segments) if segments else "-",
    )
    await message.answer(text, reply_markup=main_menu_kb)


@router.message(Command("segments"))
async def cmd_segments(message: Message) -> None:
    if not await _ensure_admin(message):
        return
    segments = await db.get_all_segments_with_names()
    if not segments:
        await message.answer("Сегменты не настроены.", reply_markup=main_menu_kb)
        return
    lines = [texts.SEGMENTS_LIST_HEADER]
    for seg in segments:
        lines.append(
            texts.SEGMENT_ITEM_TEMPLATE.format(
                segment_id=seg["segment_id"],
                format_name=seg["format_name"],
                format_id=seg["format_id"],
                limit_name=seg["limit_name"],
                limit_id=seg["limit_id"],
            )
        )
    await message.answer("\n".join(lines), reply_markup=main_menu_kb)
