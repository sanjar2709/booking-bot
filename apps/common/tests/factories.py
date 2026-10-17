from datetime import date, datetime, time, timedelta

from apps.bookings.keyboards import DayCb, ServiceCb, SpecialistCb, TimeCb
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import TZ, now
from apps.catalog.models import Service
from core.db import SessionLocal

# Seeded specialist 1 (Aziz Karimov) works Monday to Saturday and does service 1 (Haircut, 45 min)
SPECIALIST_ID = 1
SERVICE_ID = 1


def next_working_day(days=2) -> date:
    """A day at least `days` ahead that is not a Sunday, so specialist 1 works."""
    day = now().date() + timedelta(days=days)
    return day + timedelta(days=1) if day.weekday() == 6 else day


async def register(tg, user_id: int, lang='en', name='Test User', phone=None):
    user = tg.user(user_id, name)
    await tg.send(user, '/start')
    await tg.click(user, f'lang:{lang}')
    if phone:
        async with SessionLocal() as db:
            from apps.users.models import User

            (await db.get(User, user_id)).phone = phone
            await db.commit()
    return user


async def walk_to_confirm(tg, user, day: date, at='1000', service_id=SERVICE_ID, specialist_id=SPECIALIST_ID):
    """Press through the booking steps up to the confirmation screen (or the phone request)."""
    await tg.send(user, '📅 Book')
    await tg.click(user, ServiceCb(id=service_id).pack())
    await tg.click(user, SpecialistCb(id=specialist_id).pack())
    await tg.click(user, DayCb(value=day.isoformat()).pack())
    return await tg.click(user, TimeCb(value=at).pack())


async def add_booking(
    user_id: int, starts_at: datetime, status=BookingStatus.CONFIRMED, specialist_id=SPECIALIST_ID
) -> Booking:
    async with SessionLocal() as db:
        service = await db.get(Service, SERVICE_ID)
        booking = Booking(
            user_id=user_id,
            specialist_id=specialist_id,
            service_id=SERVICE_ID,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=service.duration_minutes),
            price=service.price,
            status=status,
        )
        db.add(booking)
        await db.commit()
        return booking


def at(day: date, hour: int, minute=0) -> datetime:
    return datetime.combine(day, time(hour, minute), TZ)
