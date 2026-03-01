from django.urls import path
from .views import settings_page

app_name = "settings"

urlpatterns = [
    path('', settings_page, name="page"),
]