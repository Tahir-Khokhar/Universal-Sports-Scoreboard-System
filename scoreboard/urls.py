from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_match, name='create_match'),
    path('history/', views.history, name='history'),
    path('match/<int:match_id>/score/<str:team>/', views.update_score, name='update_score'),
    path('match/<int:match_id>/end/', views.end_match, name='end_match'),
]

