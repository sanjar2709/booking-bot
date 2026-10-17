import pytest

from apps.admin.handlers import AdminCb
from apps.bookings.keyboards import CancelCb, NavCb
from apps.bookings.models import Booking, BookingStatus
from apps.common.tests.bot import buttons, texts
from apps.common.tests.factories import add_booking, at, next_working_day, register, walk_to_confirm
from core.db import SessionLocal

pytestmark = pytest.mark.usefixtures('catalog')

ADMIN_ID = 9001  # set in conftest


async def test_admin_only(tg):
    client = await register(tg, 1)

    assert await tg.send(client, '/admin') == []


async def test_menu(tg):
    admin = await register(tg, ADMIN_ID)

    replies = await tg.send(admin, '/admin')

    assert buttons(replies[0]) == ['📋 Today', '📆 Tomorrow', '📊 Stats']


async def test_day_schedule_shows_client_phone(tg):
    admin = await register(tg, ADMIN_ID)
    client = await register(tg, 1, name='Ali Valiyev', phone='+998901112233')
    day = next_working_day()
    await add_booking(client.id, at(day, 10))

    replies = await tg.click(admin, AdminCb(action='day', value=day.isoformat()).pack())

    assert 'Ali Valiyev (+998901112233)' in texts(replies)[0]
    assert buttons(replies[0]) == ['❌ 10:00 Ali Valiyev', '⬅️ Back']


async def test_admin_cancel_notifies_client_in_their_language(tg):
    admin = await register(tg, ADMIN_ID)
    client = await register(tg, 1, lang='uz')
    booking = await add_booking(client.id, at(next_working_day(), 10))

    replies = await tg.click(admin, AdminCb(action='cancel', value=str(booking.id)).pack())

    to_client = [r for r in replies if r.chat_id == client.id]
    assert to_client[0].text.startswith('❌ Afsuski')
    async with SessionLocal() as db:
        assert (await db.get(Booking, booking.id)).status == BookingStatus.CANCELLED


async def test_admin_is_told_about_new_and_cancelled_bookings(tg):
    await register(tg, ADMIN_ID)
    client = await register(tg, 1, name='Ali Valiyev', phone='+998901112233')
    await walk_to_confirm(tg, client, next_working_day())

    replies = await tg.click(client, NavCb(to='confirm').pack())
    to_admin = [r for r in replies if r.chat_id == ADMIN_ID]
    assert to_admin[0].text.startswith('🆕 New booking')
    assert '+998901112233' in to_admin[0].text

    async with SessionLocal() as db:
        booking_id = (await db.get(Booking, 1)).id
    replies = await tg.click(client, CancelCb(id=booking_id, confirmed=True).pack())
    assert [r for r in replies if r.chat_id == ADMIN_ID][0].text.startswith('↩️ Client cancelled')


async def test_stats(tg):
    admin = await register(tg, ADMIN_ID)
    client = await register(tg, 1)
    day = next_working_day()
    await add_booking(client.id, at(day, 10))
    await add_booking(client.id, at(day, 12))
    await add_booking(client.id, at(day, 14), status=BookingStatus.CANCELLED)

    replies = await tg.click(admin, AdminCb(action='stats').pack())

    text = texts(replies)[0]
    assert 'Bookings: 3' in text
    assert 'Cancelled: 1' in text
    assert 'Revenue (not cancelled): 160 000 UZS' in text
    assert 'Most booked service: Haircut' in text
