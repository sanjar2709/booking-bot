from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser

from core import settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, event_from_user: TelegramUser | None = None) -> bool:
        return event_from_user is not None and event_from_user.id in settings.ADMIN_IDS
