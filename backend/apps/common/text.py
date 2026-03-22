def normalize_manual_label(value: str | None) -> str:
    value = " ".join((value or "").strip().split())
    if not value:
        return ""
    return value[:1].upper() + value[1:]
