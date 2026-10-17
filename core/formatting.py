from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from core import settings
from core.i18n import t

TZ = ZoneInfo(settings.TIME_ZONE)


def money(value: Decimal | int, lang: str | None) -> str:
    # 120000 -> "120 000 so'm"
    return f'{value:,.0f}'.replace(',', ' ') + ' ' + t('currency', lang)


def day_label(day: date, lang: str | None) -> str:
    return f'{t("weekdays", lang)[day.weekday()]}, {day:%d.%m}'


def local(moment: datetime) -> datetime:
    """Times are stored in UTC, people want to see Tashkent time."""
    return moment.astimezone(TZ)
