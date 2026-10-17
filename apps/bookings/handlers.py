from datetime import date, datetime, time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from apps.admin.notify import notify_admins
from apps.catalog.models import Service, Specialist
from apps.users.keyboards import main_menu
from apps.users.models import User
from core.formatting import day_label, money
from core.i18n import all_languages, t

from . import services
from .keyboards import (
    DayCb,
    NavCb,
    ServiceCb,
    SpecialistCb,
    TimeCb,
    confirm_keyboard,
    days_keyboard,
    phone_keyboard,
    services_keyboard,
    specialists_keyboard,
    times_keyboard,
)
from .states import BookingForm

router = Router()


async def load_choice(db: AsyncSession, state: FSMContext) -> tuple[Service | None, Specialist | None, date | None]:
    """What the user picked so far, read back from the conversation state."""
    data = await state.get_data()
    service = await db.get(Service, data['service_id']) if 'service_id' in data else None
    specialist = await db.get(Specialist, data['specialist_id']) if 'specialist_id' in data else None
    day = date.fromisoformat(data['day']) if 'day' in data else None
    return service, specialist, day


# Each step has a "show" function, so "Back" can jump to any of them

async def show_services(message: Message, db: AsyncSession, state: FSMContext, lang: str, edit=False):
    items = await services.active_services(db)
    if not items:
        await message.answer(t('no_services', lang))
        return
    await state.set_state(BookingForm.service)
    send = message.edit_text if edit else message.answer
    await send(t('choose_service', lang), reply_markup=services_keyboard(items, lang))


async def show_specialists(message: Message, db: AsyncSession, state: FSMContext, lang: str):
    service, _, _ = await load_choice(db, state)
    items = await services.specialists_for(db, service.id)
    await state.set_state(BookingForm.specialist)
    text = t('choose_specialist', lang, service=service.title(lang))
    await message.edit_text(text, reply_markup=specialists_keyboard(items, lang))


async def show_days(message: Message, db: AsyncSession, state: FSMContext, lang: str):
    service, specialist, _ = await load_choice(db, state)
    days = await services.days_with_slots(db, specialist, service)
    await state.set_state(BookingForm.day)
    text = t('choose_day', lang, service=service.title(lang), specialist=specialist.full_name)
    if not days:
        text += '\n\n' + t('no_days', lang)
    await message.edit_text(text, reply_markup=days_keyboard(days, lang))


async def show_times(message: Message, db: AsyncSession, state: FSMContext, lang: str, prefix=''):
    service, specialist, day = await load_choice(db, state)
    slots = await services.free_slots(db, specialist, service, day)
    await state.set_state(BookingForm.time)
    text = t(
        'choose_time', lang, service=service.title(lang), specialist=specialist.full_name, day=day_label(day, lang)
    )
    if not slots:
        text += '\n\n' + t('no_times', lang)
    await message.edit_text(prefix + text, reply_markup=times_keyboard(slots, lang))


async def show_confirm(message: Message, db: AsyncSession, state: FSMContext, lang: str, edit=True):
    service, specialist, day = await load_choice(db, state)
    data = await state.get_data()
    await state.set_state(BookingForm.confirm)
    text = t(
        'confirm_booking',
        lang,
        service=service.title(lang),
        specialist=specialist.full_name,
        day=day_label(day, lang),
        time=data['time'],
        duration=service.duration_minutes,
        price=money(service.price, lang),
    )
    send = message.edit_text if edit else message.answer
    await send(text, reply_markup=confirm_keyboard(lang))


# Steps

@router.message(F.text.in_(all_languages('btn_book')))
async def start_booking(message: Message, db: AsyncSession, state: FSMContext, lang: str):
    await state.clear()
    await show_services(message, db, state, lang)


@router.callback_query(BookingForm.service, ServiceCb.filter())
async def pick_service(
    callback: CallbackQuery, callback_data: ServiceCb, db: AsyncSession, state: FSMContext, lang: str
):
    await state.update_data(service_id=callback_data.id)
    await show_specialists(callback.message, db, state, lang)
    await callback.answer()


