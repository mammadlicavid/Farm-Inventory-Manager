from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def format_currency(amount, decimals: int = 0) -> str:
    """
    Format currency consistently across the app.
    Defaults to 0 decimals to match existing UI (e.g. 1200).
    """
    if amount is None:
        return "0"

    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return "0"

    if decimals <= 0:
        quant = Decimal("1")
        value = value.quantize(quant, rounding=ROUND_HALF_UP)
        return f"{value:.0f}"

    quant = Decimal("1." + ("0" * decimals))
    value = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{value:.{decimals}f}"
