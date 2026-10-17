from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser

from .models import User


class UserMiddleware(BaseMiddleware):
    """Finds or creates the user for every update and passes `user` and `lang` to handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TelegramUser | None = data.get('event_from_user')
        if tg_user is None:
            return await handler(event, data)

        db = data['db']
        user = await db.get(User, tg_user.id)
        if user is None:
            user = User(id=tg_user.id, full_name=tg_user.full_name, username=tg_user.username)
            db.add(user)
            await db.commit()
        elif (user.full_name, user.username) != (tg_user.full_name, tg_user.username):
            user.full_name, user.username = tg_user.full_name, tg_user.username
            await db.commit()

        data['user'] = user
        data['lang'] = user.language
        return await handler(event, data)
