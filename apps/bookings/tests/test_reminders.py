from datetime import timedelta

import pytest
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from apps.bookings.models import Booking, BookingStatus
from apps.bookings.reminders import send_due_reminders
from apps.bookings.services import create_booking, now
from apps.catalog.models import Service, Specialist
from apps.common.tests.bot import FakeSession
from apps.common.tests.factories import add_booking
from apps.users.models import User
from core.db import SessionLocal

pytestmark = pytest.mark.usefixtures('catalog')


class BlockedBySomeSession(FakeSession):
    """Behaves like Telegram when some users have blocked the bot."""

    def __init__(self, blocked=()):
        super().__init__()
        self.blocked = set(blocked)

    async def make_request(self, bot, method, timeout=None):  # noqa: ASYNC109  (signature of BaseSession)
        if getattr(method, 'chat_id', None) in self.blocked:
            raise TelegramForbiddenError(method=method, message='Forbidden: bot was blocked by the user')
        return await super().make_request(bot, method, timeout)


async def make_users(*languages):
    async with SessionLocal() as db:
        db.add_all([User(id=i, full_name=f'User {i}', language=lang) for i, lang in enumerate(languages, start=1)])
        await db.commit()


async def run(session) -> int:
    async with SessionLocal() as db:
        return await send_due_reminders(Bot('42:TEST', session=session), db)


async def test_reminds_in_users_language():
    await make_users('ru')
    await add_booking(1, now() + timedelta(minutes=60))
    session = BlockedBySomeSession()

    assert await run(session) == 1
    assert session.requests[0].chat_id == 1
    assert session.requests[0].text.startswith('⏰ Напоминание')


async def test_only_due_confirmed_bookings_are_reminded():
    await make_users('en')
    await add_booking(1, now() + timedelta(hours=5))
    await add_booking(1, now() + timedelta(minutes=30), status=BookingStatus.CANCELLED, specialist_id=2)
    await add_booking(1, now() - timedelta(minutes=30), specialist_id=3)

    assert await run(BlockedBySomeSession()) == 0


async def test_no_second_reminder():
    await make_users('en')
    await add_booking(1, now() + timedelta(minutes=60))
    session = BlockedBySomeSession()

    await run(session)
    await run(session)

    assert len(session.requests) == 1


async def test_blocked_user_does_not_stop_the_others():
    await make_users('en', 'en')
    await add_booking(1, now() + timedelta(minutes=60))
    await add_booking(2, now() + timedelta(minutes=60), specialist_id=2)

    sent = await run(BlockedBySomeSession(blocked={1}))

    assert sent == 1
    async with SessionLocal() as db:
        # Marked as done for the blocked user too, so we don't retry every minute
        assert all(b.reminded_at for b in (await db.get(Booking, 1), await db.get(Booking, 2)))


async def test_booking_made_shortly_before_start_is_not_reminded():
    await make_users('en')
    async with SessionLocal() as db:
        user, specialist, service = await db.get(User, 1), await db.get(Specialist, 1), await db.get(Service, 1)
        await create_booking(db, user, specialist, service, now() + timedelta(minutes=90))

    assert await run(BlockedBySomeSession()) == 0
