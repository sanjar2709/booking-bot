import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message

from core import settings
from core.middlewares import DbSessionMiddleware

start_router = Router()


@start_router.message(CommandStart())
async def start(message: Message):
    await message.answer(f'Hello, {message.from_user.full_name}!')


def create_dispatcher() -> Dispatcher:
    storage = RedisStorage.from_url(settings.REDIS_URL) if settings.REDIS_URL else MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.include_router(start_router)
    return dp


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    if not settings.BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN environment variable is not set')

    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await create_dispatcher().start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
