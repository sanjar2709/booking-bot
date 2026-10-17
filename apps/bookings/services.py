from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.catalog.models import Service, Specialist
from apps.users.models import User
from core import settings

from .models import Booking, BookingStatus

TZ = ZoneInfo(settings.TIME_ZONE)


class SlotTakenError(Exception):
    pass


class TooLateToCancelError(Exception):
    pass


def now() -> datetime:
    return datetime.now(TZ)


async def active_services(db: AsyncSession) -> list[Service]:
    return list(await db.scalars(select(Service).where(Service.is_active).order_by(Service.id)))


async def specialists_for(db: AsyncSession, service_id: int) -> list[Specialist]:
    query = (
        select(Specialist)
        .where(Specialist.is_active, Specialist.services.any(Service.id == service_id))
        .order_by(Specialist.full_name)
    )
    return list(await db.scalars(query))


async def free_slots(db: AsyncSession, specialist: Specialist, service: Service, day: date) -> list[datetime]:
    """Start times on the day when the service fits into working hours and doesn't clash with a booking."""
    hours = specialist.hours_on(day.weekday())
    if hours is None:
        return []

    day_start = datetime.combine(day, hours.start_time, TZ)
    day_end = datetime.combine(day, hours.end_time, TZ)
    busy = list(await db.execute(
        select(Booking.starts_at, Booking.ends_at).where(
            Booking.specialist_id == specialist.id,
            Booking.status != BookingStatus.CANCELLED,
            Booking.starts_at < day_end,
            Booking.ends_at > day_start,
        )
    ))

    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=settings.SLOT_STEP_MINUTES)
    # Don't offer a time that starts in a few minutes, nobody gets there that fast
    earliest = now() + timedelta(minutes=settings.MIN_NOTICE_MINUTES)

    slots = []
    start = day_start
    while start + duration <= day_end:
        end = start + duration
        if start >= earliest and not any(start < b_end and end > b_start for b_start, b_end in busy):
            slots.append(start)
        start += step
    return slots


async def days_with_slots(db: AsyncSession, specialist: Specialist, service: Service) -> list[date]:
    today = now().date()
    days = [today + timedelta(days=i) for i in range(settings.BOOKING_DAYS_AHEAD)]
    return [day for day in days if await free_slots(db, specialist, service, day)]


async def create_booking(
    db: AsyncSession, user: User, specialist: Specialist, service: Service, starts_at: datetime
) -> Booking:
    booking = Booking(
        user_id=user.id,
        specialist_id=specialist.id,
        service_id=service.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=service.duration_minutes),
        price=service.price,
    )
    # Booked less than the reminder period ahead: they just saw the time, a reminder right away would be odd
    if starts_at - now() <= timedelta(hours=settings.REMIND_BEFORE_HOURS):
        booking.reminded_at = now()
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if 'no_overlapping_bookings' in str(e.orig):
            raise SlotTakenError from None
        raise
    await db.refresh(booking)
    return booking


async def upcoming_bookings(db: AsyncSession, user: User) -> list[Booking]:
    query = (
        select(Booking)
        .where(Booking.user_id == user.id, Booking.status == BookingStatus.CONFIRMED, Booking.starts_at > now())
        .order_by(Booking.starts_at)
    )
    return list(await db.scalars(query))


async def get_own_booking(db: AsyncSession, user: User, booking_id: int) -> Booking | None:
    booking = await db.get(Booking, booking_id)
    if booking is None or booking.user_id != user.id or booking.status != BookingStatus.CONFIRMED:
        return None
    return booking


async def cancel_booking(db: AsyncSession, booking: Booking, by_admin=False) -> Booking:
    if not by_admin and now() > booking.starts_at - timedelta(hours=settings.CANCEL_DEADLINE_HOURS):
        raise TooLateToCancelError
    booking.status = BookingStatus.CANCELLED
    await db.commit()
    return booking
