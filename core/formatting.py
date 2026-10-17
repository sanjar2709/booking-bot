from datetime import date
from decimal import Decimal

from core.i18n import t


def money(value: Decimal | int, lang: str | None) -> str:
    # 120000 -> "120 000 so'm"
    return f'{value:,.0f}'.replace(',', ' ') + ' ' + t('currency', lang)


def day_label(day: date, lang: str | None) -> str:
    return f'{t("weekdays", lang)[day.weekday()]}, {day:%d.%m}'
