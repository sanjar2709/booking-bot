from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bookings import services as booking_services
from apps.bookings.models import Booking, BookingStatus
from core import settings
from core.formatting import day_label, money
from core.i18n import t

from . import services
from .filters import IsAdmin
from .notify import booking_fields

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AdminCb(CallbackData, prefix='adm'):
    action: str  # menu, day, stats, cancel
    value: str = ''


def menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    today = booking_services.now().date()
    builder = InlineKeyboardBuilder()
    tomorrow = today + timedelta(days=1)
    builder.button(text=t('btn_admin_today', lang), callback_data=AdminCb(action='day', value=today.isoformat()))
    builder.button(text=t('btn_admin_tomorrow', lang), callback_data=AdminCb(action='day', value=tomorrow.isoformat()))
    builder.button(text=t('btn_admin_stats', lang), callback_data=AdminCb(action='stats'))
    builder.adjust(2, 1)
    return builder.as_markup()


def day_screen(day: date, bookings: list[Booking], lang: str) -> tuple[str, InlineKeyboardMarkup]:
    builder = InlineKeyboardBuilder()
    if not bookings:
        text = t('admin_day_empty', lang, day=day_label(day, lang))
    else:
        lines = [t('admin_booking_line', lang, **booking_fields(b, lang)) for b in bookings]
        text = t('admin_day', lang, day=day_label(day, lang), count=len(bookings)) + '\n\n' + '\n\n'.join(lines)
        for b in bookings:
            fields = booking_fields(b, lang)
            text_on_button = f'❌ {fields["time"]} {fields["client"]}'
            builder.button(text=text_on_button, callback_data=AdminCb(action='cancel', value=str(b.id)))
    builder.adjust(1)
    builder.button(text=t('btn_back', lang), callback_data=AdminCb(action='menu'))
    return text, builder.as_markup()


@router.message(Command('admin'))
async def admin_menu(message: Message, lang: str):
    await message.answer(t('admin_menu', lang), reply_markup=menu_keyboard(lang))


@router.callback_query(AdminCb.filter(F.action == 'menu'))
async def back_to_menu(callback: CallbackQuery, lang: str):
    await callback.message.edit_text(t('admin_menu', lang), reply_markup=menu_keyboard(lang))
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == 'day'))
async def show_day(callback: CallbackQuery, callback_data: AdminCb, db: AsyncSession, lang: str):
    day = date.fromisoformat(callback_data.value)
    text, keyboard = day_screen(day, await services.bookings_on(db, day), lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AdminCb.filter(F.action == 'cancel'))
async def cancel_booking(callback: CallbackQuery, callback_data: AdminCb, db: AsyncSession, lang: str):
    booking = await db.get(Booking, int(callback_data.value))
    if booking is None or booking.status != BookingStatus.CONFIRMED:
        await callback.answer(t('booking_not_found', lang), show_alert=True)
        return
    await booking_services.cancel_booking(db, booking, by_admin=True)

    client_lang = booking.user.language
    fields = booking_fields(booking, client_lang)
    await callback.bot.send_message(
        booking.user_id,
        t('cancelled_by_admin', client_lang, day=fields['day'], time=fields['time'], phone=settings.BUSINESS_PHONE),
    )
    await callback.answer(t('admin_cancelled', lang, id=booking.id), show_alert=True)

    day = booking_services.local_date(booking.starts_at)
    text, keyboard = day_screen(day, await services.bookings_on(db, day), lang)
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(AdminCb.filter(F.action == 'stats'))
async def show_stats(callback: CallbackQuery, db: AsyncSession, lang: str):
    data = await services.stats(db)
    text = t(
        'admin_stats',
        lang,
        total=data['total'],
        cancelled=data['cancelled'],
        revenue=money(data['revenue'], lang),
        clients=data['clients'],
        top_service=data['top_service'].title(lang) if data['top_service'] else '—',
    )
    builder = InlineKeyboardBuilder()
    builder.button(text=t('btn_back', lang), callback_data=AdminCb(action='menu'))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()
