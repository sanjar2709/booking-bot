import asyncio

import pytest
from sqlalchemy import func, select

from apps.bookings import services
from apps.bookings.keyboards import NavCb, ServiceCb
from apps.bookings.models import Booking
from apps.catalog.models import Service, Specialist
from apps.common.tests.bot import buttons, texts
from apps.common.tests.factories import add_booking, at, next_working_day, register, walk_to_confirm
from apps.users.models import User
from core.db import SessionLocal

pytestmark = pytest.mark.usefixtures('catalog')

CONFIRM = NavCb(to='confirm').pack()


async def count_bookings() -> int:
    async with SessionLocal() as db:
        return await db.scalar(select(func.count()).select_from(Booking))


async def test_services_are_listed_with_price_and_duration(tg):
    user = await register(tg, 1)

    replies = await tg.send(user, '📅 Book')

    assert buttons(replies[0])[0] == 'Haircut · 45 min · 80 000 UZS'


async def test_only_specialists_doing_the_service_are_offered(tg):
    user = await register(tg, 1)
    await tg.send(user, '📅 Book')

    # Kids haircut is done by Jasur and Bekzod, not Aziz
    replies = await tg.click(user, ServiceCb(id=4).pack())

    assert buttons(replies[0]) == ['👤 Bekzod Aliyev', '👤 Jasur Tursunov', '⬅️ Back']


async def test_full_booking_asks_phone_once(tg):
    user = await register(tg, 1)
    day = next_working_day()

    replies = await walk_to_confirm(tg, user, day)
    assert texts(replies) == ['Please share your phone number so we can reach you 👇']

    replies = await tg.send(user, contact_phone='+998901112233')
    assert 'Is everything right?' in texts(replies)[-1]

    replies = await tg.click(user, CONFIRM)
    assert texts(replies)[0].startswith("✅ You're booked!")
    assert await count_bookings() == 1

    # Second time the phone is already known
    replies = await walk_to_confirm(tg, user, day, at='1500')
    assert 'Is everything right?' in texts(replies)[0]


async def test_someone_elses_contact_is_not_accepted(tg):
    user = await register(tg, 1)
    await walk_to_confirm(tg, user, next_working_day())

    replies = await tg.send(tg.user(2), contact_phone='+998900000000')  # different sender, no state
    replies = await tg.send(user, 'my number is 123')

    assert texts(replies) == ['Please share your phone number so we can reach you 👇']
    async with SessionLocal() as db:
        assert (await db.get(User, 1)).phone is None


async def test_time_taken_while_confirming(tg):
    first = await register(tg, 1, phone='+998901111111')
    second = await register(tg, 2, phone='+998902222222')
    day = next_working_day()
    await walk_to_confirm(tg, first, day)
    await walk_to_confirm(tg, second, day)

    await tg.click(first, CONFIRM)
    replies = await tg.click(second, CONFIRM)

    assert texts(replies)[0].startswith('Sorry, someone just took this time')
    # 10:00-10:45 is gone, and so are the slots overlapping it
    assert {'09:30', '10:00', '10:30'}.isdisjoint(buttons(replies[0]))
    assert await count_bookings() == 1


async def test_booked_times_disappear_from_the_list(tg):
    user = await register(tg, 1, phone='+998901111111')
    day = next_working_day()
    await add_booking(user.id, at(day, 12))

    replies = await walk_to_confirm(tg, user, day, at='0900')
    replies = await tg.click(user, NavCb(to='times').pack())

    assert '12:00' not in buttons(replies[0])
    assert '11:00' in buttons(replies[0])  # 11:00-11:45 still fits before 12:00


async def test_back_buttons(tg):
    user = await register(tg, 1, phone='+998901111111')
    await walk_to_confirm(tg, user, next_working_day())

    replies = await tg.click(user, NavCb(to='days').pack())
    assert 'Choose a day' in texts(replies)[0]
    replies = await tg.click(user, NavCb(to='services').pack())
    assert texts(replies)[0] == 'Choose a service:'


async def test_cancel_on_confirmation(tg):
    user = await register(tg, 1, phone='+998901111111')
    await walk_to_confirm(tg, user, next_working_day())

    replies = await tg.click(user, NavCb(to='cancel').pack())

    assert texts(replies) == ['Booking cancelled.']
    assert await count_bookings() == 0


async def test_old_buttons_after_the_conversation_ended(tg):
    user = await register(tg, 1)

    await tg.click(user, NavCb(to='times').pack())
    await tg.click(user, ServiceCb(id=1).pack())

    alerts = [r.text for r in tg.session.requests if getattr(r, 'show_alert', False)]
    assert alerts == ['This button is out of date, please start again.'] * 2


async def test_no_services(tg):
    async with SessionLocal() as db:
        for service in await db.scalars(select(Service)):
            service.is_active = False
        await db.commit()
    user = await register(tg, 1)

    replies = await tg.send(user, '📅 Book')

    assert texts(replies) == ['No services yet. Please try later.']


async def test_same_slot_from_two_sessions_at_once():
    """Two confirmations hit the database at the same moment: the exclusion constraint lets one through."""
    async with SessionLocal() as db:
        db.add_all([User(id=1, full_name='A'), User(id=2, full_name='B')])
        await db.commit()
    starts_at = at(next_working_day(), 16)

    async def book(user_id):
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            specialist, service = await db.get(Specialist, 1), await db.get(Service, 1)
            try:
                await services.create_booking(db, user, specialist, service, starts_at)
                return 'ok'
            except services.SlotTakenError:
                return 'taken'

    results = await asyncio.gather(book(1), book(2))

    assert sorted(results) == ['ok', 'taken']
