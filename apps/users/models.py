from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.models import TimeStampedMixin
from core.db import Base


class User(TimeStampedMixin, Base):
    __tablename__ = 'users'

    # Telegram user id, so there is no separate key to keep in sync
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String(150), default='')
    username: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(2))
    phone: Mapped[str | None] = mapped_column(String(20))

    def __repr__(self):
        return f'<User {self.id} {self.full_name}>'
