from datetime import timedelta

import pytest

from apps.bookings import services
from apps.bookings.models import BookingStatus
from apps.catalog.models import Service, Specialist
from apps.common.tests.factories import add_booking, at, next_working_day
from apps.users.models import User
from core.db import SessionLocal

pytestmark = pytest.mark.usefixtures('catalog')


async def slots_for(day, specialist_id=1, service_id=1):
    async with SessionLocal() as db:
        specialist, service = await db.get(Specialist, specialist_id), await db.get(Service, service_id)
        return [f'{s.astimezone(services.TZ):%H:%M}' for s in await services.free_slots(db, specialist, service, day)]


async def make_user():
    async with SessionLocal() as db:
        db.add(User(id=1, full_name='A'))
        await db.commit()


async def test_whole_free_day():
    slots = await slots_for(next_working_day())

    assert slots[0] == '09:00'
    assert slots[-1] == '19:00'  # 45 minutes have to fit before 20:00
    assert len(slots) == 21


async def test_day_off():
    day = next_working_day()
    while day.weekday() != 6:
        day += timedelta(days=1)

    assert await slots_for(day) == []


async def test_bookings_block_overlapping_starts():
    await make_user()
    day = next_working_day()
    await add_booking(1, at(day, 10))

    slots = await slots_for(day)

    assert '09:00' in slots
    assert {'09:30', '10:00', '10:30'}.isdisjoint(slots)
    assert '11:00' in slots


async def test_cancelled_bookings_do_not_block():
    await make_user()
    day = next_working_day()
    await add_booking(1, at(day, 10), status=BookingStatus.CANCELLED)

    assert '10:00' in await slots_for(day)


async def test_other_specialists_bookings_do_not_block():
    await make_user()
    day = next_working_day()
    await add_booking(1, at(day, 10), specialist_id=3)

    assert '10:00' in await slots_for(day)


async def test_today_starts_after_minimum_notice():
    slots = await slots_for(services.now().date())
    earliest = services.now() + timedelta(minutes=60)

    assert all(slot >= f'{earliest:%H:%M}' for slot in slots)


async def test_days_with_slots_skip_sundays():
    async with SessionLocal() as db:
        days = await services.days_with_slots(db, await db.get(Specialist, 1), await db.get(Service, 1))

    assert days
    assert all(day.weekday() != 6 for day in days)
