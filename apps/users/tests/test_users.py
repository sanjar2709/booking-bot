import asyncio

from sqlalchemy import func, select

from apps.common.tests.bot import buttons, texts
from apps.users.models import User
from core.db import SessionLocal
from core.i18n import LANGUAGES, all_languages, t
from core.locales import en, ru, uz


def test_all_languages_have_the_same_texts():
    assert set(uz.TEXTS) == set(ru.TEXTS) == set(en.TEXTS)


def test_translation_fallbacks():
    assert t('btn_book', 'ru') == '📅 Записаться'
    assert t('btn_book', 'de') == t('btn_book', 'uz')
    assert t('no_such_key', 'en') == 'no_such_key'
    assert all_languages('btn_book') == {'📅 Yozilish', '📅 Записаться', '📅 Book'}


async def test_new_user_is_asked_for_language_in_all_three(tg):
    user = tg.user(1, 'Sanjar Samadov')

    replies = await tg.send(user, '/start')

    assert len(texts(replies)[0].splitlines()) == len(LANGUAGES)
    assert buttons(replies[0]) == [title for title, _ in LANGUAGES.values()]


async def test_choosing_language_shows_menu_in_it(tg):
    user = tg.user(1, 'Sanjar Samadov')
    await tg.send(user, '/start')

    replies = await tg.click(user, 'lang:ru')

    assert texts(replies)[0] == t('language_saved', 'ru')
    assert 'Sanjar Samadov' in texts(replies)[1]
    assert buttons(replies[-1]) == ['📅 Записаться', '🗂 Мои записи', '📞 Контакты', '🌐 Язык']


async def test_known_user_gets_welcome_right_away(tg):
    user = tg.user(1)
    await tg.send(user, '/start')
    await tg.click(user, 'lang:en')

    replies = await tg.send(user, '/start')

    assert texts(replies)[0].startswith('Hello')


async def test_change_language_later(tg):
    user = tg.user(1)
    await tg.send(user, '/start')
    await tg.click(user, 'lang:uz')

    await tg.send(user, '🌐 Til')
    replies = await tg.click(user, 'lang:en')

    assert texts(replies) == ['Language saved ✅', 'Main menu']


async def test_unknown_language_code_is_ignored(tg):
    user = tg.user(1)
    await tg.send(user, '/start')

    assert await tg.click(user, 'lang:de') == []


async def test_contacts(tg):
    user = tg.user(1)
    await tg.send(user, '/start')
    await tg.click(user, 'lang:en')

    replies = await tg.send(user, '📞 Contacts')

    assert 'Barber House' in texts(replies)[0]


async def test_several_first_updates_at_once(tg):
    """A new user's updates can arrive together and run in parallel, the user must be created once without errors."""
    user = tg.user(1, 'Sanjar Samadov')

    await asyncio.gather(*(tg.send(user, '/start') for _ in range(5)))

    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 1
