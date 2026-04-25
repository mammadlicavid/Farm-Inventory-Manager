from django.core.cache import cache

from .services import _header_notification_count_cache_key
from .services import get_header_notification_count


def pending_notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    # Read cached count only — never trigger expensive stock-alert computation
    # on every page load.  The real count is refreshed when the dashboard or
    # notification pages are visited.
    cached = cache.get(_header_notification_count_cache_key(user.pk))
    if cached is None:
        cached = get_header_notification_count(user)
    return {
        "pending_notification_count": int(cached) if cached is not None else 0,
    }
