"""Fill an empty database with a demo barbershop: python -m apps.catalog.seed"""

import asyncio
from datetime import time
from decimal import Decimal

from sqlalchemy import func, select

from core.db import SessionLocal

from .models import Service, Specialist, WorkingHours

SERVICES = (
    # uz, ru, en, minutes, price
    ('Soch olish', 'Стрижка', 'Haircut', 45, 80_000),
    ('Soqol olish', 'Бритьё бороды', 'Beard shave', 30, 50_000),
    ('Soch va soqol', 'Стрижка и борода', 'Haircut and beard', 75, 120_000),
    ('Bolalar sochi', 'Детская стрижка', 'Kids haircut', 30, 60_000),
)

SPECIALISTS = (
    # name, service numbers, working weekdays
    ('Aziz Karimov', (0, 1, 2), range(0, 6)),
    ('Jasur Tursunov', (0, 2, 3), range(1, 7)),
    ('Bekzod Aliyev', (0, 1, 3), (0, 1, 2, 3, 4)),
)


async def seed():
    async with SessionLocal() as db:
        if await db.scalar(select(func.count()).select_from(Service)):
            print('Database already has services, nothing to do')
            return

        services = [
            Service(title_uz=uz, title_ru=ru, title_en=en, duration_minutes=minutes, price=Decimal(price))
            for uz, ru, en, minutes, price in SERVICES
        ]
        for name, service_numbers, weekdays in SPECIALISTS:
            db.add(Specialist(
                full_name=name,
                services=[services[i] for i in service_numbers],
                working_hours=[WorkingHours(weekday=d, start_time=time(9), end_time=time(20)) for d in weekdays],
            ))
        await db.commit()
        print(f'Added {len(services)} services and {len(SPECIALISTS)} specialists')


if __name__ == '__main__':
    asyncio.run(seed())
