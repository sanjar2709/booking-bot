from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.i18n import LANGUAGES, all_languages, t

from .keyboards import language_keyboard, main_menu
from .models import User

router = Router()


@router.message(CommandStart())
async def start(message: Message, user: User, lang: str | None, state: FSMContext):
    await state.clear()
    if not lang:
        # Nobody chose a language yet, so ask in all three
        text = '\n'.join(t('choose_language', code) for code in LANGUAGES)
        await message.answer(text, reply_markup=language_keyboard())
        return
    text = t('welcome', lang, name=user.full_name, business=settings.BUSINESS_NAME)
    await message.answer(text, reply_markup=main_menu(lang))


@router.message(F.text.in_(all_languages('btn_language')))
async def change_language(message: Message, lang: str):
    await message.answer(t('choose_language', lang), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith('lang:'))
async def set_language(callback: CallbackQuery, user: User, db: AsyncSession):
    code = callback.data.split(':')[1]
    if code not in LANGUAGES:
        await callback.answer()
        return
    is_first_time = user.language is None
    user.language = code
    await db.commit()

    await callback.message.edit_text(t('language_saved', code))
    if is_first_time:
        text = t('welcome', code, name=user.full_name, business=settings.BUSINESS_NAME)
    else:
        text = t('main_menu', code)
    await callback.message.answer(text, reply_markup=main_menu(code))
    await callback.answer()


@router.message(F.text.in_(all_languages('btn_contacts')))
async def contacts(message: Message, lang: str):
    await message.answer(
        t(
            'contacts',
            lang,
            business=settings.BUSINESS_NAME,
            address=settings.BUSINESS_ADDRESS,
            phone=settings.BUSINESS_PHONE,
            hours=settings.BUSINESS_HOURS,
        )
    )