@router.callback_query(BookingForm.specialist, SpecialistCb.filter())
async def pick_specialist(
    callback: CallbackQuery, callback_data: SpecialistCb, db: AsyncSession, state: FSMContext, lang: str
):
    await state.update_data(specialist_id=callback_data.id)
    await show_days(callback.message, db, state, lang)
    await callback.answer()


@router.callback_query(BookingForm.day, DayCb.filter())
async def pick_day(callback: CallbackQuery, callback_data: DayCb, db: AsyncSession, state: FSMContext, lang: str):
    await state.update_data(day=callback_data.value)
    await show_times(callback.message, db, state, lang)
    await callback.answer()


@router.callback_query(BookingForm.time, TimeCb.filter())
async def pick_time(
    callback: CallbackQuery, callback_data: TimeCb, db: AsyncSession, state: FSMContext, user: User, lang: str
):
    await state.update_data(time=f'{callback_data.value[:2]}:{callback_data.value[2:]}')
    await callback.answer()
    if not user.phone:
        await state.set_state(BookingForm.phone)
        await callback.message.delete()
        await callback.message.answer(t('ask_phone', lang), reply_markup=phone_keyboard(lang))
        return
    await show_confirm(callback.message, db, state, lang)


@router.message(BookingForm.phone, F.contact)
async def got_phone(message: Message, db: AsyncSession, state: FSMContext, user: User, lang: str):
    # Only accept the user's own contact, not someone else's forwarded card
    if message.contact.user_id != user.id:
        await message.answer(t('ask_phone', lang), reply_markup=phone_keyboard(lang))
        return
    user.phone = message.contact.phone_number
    await db.commit()
    await message.answer(t('phone_saved', lang), reply_markup=main_menu(lang))
    await show_confirm(message, db, state, lang, edit=False)


@router.message(BookingForm.phone)
async def phone_needed(message: Message, lang: str):
    await message.answer(t('ask_phone', lang), reply_markup=phone_keyboard(lang))


@router.callback_query(BookingForm.confirm, NavCb.filter(F.to == 'confirm'))
async def confirm(callback: CallbackQuery, db: AsyncSession, state: FSMContext, user: User, lang: str):
    service, specialist, day = await load_choice(db, state)
    hour, minute = map(int, (await state.get_data())['time'].split(':'))
    starts_at = datetime.combine(day, time(hour, minute), services.TZ)

    try:
        booking = await services.create_booking(db, user, specialist, service, starts_at)
    except services.SlotTakenError:
        await show_times(callback.message, db, state, lang, prefix=t('slot_taken', lang) + '\n\n')
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(t(
        'booked',
        lang,
        service=service.title(lang),
        specialist=specialist.full_name,
        day=day_label(day, lang),
        time=f'{booking.starts_at.astimezone(services.TZ):%H:%M}',
    ))
    await callback.answer()
    await notify_admins(callback.bot, db, 'admin_new_booking', booking)


# Navigation

@router.callback_query(NavCb.filter(F.to == 'cancel'))
async def cancel(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await callback.message.edit_text(t('booking_cancelled_by_user', lang))
    await callback.answer()


# What has to be chosen already to open each screen
REQUIRED = {
    'services': (),
    'specialists': ('service_id',),
    'days': ('service_id', 'specialist_id'),
    'times': ('service_id', 'specialist_id', 'day'),
}


@router.callback_query(NavCb.filter())
async def go_back(callback: CallbackQuery, callback_data: NavCb, db: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    if callback_data.to not in REQUIRED or any(key not in data for key in REQUIRED[callback_data.to]):
        await callback.answer(t('session_expired', lang), show_alert=True)
        return
    screens = {
        'services': lambda: show_services(callback.message, db, state, lang, edit=True),
        'specialists': lambda: show_specialists(callback.message, db, state, lang),
        'days': lambda: show_days(callback.message, db, state, lang),
        'times': lambda: show_times(callback.message, db, state, lang),
    }
    await screens[callback_data.to]()
    await callback.answer()


# Buttons from an old message after the conversation moved on or the bot restarted
@router.callback_query(F.data.regexp(r'^(svc|spc|day|tm|nav):'))
async def stale_button(callback: CallbackQuery, lang: str):
    await callback.answer(t('session_expired', lang), show_alert=True)
