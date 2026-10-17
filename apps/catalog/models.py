from datetime import time
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, ForeignKey, Numeric, SmallInteger, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.common.models import TimeStampedMixin
from core.db import Base

specialist_services = Table(
    'specialist_services',
    Base.metadata,
    Column('specialist_id', ForeignKey('specialists.id', ondelete='CASCADE'), primary_key=True),
    Column('service_id', ForeignKey('services.id', ondelete='CASCADE'), primary_key=True),
)


class Service(TimeStampedMixin, Base):
    __tablename__ = 'services'
    __table_args__ = (
        CheckConstraint('duration_minutes > 0', name='positive_duration'),
        CheckConstraint('price >= 0', name='non_negative_price'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title_uz: Mapped[str] = mapped_column(String(100))
    title_ru: Mapped[str] = mapped_column(String(100))
    title_en: Mapped[str] = mapped_column(String(100))
    duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        return f'<Service {self.title_en}>'

    def title(self, lang: str | None) -> str:
        return getattr(self, f'title_{lang}', None) or self.title_uz


class Specialist(TimeStampedMixin, Base):
    __tablename__ = 'specialists'

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(default=True)

    services: Mapped[list[Service]] = relationship(secondary=specialist_services, lazy='selectin')
    working_hours: Mapped[list['WorkingHours']] = relationship(
        back_populates='specialist',
        cascade='all, delete-orphan',
        order_by='WorkingHours.weekday',
        lazy='selectin',
    )

    def __repr__(self):
        return f'<Specialist {self.full_name}>'

    def hours_on(self, weekday: int) -> 'WorkingHours | None':
        return next((h for h in self.working_hours if h.weekday == weekday), None)


class WorkingHours(Base):
    """Weekly schedule: one row per working day. Days without a row are days off."""

    __tablename__ = 'working_hours'
    __table_args__ = (
        UniqueConstraint('specialist_id', 'weekday', name='uq_working_hours_specialist_weekday'),
        CheckConstraint('weekday BETWEEN 0 AND 6', name='valid_weekday'),
        CheckConstraint('start_time < end_time', name='start_before_end'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    specialist_id: Mapped[int] = mapped_column(ForeignKey('specialists.id', ondelete='CASCADE'))
    # 0 = Monday ... 6 = Sunday, same as date.weekday()
    weekday: Mapped[int] = mapped_column(SmallInteger)
    start_time: Mapped[time]
    end_time: Mapped[time]

    specialist: Mapped[Specialist] = relationship(back_populates='working_hours')
