from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from core.i18n import LANGUAGES, t


def language_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f'lang:{code}')] for code, (title, _) in LANGUAGES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t('btn_book', lang))],
            [KeyboardButton(text=t('btn_my_bookings', lang)), KeyboardButton(text=t('btn_contacts', lang))],
            [KeyboardButton(text=t('btn_language', lang))],
        ],
        resize_keyboard=True,
    )
