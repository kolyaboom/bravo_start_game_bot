import logging
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import db, texts
from bot.keyboards import (
    MAIN_MENU_BUTTON_HELP,
    MAIN_MENU_BUTTON_START,
    confirm_keyboard,
    formats_keyboard,
    help_inline_keyboard,
    limits_keyboard,
    main_menu_kb,
)
from bot.states import UserStates
from bot.handlers import moderation as moderation_module


logger = logging.getLogger(__name__)

router = Router(name="user")
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)


async def _is_banned(tg_id: int) -> bool:
    return await db.is_banned_by_tg_id(tg_id)


async def _ensure_not_banned(message: Message) -> bool:
    if await _is_banned(message.from_user.id):
        await message.answer(texts.BANNED_TEXT, reply_markup=main_menu_kb)
        return False
    return True


async def _ask_nick(message: Message, state: FSMContext) -> None:
    await state.set_state(UserStates.ASK_NICK)
    await message.answer(texts.ASK_NICK, reply_markup=main_menu_kb)


async def _ask_format(message: Message, state: FSMContext) -> None:
    formats = await db.get_all_formats()
    if not formats:
        await message.answer(texts.NO_FORMATS_TEXT, reply_markup=main_menu_kb)
        await state.clear()
        return
    kb = formats_keyboard(formats)
    await state.set_state(UserStates.CHOOSE_FORMAT)
    await message.answer(texts.QUESTION_FORMAT, reply_markup=kb)


async def _ask_limit(message: Message, state: FSMContext, format_id: int) -> None:
    limits = await db.get_limits_for_format(format_id)
    if not limits:
        await message.answer(texts.NO_LIMITS_TEXT, reply_markup=main_menu_kb)
        await state.clear()
        return
    kb = limits_keyboard(limits)
    await state.set_state(UserStates.CHOOSE_LIMIT)
    await message.answer(texts.QUESTION_LIMIT, reply_markup=kb)


async def _show_confirmation(
    message: Message, state: FSMContext, format_id: int, limit_id: int
) -> None:
    fmt = await db.get_format_by_id(format_id)
    lim = await db.get_limit_by_id(limit_id)
    if not fmt or not lim:
        await message.answer("Произошла ошибка при получении формата или лимита.", reply_markup=main_menu_kb)
        await state.clear()
        return
    fmt_name = texts.html_safe(fmt["name"])
    lim_name = texts.html_safe(lim["name"])
    text = texts.CONFIRM_TEMPLATE.format(format=fmt_name, limit=lim_name)
    await state.set_state(UserStates.CONFIRM)
    await message.answer(text, reply_markup=confirm_keyboard())


async def _get_or_create_player(message: Message) -> dict:
    user = message.from_user
    player = await db.get_or_create_player(user.id, user.username)
    # Keep username up to date
    if user.username and player.get("username") != user.username:
        await db.update_player_username(user.id, user.username)
    return player


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not await _ensure_not_banned(message):
        return

    player = await _get_or_create_player(message)

    if not player.get("nick"):
        await _ask_nick(message, state)
    else:
        await message.answer(texts.ALREADY_REGISTERED, reply_markup=main_menu_kb)
        await _ask_format(message, state)


@router.message(F.text == MAIN_MENU_BUTTON_START)
async def on_main_menu(message: Message, state: FSMContext) -> None:
    if not await _ensure_not_banned(message):
        return

    await state.clear()
    player = await _get_or_create_player(message)
    if not player.get("nick"):
        await _ask_nick(message, state)
    else:
        await _ask_format(message, state)


@router.message(F.text == MAIN_MENU_BUTTON_HELP)
async def on_help(message: Message, state: FSMContext) -> None:  # noqa: ARG001
    # Помощь доступна даже заблокированным игрокам?
    # Требование: бан запрещает любые действия, кроме получения сообщения "Вы заблокированы".
    # Поэтому, если игрок забанен, показываем только сообщение о бане.
    if await _is_banned(message.from_user.id):
        await message.answer(texts.BANNED_TEXT, reply_markup=main_menu_kb)
        return

    await message.answer(texts.HELP_TEXT, reply_markup=main_menu_kb)
    await message.answer(texts.HELP_TEXT, reply_markup=help_inline_keyboard())


@router.message(UserStates.ASK_NICK)
async def on_nick(message: Message, state: FSMContext) -> None:
    if not await _ensure_not_banned(message):
        await state.clear()
        return

    nick = message.text.strip()
    player = await _get_or_create_player(message)
    internal_id = player["internal_id"]
    await db.set_player_nick(internal_id, nick)

    await _ask_format(message, state)


@router.callback_query(F.data.startswith("fmt:"))
async def on_format_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    if await _is_banned(callback.from_user.id):
        await callback.message.answer(texts.BANNED_TEXT, reply_markup=main_menu_kb)
        await callback.answer()
        await state.clear()
        return

    data = callback.data or ""
    try:
        _, fmt_id_str = data.split(":", maxsplit=1)
        format_id = int(fmt_id_str)
    except ValueError:
        await callback.answer("Некорректный формат данных.", show_alert=True)
        return

    await state.update_data(format_id=format_id)
    await callback.answer()
    await _ask_limit(callback.message, state, format_id)


@router.callback_query(F.data.startswith("lim:"))
async def on_limit_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    if await _is_banned(callback.from_user.id):
        await callback.message.answer(texts.BANNED_TEXT, reply_markup=main_menu_kb)
        await callback.answer()
        await state.clear()
        return

    data = callback.data or ""
    try:
        _, lim_id_str = data.split(":", maxsplit=1)
        limit_id = int(lim_id_str)
    except ValueError:
        await callback.answer("Некорректный формат данных.", show_alert=True)
        return

    fsm_data = await state.get_data()
    format_id = fsm_data.get("format_id")
    if not format_id:
        await callback.message.answer("Не выбран формат. Начните сначала.", reply_markup=main_menu_kb)
        await state.clear()
        await callback.answer()
        return

    await state.update_data(limit_id=limit_id)
    await callback.answer()
    await _show_confirmation(callback.message, state, format_id, limit_id)


@router.callback_query(F.data == "confirm:no")
async def on_confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    if await _is_banned(callback.from_user.id):
        await callback.message.answer(texts.BANNED_TEXT, reply_markup=main_menu_kb)
        await callback.answer()
        await state.clear()
        return

    await state.clear()
    await callback.answer()
    await _ask_format(callback.message, state)


@router.callback_query(F.data == "confirm:yes")
async def on_confirm_yes(callback: CallbackQuery, state: FSMContext) -> None:
    if await _is_banned(callback.from_user.id):
        await callback.message.answer(texts.BANNED_TEXT, reply_markup=main_menu_kb)
        await callback.answer()
        await state.clear()
        return

    fsm_data = await state.get_data()
    format_id: Optional[int] = fsm_data.get("format_id")
    limit_id: Optional[int] = fsm_data.get("limit_id")
    if not format_id or not limit_id:
        await callback.message.answer("Не выбран формат или лимит. Начните сначала.", reply_markup=main_menu_kb)
        await state.clear()
        await callback.answer()
        return

    player = await db.get_or_create_player(
        callback.from_user.id,
        callback.from_user.username,
    )
    player_id = int(player["internal_id"])

    request_id = await db.create_request(player_id, format_id, limit_id)

    await moderation_module.send_request_to_admins(callback.bot, request_id)

    await callback.answer("Ваш запрос отправлен на модерацию.")
    await state.clear()
    await callback.message.answer("Ваша заявка отправлена на модерацию.", reply_markup=main_menu_kb)

