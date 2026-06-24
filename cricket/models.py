from django.db import models
from scoreboard.models import Match


class CricketMatch(models.Model):
    MATCH_TYPES = [
        ('t20', 'T20'),
        ('odi', 'ODI'),
        ('test', 'Test Match'),
    ]

    match = models.OneToOneField(
        Match,
        on_delete=models.CASCADE,      # Delete matches if user is deleted
        related_name='cricket_match'   # Access: user.matches.all()
    )
    match_type = models.CharField(max_length=10, choices=MATCH_TYPES)
    overs = models.IntegerField(null=True, blank=True)  # For limited overs
    is_limited_overs = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.match.team_a} vs {self.match.team_b} - {self.get_match_type_display()}"


class Player(models.Model):
    cricket_match = models.ForeignKey(
        CricketMatch,
        on_delete=models.CASCADE,
        related_name='players'
    )
    name = models.CharField(max_length=100)
    team = models.CharField(max_length=1, choices=[('A', 'Team A'), ('B', 'Team B')])

    # Batting order / categories (used for Test match and for auto replacing striker after wicket)
    batting_order = models.IntegerField(default=0)  # 1..11 (smaller = earlier)
    BAT_CATEGORIES = [
        ('TOP', 'Top Order'),      # Changed to uppercase to match requested format
        ('MIDDLE', 'Middle Order'),
        ('LOWER', 'Lower Order'),
    ]
    batting_category = models.CharField(max_length=20, choices=BAT_CATEGORIES, default='MIDDLE')

    # Role used for bowling lists (bowlers + all-rounders)
    PLAYER_ROLES = [
        ('BATSMAN', 'Batsman'),
        ('BOWLER', 'Bowler'),
        ('ALL_ROUNDER', 'All-rounder'),
    ]
    player_role = models.CharField(max_length=20, choices=PLAYER_ROLES, default='BATSMAN')

    # Batting stats
    runs_scored = models.IntegerField(default=0)
    balls_faced = models.IntegerField(default=0)
    fours = models.IntegerField(default=0)
    sixes = models.IntegerField(default=0)
    is_out = models.BooleanField(default=False)
    out_type = models.CharField(max_length=20, blank=True, null=True)
    out_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='out_to_players'
    )
    out_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='out_by_players'
    )

    # Bowling stats
    balls_bowled = models.IntegerField(default=0)
    runs_conceded = models.IntegerField(default=0)
    wickets_taken = models.IntegerField(default=0)
    maidens = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.team})"


class Innings(models.Model):
    cricket_match = models.ForeignKey(
        CricketMatch,
        on_delete=models.CASCADE,
        related_name='innings'
    )
    innings_number = models.IntegerField()
    team_batting = models.CharField(
        max_length=1,
        choices=[('A', 'Team A'), ('B', 'Team B')],
        default='A'
    )
    total_runs = models.IntegerField(default=0)
    overs_bowled = models.IntegerField(default=0)
    balls_bowled = models.IntegerField(default=0)
    target_runs = models.IntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cricket_match', 'innings_number']

    def __str__(self):
        return f"Innings {self.innings_number} - {self.team_batting}"


class Ball(models.Model):
    EXTRA_TYPES = [
        ('none', 'None'),
        ('wide', 'Wide'),
        ('no_ball', 'No Ball'),
        ('bye', 'Bye'),
        ('leg_bye', 'Leg Bye'),
    ]

    innings = models.ForeignKey(Innings, on_delete=models.CASCADE, related_name='balls')
    batsman = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='batsman_balls')
    non_striker = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='non_striker_balls')
    bowler = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='bowler_balls')
    runs = models.IntegerField()
    extras = models.CharField(max_length=20, choices=EXTRA_TYPES, default='none')
    is_wicket = models.BooleanField(default=False)
    wicket_type = models.CharField(max_length=20, blank=True, null=True)
    fielder = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fielder_balls'
    )
    ball_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ball {self.ball_number}: {self.batsman.name} - {self.runs} runs"
