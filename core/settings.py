import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Telegram user ids of people who can open /admin, separated by spaces
ADMIN_IDS = {int(i) for i in os.getenv('ADMIN_IDS', '').split()}

TIME_ZONE = 'Asia/Tashkent'

# Booking

BOOKING_DAYS_AHEAD = int(os.getenv('BOOKING_DAYS_AHEAD', 7))
SLOT_STEP_MINUTES = int(os.getenv('SLOT_STEP_MINUTES', 30))
MIN_NOTICE_MINUTES = int(os.getenv('MIN_NOTICE_MINUTES', 60))
CANCEL_DEADLINE_HOURS = int(os.getenv('CANCEL_DEADLINE_HOURS', 2))

# Shown in the welcome message and under "Contacts"
BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Barber House')
BUSINESS_ADDRESS = os.getenv('BUSINESS_ADDRESS', 'Tashkent, Amir Temur street 15')
BUSINESS_PHONE = os.getenv('BUSINESS_PHONE', '+998 90 123 45 67')
BUSINESS_HOURS = os.getenv('BUSINESS_HOURS', '09:00 - 20:00')

# Database

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
DB_ECHO = os.getenv('DB_ECHO') == '1'

# Conversation state (which step of the booking a user is on) is kept in Redis,
# so a restart of the bot doesn't throw people out in the middle. Empty means memory.
REDIS_URL = os.getenv('REDIS_URL', '')
