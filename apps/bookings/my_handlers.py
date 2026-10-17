from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from apps.admin.notify import notify_admins
from apps.users.models import User
from core import settings
from core.formatting import day_label, local
from core.i18n import all_languages, t

from . import services
from .keyboards import CancelCb, NavCb, ask_cancel_keyboard, my_bookings_keyboard
from .models import Booking

router = Router()


def when(booking: Booking, lang: str) -> dict:
    starts = local(booking.starts_at)
    return {'day': day_label(starts.date(), lang), 'time': f'{starts:%H:%M}'}


async def bookings_screen(db: AsyncSession, user: User, lang: str) -> tuple[str, object]:
    bookings = await services.upcoming_bookings(db, user)
    if not bookings:
        return t('my_bookings_empty', lang), None
    lines = [
        t('booking_line', lang, service=b.service.title(lang), specialist=b.specialist.full_name, **when(b, lang))
        for b in bookings
    ]
    return t('my_bookings', lang) + '\n\n' + '\n\n'.join(lines), my_bookings_keyboard(bookings, lang)


@router.message(F.text.in_(all_languages('btn_my_bookings')))
async def my_bookings(message: Message, db: AsyncSession, user: User, lang: str):
    text, keyboard = await bookings_screen(db, user, lang)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(NavCb.filter(F.to == 'my'))
async def back_to_list(callback: CallbackQuery, db: AsyncSession, user: User, lang: str):
    text, keyboard = await bookings_screen(db, user, lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(CancelCb.filter())
async def cancel(callback: CallbackQuery, callback_data: CancelCb, db: AsyncSession, user: User, lang: str):
    booking = await services.get_own_booking(db, user, callback_data.id)
    if booking is None:
        await callback.answer(t('booking_not_found', lang), show_alert=True)
        return

    if not callback_data.confirmed:
        text = t('ask_cancel', lang, **when(booking, lang))
        await callback.message.edit_text(text, reply_markup=ask_cancel_keyboard(booking.id, lang))
        await callback.answer()
        return

    try:
        await services.cancel_booking(db, booking)
    except services.TooLateToCancelError:
        text = t('cancel_too_late', lang, hours=settings.CANCEL_DEADLINE_HOURS, phone=settings.BUSINESS_PHONE)
        await callback.answer(text, show_alert=True)
        return
    await callback.message.edit_text(t('cancelled', lang, **when(booking, lang)))
    await callback.answer()
    await notify_admins(callback.bot, db, 'admin_client_cancelled', booking)
