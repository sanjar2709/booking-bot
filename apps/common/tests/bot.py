"""A fake Telegram for tests: updates go into the real dispatcher, replies are recorded instead of sent."""

from datetime import datetime
from itertools import count
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Contact, Message, Update, User

_ids = count(1)


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.requests: list[TelegramMethod] = []

    # Same signature as BaseSession.make_request, hence the timeout argument
    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None) -> Any:  # noqa: ASYNC109
        self.requests.append(method)
        if method.__returning__ is Message or getattr(method, 'text', None) is not None:
            chat_id = getattr(method, 'chat_id', None) or 1
            return Message(
                message_id=next(_ids),
                date=datetime.now(),
                chat=Chat(id=chat_id, type='private'),
                text=getattr(method, 'text', None),
            )
        return True

    async def stream_content(self, *args, **kwargs):
        yield b''

    async def close(self):
        pass


class FakeTelegram:
    def __init__(self, dispatcher):
        self.session = FakeSession()
        self.bot = Bot('42:TEST', session=self.session)
        self.dp = dispatcher

    def user(self, user_id: int, name='Test User', username=None) -> User:
        first, _, last = name.partition(' ')
        return User(id=user_id, is_bot=False, first_name=first, last_name=last or None, username=username)

    async def send(self, user: User, text: str | None = None, contact_phone: str | None = None):
        contact = None
        if contact_phone:
            contact = Contact(phone_number=contact_phone, first_name=user.first_name, user_id=user.id)
        message = Message(
            message_id=next(_ids),
            date=datetime.now(),
            chat=Chat(id=user.id, type='private'),
            from_user=user,
            text=text,
            contact=contact,
        )
        return await self._feed(Update(update_id=next(_ids), message=message))

    async def click(self, user: User, data: str):
        callback = CallbackQuery(
            id=str(next(_ids)),
            from_user=user,
            chat_instance='test',
            data=data,
            message=Message(
                message_id=next(_ids), date=datetime.now(), chat=Chat(id=user.id, type='private'), text='…'
            ),
        )
        return await self._feed(Update(update_id=next(_ids), callback_query=callback))

    async def _feed(self, update: Update) -> list[TelegramMethod]:
        before = len(self.session.requests)
        await self.dp.feed_update(self.bot, update)
        # What the bot sent back for this update, without callback answers
        return [r for r in self.session.requests[before:] if not isinstance(r, AnswerCallbackQuery)]


def texts(requests: list[TelegramMethod]) -> list[str]:
    return [r.text for r in requests if getattr(r, 'text', None)]


def buttons(request: TelegramMethod) -> list[str]:
    markup = request.reply_markup
    rows = getattr(markup, 'inline_keyboard', None) or getattr(markup, 'keyboard', None) or []
    return [b.text for row in rows for b in row]
