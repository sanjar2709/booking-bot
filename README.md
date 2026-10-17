# booking-bot

[![CI](https://github.com/sanjar2709/booking-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjar2709/booking-bot/actions/workflows/ci.yml)

Telegram bot for booking appointments at a barbershop, a clinic or any place that works by schedule.
A client picks a service, a specialist, a day and a free time, shares their phone once, and gets a reminder
two hours before the visit. The owner sees the day's schedule and stats right in the bot.

Built with aiogram 3, async SQLAlchemy and PostgreSQL. Uzbek, Russian and English.

## What a booking looks like

```
👤 📅 Book
🤖 Choose a service:
   [Haircut · 45 min · 80 000 UZS] [Beard shave · 30 min · 50 000 UZS] ...
👤 Haircut
🤖 Choose a specialist:  [👤 Aziz Karimov] [👤 Bekzod Aliyev] [👤 Jasur Tursunov] [⬅️ Back]
👤 Aziz Karimov
🤖 Choose a day:  [Mon, 19.10] [Tue, 20.10] [Wed, 21.10] ...
👤 Mon, 19.10
🤖 Choose a time:  [09:00] [09:30] [10:00] [10:30] ...
👤 10:00
🤖 Please share your phone number so we can reach you 👇   [📱 Share phone number]
🤖 Please check: Haircut, Aziz Karimov, Mon 19.10 10:00, 45 min, 80 000 UZS   [✅ Confirm] [⬅️ Back] [❌ Cancel]
👤 ✅ Confirm
🤖 ✅ You're booked! We'll remind you 2 hours before.
```

## Features

**For clients**
- Book in a few taps: service → specialist → day → time, with a back button on every step
- Only days and times that are really free are shown: working hours, service length and existing bookings are all taken into account
- Phone number is asked once, through Telegram's "share contact" button (someone else's contact is not accepted)
- "My bookings" with cancellation, allowed up to 2 hours before the visit
- Reminder 2 hours before, in the client's language

**For the owner** (`/admin`, for Telegram ids in `ADMIN_IDS`)
- Today's and tomorrow's schedule with client names and phones
- Cancel a booking, the client gets a message in their language
- Stats for the last 30 days: bookings, cancellations, revenue, most booked service
- A message for every new booking and every cancellation by a client

## Some decisions

**No double bookings.** If two clients confirm the same time at the same second, a "check then insert" approach lets
both through. Here PostgreSQL has an exclusion constraint on the bookings table: for one specialist, two active bookings
can't have overlapping time ranges. The second confirmation fails, and the bot shows that client the updated list of free times.

**Reminders without a queue.** A background task checks every minute for bookings starting within 2 hours. Rows are picked with
`SELECT ... FOR UPDATE SKIP LOCKED` and marked with `reminded_at`, so even two running copies of the bot don't send a reminder twice.
If a client blocked the bot, the booking is still marked as reminded and the loop moves on.

**Conversation state in Redis.** The step a client is on lives in Redis, so restarting the bot doesn't throw people out
in the middle of a booking. Buttons from an old message answer "this button is out of date" instead of crashing.

**Tests without Telegram.** `apps/common/tests/bot.py` feeds fake updates into the real dispatcher and records what the bot
would send. So the tests go through the actual handlers, filters, keyboards and state, not just the service functions.

## Running it

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Fill in `.env`:

```bash
cp .env.example .env    # BOT_TOKEN, your Telegram id in ADMIN_IDS, database credentials
```

3. Start it and add the demo barbershop (4 services, 3 specialists):

```bash
docker compose up -d
docker compose exec bot python -m apps.catalog.seed
```

Without Docker for the bot itself:

```bash
docker compose up -d db redis
python -m venv venv && source venv/bin/activate
pip install -r requirements/dev.txt
alembic upgrade head
python -m apps.catalog.seed
python main.py
```

Business name, address, phone, booking window, slot step and the reminder time are set through `.env`, see `core/settings.py`.

## Tests

```bash
pytest --cov
```

42 tests, 96% coverage, including a test where two sessions book the same slot at the same moment.

## Project layout

```
apps/
  users/      user model, language choice, main menu
  catalog/    services, specialists, working hours, demo data
  bookings/   booking steps, my bookings, reminders, free slot calculation
  admin/      /admin panel and notifications for the owner
  common/     base model, fake Telegram and factories for tests
core/
  locales/    uz, ru, en texts
  settings.py, db.py, i18n.py, formatting.py, middlewares.py
migrations/   Alembic
main.py
```

## License

MIT
