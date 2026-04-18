from django.utils.translation import gettext as _


KNOWN_EXPENSE_PREFIXES = {
    "Toxum alışı",
    "Alət alışı",
    "Heyvan alışı",
    "Texnika alışı",
    "Hazır məhsul alışı",
}


def translate_expense_title(title: str | None) -> str:
    text = str(title or "").strip()
    if not text:
        return ""

    if text.endswith("(Digər)"):
        base = text[:-7].strip()
        if base in KNOWN_EXPENSE_PREFIXES:
            return f"{_(base)} ({_('Digər')})"

    if ":" in text:
        prefix, suffix = text.split(":", 1)
        prefix = prefix.strip()
        suffix = suffix.strip()
        if prefix in KNOWN_EXPENSE_PREFIXES and suffix:
            return f"{_(prefix)}: {suffix}"

    if text in KNOWN_EXPENSE_PREFIXES:
        return str(_(text))

    return text
