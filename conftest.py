import asyncio
import os

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

# Tests use their own database, so local data is never touched,
# conversation state lives in memory and user 9001 is the admin.
# This has to happen before core.settings is imported anywhere.
load_dotenv()
os.environ['REDIS_URL'] = ''
os.environ['ADMIN_IDS'] = '9001'
os.environ['DB_NAME'] = f'{os.environ["DB_NAME"]}_test'

from sqlalchemy import text  # noqa: E402

from apps.catalog.seed import seed  # noqa: E402
from apps.common.tests.bot import FakeTelegram  # noqa: E402
from core import settings  # noqa: E402
from core.db import engine  # noqa: E402
from main import create_dispatcher  # noqa: E402


async def recreate_test_database():
    conn = await asyncpg.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database='postgres',
    )
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{settings.DB_NAME}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
    finally:
        await conn.close()


def pytest_sessionstart(session):
    asyncio.run(recreate_test_database())
    # Build the schema with the real migrations, so they get tested too
    command.upgrade(Config('alembic.ini'), 'head')


@pytest.fixture(autouse=True)
async def clean_db():
    yield
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE users, services, specialists, bookings RESTART IDENTITY CASCADE'))


@pytest.fixture
async def catalog():
    """The demo barbershop: 4 services, 3 specialists working 9:00-20:00."""
    await seed()


# Routers can be attached to one dispatcher only, so all tests share it
dispatcher = create_dispatcher()


@pytest.fixture
def tg():
    # Forget conversation state from the previous test
    dispatcher.storage.storage.clear()
    return FakeTelegram(dispatcher)
