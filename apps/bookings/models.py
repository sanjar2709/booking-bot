from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.catalog.models import Service, Specialist
from apps.common.models import TimeStampedMixin
from apps.users.models import User
from core.db import Base


class BookingStatus(StrEnum):
    CONFIRMED = 'confirmed'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class Booking(TimeStampedMixin, Base):
    __tablename__ = 'bookings'
    __table_args__ = (
        CheckConstraint('starts_at < ends_at', name='starts_before_ends'),
        # Two active bookings of one specialist can't overlap. The database checks it,
        # so two people pressing "Confirm" at the same second can't both get the time.
        ExcludeConstraint(
            ('specialist_id', '='),
            (func.tstzrange(text('starts_at'), text('ends_at'), text("'[)'")), '&&'),
            name='no_overlapping_bookings',
            using='gist',
            where=text("status != 'cancelled'"),
        ),
        Index('ix_bookings_specialist_starts_at', 'specialist_id', 'starts_at'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    specialist_id: Mapped[int] = mapped_column(ForeignKey('specialists.id', ondelete='RESTRICT'))
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id', ondelete='RESTRICT'))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=BookingStatus.CONFIRMED,
    )
    # Copied from the service, so a later price change doesn't touch existing bookings
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(lazy='joined')
    specialist: Mapped[Specialist] = relationship(lazy='joined')
    service: Mapped[Service] = relationship(lazy='joined')

    def __repr__(self):
        return f'<Booking {self.id} {self.starts_at:%Y-%m-%d %H:%M}>'
