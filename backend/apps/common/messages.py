from django.contrib import messages


_ACTION_MESSAGES = {
    "create": "Uğurla əlavə edildi.",
    "update": "Uğurla yeniləndi.",
    "delete": "Uğurla silindi.",
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

