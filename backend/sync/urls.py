from django.urls import path
from . import views

app_name = "sync"

urlpatterns = [
    path("", views.sync_page, name="page"),
    path("status/", views.sync_status, name="status"),
    path("pull-status/", views.sync_pull_status, name="pull_status"),
    path("push/", views.sync_push, name="push"),
]
