from django.core.cache import cache
from django.utils import timezone


USER_VIEW_BUST_TTL = 60 * 60 * 24 * 30


def _user_view_bust_key(scope: str, user_id: int) -> str:
    return f"ui-bust:{scope}:v1:{user_id}"


def get_user_view_bust_value(scope: str, user_id: int) -> str:
    return str(cache.get(_user_view_bust_key(scope, user_id), "0"))


def bust_user_view_scope(scope: str, user_id: int) -> None:
    cache.set(_user_view_bust_key(scope, user_id), timezone.now().isoformat(), USER_VIEW_BUST_TTL)


def get_dashboard_bust_value(user_id: int) -> str:
    return get_user_view_bust_value("dashboard", user_id)


def get_calendar_bust_value(user_id: int) -> str:
    return get_user_view_bust_value("calendar", user_id)


def get_reports_bust_value(user_id: int) -> str:
    return get_user_view_bust_value("reports", user_id)


def bust_dashboard_related_caches(user_id: int) -> None:
    bust_user_view_scope("dashboard", user_id)
    bust_user_view_scope("calendar", user_id)
    bust_user_view_scope("reports", user_id)
    from notifications.services import invalidate_notification_header_count_cache

    invalidate_notification_header_count_cache(user_id)
