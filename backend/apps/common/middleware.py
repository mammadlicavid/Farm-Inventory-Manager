from django.utils import translation
from django.utils import timezone
from django.apps import apps
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

            if not cached_language or active_timezone is None:
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
                        request.session["user_language_pref"] = language
                    if sidebar_settings.timezone:
                        active_timezone = sidebar_settings.timezone
                        request.session["user_timezone_pref"] = active_timezone

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
