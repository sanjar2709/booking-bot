import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from apps.bookings.handlers import router as bookings_router
from apps.bookings.my_handlers import router as my_bookings_router
from apps.users.handlers import router as users_router
from apps.users.middlewares import UserMiddleware
from core import settings
from core.middlewares import DbSessionMiddleware


def create_dispatcher() -> Dispatcher:
    storage = RedisStorage.from_url(settings.REDIS_URL) if settings.REDIS_URL else MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.include_router(users_router)
    dp.include_router(my_bookings_router)
    dp.include_router(bookings_router)
    return dp


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    if not settings.BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN environment variable is not set')

    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await create_dispatcher().start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
