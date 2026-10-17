import asyncio
import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.db import SessionLocal
from core.formatting import local
from core.i18n import t

from .models import Booking, BookingStatus
from .services import now

logger = logging.getLogger(__name__)


async def send_due_reminders(bot: Bot, db: AsyncSession) -> int:
    """Remind people whose visit starts within REMIND_BEFORE_HOURS. Returns how many were sent."""
    query = (
        select(Booking)
        .where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.reminded_at.is_(None),
            Booking.starts_at > now(),
            Booking.starts_at <= now() + timedelta(hours=settings.REMIND_BEFORE_HOURS),
        )
        # If two copies of the bot run, each row is taken by one of them only
        .with_for_update(skip_locked=True, of=Booking)
    )
    sent = 0
    for booking in await db.scalars(query):
        lang = booking.user.language
        text = t(
            'reminder',
            lang,
            time=f'{local(booking.starts_at):%H:%M}',
            service=booking.service.title(lang),
            specialist=booking.specialist.full_name,
            address=settings.BUSINESS_ADDRESS,
        )
        try:
            await bot.send_message(booking.user_id, text)
            sent += 1
        except TelegramForbiddenError:
            # The user blocked the bot, nothing we can do
            logger.info('User %s blocked the bot, reminder for booking %s skipped', booking.user_id, booking.id)
        booking.reminded_at = now()
    await db.commit()
    return sent


async def reminder_loop(bot: Bot, every_seconds: int = 60):
    while True:
        try:
            async with SessionLocal() as db:
                if sent := await send_due_reminders(bot, db):
                    logger.info('Sent %s reminders', sent)
        except Exception:
            logger.exception('Reminder run failed, will try again')
        await asyncio.sleep(every_seconds)
