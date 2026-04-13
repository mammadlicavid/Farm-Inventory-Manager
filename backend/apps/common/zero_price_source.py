from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext_lazy as _


ZERO_PRICE_SOURCE_CHOICES = [
    ("internal", _("Təsərrüfat daxilində yaranıb")),
    ("existing", _("Əvvəlcədən məndə var idi")),
    ("free", _("Pulsuz gəlib / hədiyyədir")),
    ("other", _("Digər")),
]

ZERO_PRICE_SOURCE_VALUES = {value for value, _label in ZERO_PRICE_SOURCE_CHOICES}


def _normalized_price_text(value: str | int | float | Decimal | None) -> str:
    if value is None:
        return ""
    return str(value).strip().replace(",", ".")


def normalize_zero_price_source(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if normalized in ZERO_PRICE_SOURCE_VALUES:
        return normalized
    return None


def is_explicit_zero_price(value: str | int | float | Decimal | None) -> bool:
    raw = _normalized_price_text(value)
    if not raw:
        return False
    try:
        return Decimal(raw) == 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def is_blank_or_zero_price(value: str | int | float | Decimal | None) -> bool:
    raw = _normalized_price_text(value)
    if not raw:
        return True
    try:
        return Decimal(raw) == 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def get_zero_price_source_label(record) -> str:
    if not record:
        return ""

    quantity = getattr(record, "quantity", 0) or 0
    zero_price_source = getattr(record, "zero_price_source", None)
    price = getattr(record, "price", None)

    if quantity <= 0 or not zero_price_source or not is_blank_or_zero_price(price):
        return ""

    display_getter = getattr(record, "get_zero_price_source_display", None)
    if callable(display_getter):
        return str(display_getter() or "").strip()

    return ""
