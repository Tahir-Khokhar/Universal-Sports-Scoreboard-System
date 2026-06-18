from django.contrib import admin
from .models import Match


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "sport_name", "team_a", "team_b", "score_a", "score_b", "winner", "is_ended", "created_at")
    list_filter = ("sport_name", "is_ended", "created_at")
    search_fields = ("team_a", "team_b")

