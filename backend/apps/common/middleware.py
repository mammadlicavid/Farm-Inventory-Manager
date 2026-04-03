from django.utils import translation
from django.utils import timezone
from django.apps import apps
from zoneinfo import ZoneInfo


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.session.get("django_language", "az")
        active_timezone = None

        if getattr(request, "user", None) and request.user.is_authenticated:
            try:
                UserSettings = apps.get_model("sidebar_menu", "UserSettings")
                sidebar_settings = UserSettings.objects.filter(user=request.user).only("language", "timezone").first()
            except Exception:
                sidebar_settings = None
            if sidebar_settings:
                request.user._sidebar_settings_cache = sidebar_settings
                if sidebar_settings.language:
                    language = sidebar_settings.language
                    request.session["django_language"] = language
                if sidebar_settings.timezone:
                    active_timezone = sidebar_settings.timezone

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
        response.set_cookie("django_language", language)
        return response
