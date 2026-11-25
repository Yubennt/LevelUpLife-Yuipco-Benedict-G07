from django.urls import path
from . import views

app_name = 'habits'

urlpatterns = [
    path('', views.habit_list, name='habit_list'),
    path('create/', views.habit_create, name='habit_create'),
    path('<int:pk>/edit/', views.habit_update, name='habit_update'),
    path('<int:pk>/delete/', views.habit_delete, name='habit_delete'),
    path('<int:pk>/toggle/', views.toggle_habit_complete, name='habit_toggle'),
]