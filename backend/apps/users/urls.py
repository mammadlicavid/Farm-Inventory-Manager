# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("process_login/", views.process_login, name="process_login"),
    path("logout/", views.logout_view, name="logout"),

    path("signup/", views.signup_page, name="signup"),
    path("process_signup/", views.process_signup, name="process_signup"),
]




