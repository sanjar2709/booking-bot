from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from core.db import SessionLocal


class DbSessionMiddleware(BaseMiddleware):
    """Opens one database session per update and passes it to handlers as `db`."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with SessionLocal() as db:
            data['db'] = db
            return await handler(event, data)
