from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import TZ, now
from apps.catalog.models import Service


async def bookings_on(db: AsyncSession, day: date) -> list[Booking]:
    start = datetime.combine(day, datetime.min.time(), TZ)
    query = (
        select(Booking)
        .where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at >= start,
            Booking.starts_at < start + timedelta(days=1),
        )
        .order_by(Booking.starts_at)
    )
    return list(await db.scalars(query))


async def stats(db: AsyncSession, days: int = 30) -> dict:
    since = now() - timedelta(days=days)
    recent = Booking.created_at >= since
    active = Booking.status != BookingStatus.CANCELLED

    total = await db.scalar(select(func.count()).where(recent))
    cancelled = await db.scalar(select(func.count()).where(recent, Booking.status == BookingStatus.CANCELLED))
    revenue = await db.scalar(select(func.coalesce(func.sum(Booking.price), 0)).where(recent, active))
    clients = await db.scalar(select(func.count(func.distinct(Booking.user_id))).where(recent))
    top = (await db.execute(
        select(Service, func.count(Booking.id).label('n'))
        .join(Booking, Booking.service_id == Service.id)
        .where(recent, active)
        .group_by(Service.id)
        .order_by(func.count(Booking.id).desc())
        .limit(1)
    )).first()
    return {
        'total': total,
        'cancelled': cancelled,
        'revenue': revenue,
        'clients': clients,
        'top_service': top[0] if top else None,
    }
