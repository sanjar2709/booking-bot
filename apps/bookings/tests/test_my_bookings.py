from datetime import timedelta

import pytest

from apps.bookings.keyboards import CancelCb, NavCb
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import now
from apps.common.tests.bot import buttons, texts
from apps.common.tests.factories import add_booking, at, next_working_day, register
from core.db import SessionLocal

pytestmark = pytest.mark.usefixtures('catalog')


async def status_of(booking_id: int) -> BookingStatus:
    async with SessionLocal() as db:
        return (await db.get(Booking, booking_id)).status


def alerts(tg) -> list[str]:
    return [r.text for r in tg.session.requests if getattr(r, 'show_alert', False)]


async def test_empty(tg):
    user = await register(tg, 1)

    replies = await tg.send(user, '🗂 My bookings')

    assert texts(replies) == ["You don't have any upcoming bookings. Press «📅 Book»."]


async def test_lists_only_upcoming_confirmed(tg):
    user = await register(tg, 1)
    day = next_working_day()
    await add_booking(user.id, at(day, 10))
    await add_booking(user.id, at(day, 12), status=BookingStatus.CANCELLED)
    await add_booking(user.id, now() - timedelta(days=1))

    replies = await tg.send(user, '🗂 My bookings')

    assert texts(replies)[0].count('📅') == 1
    assert len(buttons(replies[0])) == 1


async def test_cancel_with_confirmation(tg):
    user = await register(tg, 1)
    booking = await add_booking(user.id, at(next_working_day(), 10))

    replies = await tg.click(user, CancelCb(id=booking.id).pack())
    assert buttons(replies[0]) == ['Yes, cancel', 'No']

    replies = await tg.click(user, NavCb(to='my').pack())
    assert await status_of(booking.id) == BookingStatus.CONFIRMED

    replies = await tg.click(user, CancelCb(id=booking.id, confirmed=True).pack())
    assert texts(replies)[0].startswith('❌ Booking cancelled')
    assert await status_of(booking.id) == BookingStatus.CANCELLED


async def test_too_late_to_cancel(tg):
    user = await register(tg, 1)
    booking = await add_booking(user.id, now() + timedelta(minutes=90))

    await tg.click(user, CancelCb(id=booking.id, confirmed=True).pack())

    assert alerts(tg)[-1].startswith('Bookings can be cancelled at least 2 hours in advance')
    assert await status_of(booking.id) == BookingStatus.CONFIRMED


async def test_cannot_cancel_someone_elses_booking(tg):
    owner = await register(tg, 1)
    stranger = await register(tg, 2)
    booking = await add_booking(owner.id, at(next_working_day(), 10))

    await tg.click(stranger, CancelCb(id=booking.id, confirmed=True).pack())

    assert alerts(tg)[-1] == 'Booking not found or already cancelled.'
    assert await status_of(booking.id) == BookingStatus.CONFIRMED
