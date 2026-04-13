from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_list, name="list"),
    path("new/", views.reports_form, name="form"),
    path("pdf/", views.reports_pdf, name="pdf"),
]
