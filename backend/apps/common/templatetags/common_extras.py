from decimal import Decimal, InvalidOperation

from django import template
from django.apps import apps
from django.utils.translation import get_language


register = template.Library()

EXCHANGE_RATES = {
    "AZN": Decimal("1"),
    "USD": Decimal("1.7"),
    "EUR": Decimal("1.85"),
}


def _user_settings(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if hasattr(user, "_sidebar_settings_cache"):
        return user._sidebar_settings_cache
    try:
        UserSettings = apps.get_model("sidebar_menu", "UserSettings")
        settings_obj = UserSettings.objects.filter(user=user).only("unit", "currency").first()
        user._sidebar_settings_cache = settings_obj
        return settings_obj
    except Exception:
        user._sidebar_settings_cache = None
        return None


def _as_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _format_decimal(value):
    normalized = value.quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _snap_imperial_display(value):
    nearest_integer = value.quantize(Decimal("1"))
    if abs(value - nearest_integer) <= Decimal("0.02"):
        return nearest_integer
    nearest_tenth = value.quantize(Decimal("0.1"))
    if abs(value - nearest_tenth) <= Decimal("0.01"):
        return nearest_tenth
    return value


def _unit_label(unit):
    labels = {
        "az": {
            "kg": "kq",
            "lb": "pound",
            "oz": "ounce",
            "litr": "litr",
            "gallon": "gallon",
            "ml": "millilitr",
        },
        "en": {
            "kg": "kg",
            "lb": "pound",
            "oz": "ounce",
            "litr": "liter",
            "gallon": "gallon",
            "ml": "milliliter",
        },
        "ru": {
            "kg": "кг",
            "lb": "фунт",
            "oz": "унция",
            "litr": "литр",
            "gallon": "галлон",
            "ml": "миллилитр",
        },
    }
    lang = (get_language() or "az").split("-")[0]
    return labels.get(lang, labels["az"]).get(unit, unit)


def _user_weight_preference(user):
    settings_obj = _user_settings(user)
    raw = getattr(settings_obj, "unit", "kg_litr") or "kg_litr"
    if raw == "kg":
        raw = "kg_litr"
    elif raw == "lb":
        raw = "lb_gallon"
    elif raw == "gallon":
        raw = "kg_gallon"
    raw = str(raw)
    if raw.startswith("lb_") or raw.startswith("oz_"):
        return "lb"
    return "kg"


def _user_volume_preference(user):
    settings_obj = _user_settings(user)
    raw = getattr(settings_obj, "unit", "kg_litr") or "kg_litr"
    if raw == "kg":
        raw = "kg_litr"
    elif raw == "lb":
        raw = "lb_gallon"
    elif raw == "gallon":
        raw = "kg_gallon"
    return "gallon" if str(raw).endswith("_gallon") else "litr"


def _user_currency(user):
    settings_obj = _user_settings(user)
    return getattr(settings_obj, "currency", "AZN") or "AZN"


def _currency_symbol(currency):
    return {
        "AZN": "₼",
        "USD": "$",
        "EUR": "€",
    }.get(currency or "AZN", "₼")


def _convert_currency(amount, currency):
    value = _as_decimal(amount)
    if value is None:
        return "0"
    rate = EXCHANGE_RATES.get(currency or "AZN", EXCHANGE_RATES["AZN"])
    converted = value / rate if rate else value
    return _format_decimal(converted)


def _convert_measure(quantity, unit, user=None):
    unit_key = str(unit or "").strip()
    amount = _as_decimal(quantity)
    if amount is None:
        return str(quantity), display_unit(unit_key)

    if unit_key in {"kq", "kg", "qram", "ton"}:
        preference = _user_weight_preference(user)
        in_kg = amount
        if unit_key == "qram":
            in_kg = amount / Decimal("1000")
        elif unit_key == "ton":
            in_kg = amount * Decimal("1000")

        if preference == "lb":
            converted = _snap_imperial_display(in_kg * Decimal("2.2046226218"))
            return _format_decimal(converted), _unit_label("lb")
        return _format_decimal(in_kg), _unit_label("kg")

    if unit_key in {"litr", "ml"}:
        preference = _user_volume_preference(user)
        in_liters = amount if unit_key == "litr" else amount / Decimal("1000")
        if preference == "gallon":
            converted = _snap_imperial_display(in_liters / Decimal("3.785411784"))
            return _format_decimal(converted), _unit_label("gallon")
        if unit_key == "ml":
            return _format_decimal(amount), _unit_label("ml")
        return _format_decimal(in_liters), _unit_label("litr")

    return _format_decimal(amount), display_unit(unit_key)


@register.filter
def display_unit(value):
    unit = str(value or "").strip()
    mapping = {
        "kg": "kq",
        "ml": "millilitr",
    }
    return mapping.get(unit, unit)


@register.simple_tag
def display_measure(quantity, unit, user=None):
    value, label = _convert_measure(quantity, unit, user)
    return f"{value} {label}".strip()


@register.simple_tag
def display_quantity(quantity, unit, user=None):
    value, _label = _convert_measure(quantity, unit, user)
    return value


@register.simple_tag
def display_unit_for_user(quantity, unit, user=None):
    _value, label = _convert_measure(quantity, unit, user)
    return label


@register.simple_tag
def unit_system(user=None):
    return _user_weight_preference(user)


@register.simple_tag
def volume_system(user=None):
    return _user_volume_preference(user)


@register.simple_tag
def currency_symbol(user=None):
    return _currency_symbol(_user_currency(user))


@register.simple_tag
def money(amount, user=None, prefix=""):
    currency = _user_currency(user)
    symbol = _currency_symbol(currency)
    converted = _convert_currency(amount, currency)
    if currency == "AZN":
        return f"{prefix}{converted}{symbol}"
    return f"{prefix}{symbol}{converted}"
