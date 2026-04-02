from django.contrib import messages
from django.utils.translation import gettext_lazy as _

_ACTION_MESSAGES = {
    "create": _("Uğurla əlavə edildi."),
    "update": _("Uğurla yeniləndi."),
    "delete": _("Uğurla silindi."),
}


def add_crud_success_message(request, entity: str, action: str) -> None:
    """
    Add a standardized success message for CRUD operations.

    Messages are short, professional, and in Azerbaijani, for example:
    - "Uğurla əlavə edildi."
    - "Uğurla yeniləndi."
    - "Uğurla silindi."
    """
    message = _ACTION_MESSAGES.get(action)
    if not message:
        raise ValueError(f"Unsupported action '{action}'. Use one of: {', '.join(_ACTION_MESSAGES)}.")

    messages.success(request, message)
