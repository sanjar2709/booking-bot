from datetime import date, datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apps.bookings.models import Booking
from apps.catalog.models import Service, Specialist
from core.formatting import day_label, local, money
from core.i18n import t


class ServiceCb(CallbackData, prefix='svc'):
    id: int


class SpecialistCb(CallbackData, prefix='spc'):
    id: int


class DayCb(CallbackData, prefix='day'):
    value: str  # 2026-10-20


class TimeCb(CallbackData, prefix='tm'):
    value: str  # 1430, ':' is the separator inside callback data


class CancelCb(CallbackData, prefix='cnl'):
    id: int
    confirmed: bool = False


class NavCb(CallbackData, prefix='nav'):
    to: str  # services, specialists, days, times, confirm, cancel


def back_button(lang: str, to: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t('btn_back', lang), callback_data=NavCb(to=to).pack())


def services_keyboard(services: list[Service], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        text = f'{service.title(lang)} · {service.duration_minutes} {t("minutes", lang)} · {money(service.price, lang)}'
        builder.button(text=text, callback_data=ServiceCb(id=service.id))
    builder.adjust(1)
    return builder.as_markup()


def specialists_keyboard(specialists: list[Specialist], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for specialist in specialists:
        builder.button(text=f'👤 {specialist.full_name}', callback_data=SpecialistCb(id=specialist.id))
    builder.adjust(1)
    builder.row(back_button(lang, 'services'))
    return builder.as_markup()


def days_keyboard(days: list[date], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for day in days:
        builder.button(text=day_label(day, lang), callback_data=DayCb(value=day.isoformat()))
    builder.adjust(3)
    builder.row(back_button(lang, 'specialists'))
    return builder.as_markup()


def times_keyboard(slots: list[datetime], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=f'{slot:%H:%M}', callback_data=TimeCb(value=f'{slot:%H%M}'))
    builder.adjust(4)
    builder.row(back_button(lang, 'days'))
    return builder.as_markup()


def confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    confirm = InlineKeyboardButton(text=t('btn_confirm', lang), callback_data=NavCb(to='confirm').pack())
    cancel = InlineKeyboardButton(text=t('btn_cancel', lang), callback_data=NavCb(to='cancel').pack())
    return InlineKeyboardMarkup(inline_keyboard=[[confirm], [back_button(lang, 'times'), cancel]])


def phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t('btn_share_phone', lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def my_bookings_keyboard(bookings: list[Booking], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        starts = local(booking.starts_at)
        text = t('btn_cancel_booking', lang, day=day_label(starts.date(), lang), time=f'{starts:%H:%M}')
        builder.button(text=text, callback_data=CancelCb(id=booking.id))
    builder.adjust(1)
    return builder.as_markup()


def ask_cancel_keyboard(booking_id: int, lang: str) -> InlineKeyboardMarkup:
    confirmed = CancelCb(id=booking_id, confirmed=True).pack()
    yes = InlineKeyboardButton(text=t('btn_yes_cancel', lang), callback_data=confirmed)
    no = InlineKeyboardButton(text=t('btn_no', lang), callback_data=NavCb(to='my').pack())
    return InlineKeyboardMarkup(inline_keyboard=[[yes, no]])
