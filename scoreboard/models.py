from django.conf import settings
from django.db import models


class Match(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches',
        null=True,
        blank=True,
    )


    sport_name = models.CharField(max_length=50)
    team_a = models.CharField(max_length=100)
    team_b = models.CharField(max_length=100)

    score_a = models.IntegerField(default=0)
    score_b = models.IntegerField(default=0)

    winner = models.CharField(max_length=100, blank=True, null=True)
    is_ended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team_a} vs {self.team_b} ({self.sport_name})"
