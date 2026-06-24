from django.conf import settings
from django.db import models

# Model for other sport like football
class Match(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # References the User model
        on_delete=models.CASCADE,  # Delete matches if user is deleted
        related_name='matches',    # Access: user.matches.all()
        null=True,                 # Database can store NULL
        blank=True,                # Forms can leave this empty
    )


    sport_name = models.CharField(max_length=50)
    team_a = models.CharField(max_length=100)
    team_b = models.CharField(max_length=100)

    # Venue details (stadium + city) for match header UI
    venue_stadium_name = models.CharField(max_length=200, blank=True, null=True)
    venue_city = models.CharField(max_length=200, blank=True, null=True)



    score_a = models.IntegerField(default=0)
    score_b = models.IntegerField(default=0)

    winner = models.CharField(max_length=100, blank=True, null=True)
    is_ended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team_a} vs {self.team_b} ({self.sport_name})"



