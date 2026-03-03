from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tez-xerc/', views.tez_xerc, name='tez_xerc'),
]
