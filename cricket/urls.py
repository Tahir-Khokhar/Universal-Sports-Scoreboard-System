from django.urls import path

from . import views

urlpatterns = [
    # Generic match creation lives in the scoreboard app.
    # Keep cricket app URLs focused only on cricket-specific routes.
    # (This path used to refer to a non-existent `cricket.views.create_match`.)

    # history route is handled by the `scoreboard` app (not by cricket.views)


    path('match/create/', views.create_cricket_match, name='create_cricket_match'),
    path('match/<int:match_id>/toss/', views.cricket_toss, name='cricket_toss'),
    path('match/<int:match_id>/toss/save/', views.save_cricket_toss, name='save_cricket_toss'),
    path('match/<int:match_id>/', views.cricket_match_detail, name='cricket_match_detail'),
    path('match/<int:match_id>/state/', views.get_match_state, name='get_match_state'),
    path('match/<int:match_id>/score/', views.add_ball_score, name='add_ball_score'),
    path('match/<int:match_id>/scoreboard/', views.cricket_scoreboard, name='cricket_scoreboard'),
]
