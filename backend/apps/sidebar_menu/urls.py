from django.urls import path
from . import views

app_name = 'sidebar_menu'

urlpatterns = [
    path('profil/',             views.profile_view,         name='profile'),
    path('profil/sifre-deyis/', views.change_password_view, name='change_password'),
    path('parametrler/',        views.setting_view,         name='setting'),   # ← renamed
    path('komek/',              views.help_view,             name='help'),
]