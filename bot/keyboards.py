from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.texts import CONFIRM_NO, CONFIRM_YES, HELP_TEXT


MAIN_MENU_BUTTON_START = "В НАЧАЛО"
MAIN_MENU_BUTTON_HELP = "ПОМОЩЬ"


main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=MAIN_MENU_BUTTON_START),
            KeyboardButton(text=MAIN_MENU_BUTTON_HELP),
        ]
    ],
    resize_keyboard=True,
)


def formats_keyboard(formats: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=item["name"], callback_data=f"fmt:{item['id']}")]
        for item in formats
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def limits_keyboard(limits: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=item["name"], callback_data=f"lim:{item['id']}")]
        for item in limits
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=CONFIRM_YES, callback_data="confirm:yes"),
            InlineKeyboardButton(text=CONFIRM_NO, callback_data="confirm:no"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def moderation_keyboard(request_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ approve", callback_data=f"mod:approve:{request_id}"
            ),
            InlineKeyboardButton(
                text="❌ reject", callback_data=f"mod:reject:{request_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def help_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=HELP_TEXT,
                url="https://t.me/Bravo_Poker",
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

