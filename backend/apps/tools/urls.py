from django.urls import path
from . import views

app_name = 'tools'

urlpatterns = [
    path('', views.tool_list, name='tool_list'),
    path('get-items/', views.get_tool_items, name='get_tool_items'),
    path('create/', views.tool_create, name='tool_create'),
    path('update/<int:pk>/', views.tool_update, name='tool_update'),
    path('delete/<int:pk>/', views.tool_delete, name='tool_delete'),
]
