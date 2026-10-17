import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bookings.models import Booking
from apps.users.models import User
from core import settings
from core.formatting import day_label, local
from core.i18n import t

logger = logging.getLogger(__name__)


def booking_fields(booking: Booking, lang: str | None) -> dict:
    starts = local(booking.starts_at)
    return {
        'id': booking.id,
        'day': day_label(starts.date(), lang),
        'time': f'{starts:%H:%M}',
        'service': booking.service.title(lang),
        'specialist': booking.specialist.full_name,
        'client': booking.user.full_name,
        'phone': booking.user.phone or '—',
    }


async def notify_admins(bot: Bot, db: AsyncSession, key: str, booking: Booking):
    """Tell every admin about a booking event, each in their own language."""
    await db.refresh(booking, ('user', 'service', 'specialist'))
    for admin_id in settings.ADMIN_IDS:
        admin = await db.get(User, admin_id)
        lang = admin.language if admin else None
        try:
            await bot.send_message(admin_id, t(key, lang, **booking_fields(booking, lang)))
        except TelegramAPIError:
            # An admin who never opened the bot can't receive messages, don't break the client's flow
            logger.warning('Could not notify admin %s', admin_id)
