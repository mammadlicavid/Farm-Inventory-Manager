from .services import get_header_notification_count


def pending_notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {
        "pending_notification_count": get_header_notification_count(user),
    }
