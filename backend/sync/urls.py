from django.urls import path
from . import views

app_name = "sync"

urlpatterns = [
    path("", views.sync_page, name="page"),
]