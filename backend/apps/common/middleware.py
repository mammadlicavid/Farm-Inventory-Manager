from django.utils import translation
from django.utils import timezone
from django.apps import apps
from django.contrib import messages as message_constants
from django.contrib.messages import get_messages
from django.http import JsonResponse
from zoneinfo import ZoneInfo


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.session.get("django_language", "az")
        active_timezone = request.session.get("user_timezone_pref")

        if getattr(request, "user", None) and request.user.is_authenticated:
            cached_language = request.session.get("user_language_pref")
            if cached_language:
                language = cached_language

            # Only query the DB when we haven't resolved settings for this
            # session yet.  A sentinel value "_checked" prevents re-querying
            # when the user simply has no UserSettings row.
            needs_check = (
                not cached_language or active_timezone is None
            ) and not request.session.get("_user_settings_checked")

            if needs_check:
                try:
                    UserSettings = apps.get_model("sidebar_menu", "UserSettings")
                    sidebar_settings = UserSettings.objects.filter(user=request.user).only(
                        "language",
                        "timezone",
                    ).first()
                except Exception:
                    sidebar_settings = None

                if sidebar_settings:
                    request.user._sidebar_settings_cache = sidebar_settings
                    if sidebar_settings.language:
                        language = sidebar_settings.language
                        request.session["django_language"] = language
                        request.session["user_language_pref"] = language
                    if sidebar_settings.timezone:
                        active_timezone = sidebar_settings.timezone
                        request.session["user_timezone_pref"] = active_timezone

                # Mark as checked so we never re-query in this session
                request.session["_user_settings_checked"] = True

        translation.activate(language)
        request.LANGUAGE_CODE = language
        if active_timezone:
            try:
                timezone.activate(ZoneInfo(active_timezone))
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()

        response = self.get_response(request)
        if request.COOKIES.get("django_language") != language:
            response.set_cookie("django_language", language)
        return response


class AjaxRedirectMessageMiddleware:
    """
    Convert AJAX form redirects into small JSON payloads.

    The add/update/delete screens submit via fetch and only need the result
    messages. Letting fetch follow the redirect forces Django to render a full
    page that the browser then parses just to find the toast text.
    """

    REDIRECT_STATUSES = {301, 302, 303, 307, 308}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not self._should_convert(request, response):
            return response

        payload_messages = []
        has_error = False
        for message in get_messages(request):
            tags = str(getattr(message, "tags", "") or "info")
            level = int(getattr(message, "level", message_constants.INFO))
            if level >= message_constants.ERROR or "error" in tags:
                has_error = True
            payload_messages.append(
                {
                    "text": str(message),
                    "tags": tags,
                    "level": level,
                }
            )

        return JsonResponse(
            {
                "ok": not has_error,
                "redirect": response.get("Location", ""),
                "messages": payload_messages,
            },
            status=400 if has_error else 200,
        )

    def _should_convert(self, request, response):
        return (
            request.method != "GET"
            and request.headers.get("x-requested-with") == "XMLHttpRequest"
            and response.status_code in self.REDIRECT_STATUSES
        )
