from django.urls import path
from . import views

app_name = 'sidebar_menu'

urlpatterns = [
    path('profile/',                views.profile_view,         name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('settings/',               views.setting_view,         name='setting'),
    path('help/',                   views.help_view,            name='help'),
]
