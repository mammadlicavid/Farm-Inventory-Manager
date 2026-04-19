from django.utils.translation import gettext as _


KNOWN_EXPENSE_PREFIXES = {
    "Toxum alışı",
    "Alət alışı",
    "Heyvan alışı",
    "Texnika alışı",
    "Hazır məhsul alışı",
}

EXPENSE_PREFIX_ALIASES = {
    "toxum alışı": "Toxum alışı",
    "seed purchase": "Toxum alışı",
    "покупка семян": "Toxum alışı",
    "alət alışı": "Alət alışı",
    "tool purchase": "Alət alışı",
    "покупка инструмента": "Alət alışı",
    "heyvan alışı": "Heyvan alışı",
    "animal purchase": "Heyvan alışı",
    "покупка животных": "Heyvan alışı",
    "texnika alışı": "Texnika alışı",
    "equipment purchase": "Texnika alışı",
    "покупка техники": "Texnika alışı",
    "hazır məhsul alışı": "Hazır məhsul alışı",
    "finished product purchase": "Hazır məhsul alışı",
    "покупка готовой продукции": "Hazır məhsul alışı",
}

ITEM_NAME_ALIASES = {
    "alfalfa seed": "Yonca toxumu",
    "семена люцерны": "Yonca toxumu",
    "sugar beet seed": "Şəkər çuğunduru toxumu",
    "семена сахарной свеклы": "Şəkər çuğunduru toxumu",
    "goat": "Keçi",
    "коза": "Keçi",
}


def _translate_value(value: str | None) -> str:
    return _(str(value or "").strip()) if str(value or "").strip() else ""


def _canonical_prefix(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return EXPENSE_PREFIX_ALIASES.get(text.lower(), text)


def _canonical_item_name(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return ITEM_NAME_ALIASES.get(text.lower(), text)


def translate_expense_title(title: str | None) -> str:
    text = str(title or "").strip()
    if not text:
        return ""

    if text.endswith("(Digər)"):
        base = text[:-7].strip()
        canonical_base = _canonical_prefix(base)
        if canonical_base in KNOWN_EXPENSE_PREFIXES:
            return f"{_translate_value(canonical_base)} ({_('Digər')})"

    if ":" in text:
        prefix, suffix = text.split(":", 1)
        prefix = _canonical_prefix(prefix.strip())
        suffix = _canonical_item_name(suffix.strip())
        if prefix in KNOWN_EXPENSE_PREFIXES:
            translated_prefix = _translate_value(prefix)
            if suffix:
                return f"{translated_prefix}: {_translate_value(suffix)}"
            return f"{translated_prefix}:"

    canonical_text = _canonical_prefix(text)
    if canonical_text in KNOWN_EXPENSE_PREFIXES:
        return _translate_value(canonical_text)

    # Legacy farm-product expense titles like "Şaftalı alışı" become the shared format.
    lowered = text.lower()
    if lowered.endswith(" alışı") and ":" not in text:
        item_name = _canonical_item_name(text[:-6].strip())
        if item_name and _canonical_prefix(text) == text:
            return f"{_translate_value('Hazır məhsul alışı')}: {_translate_value(item_name)}"

    return text
