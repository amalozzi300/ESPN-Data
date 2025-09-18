from django.db import models


class Event(models.Model):
    LEAGUE_CHOICES = [
        ('college-football', 'NCAAF'),
        ('nfl', 'NFL'),
        ('nba', 'NBA'),
        ('mlb', 'MLB'),
    ]
    SEASON_TYPE_CHOICES = [
        (2, 'Regular Season'),
        (3, 'Post Season'),
    ]

    league = models.CharField(max_length=16, choices=LEAGUE_CHOICES)
    espn_id = models.CharField(max_length=24)
    date = models.DateField()
    season = models.IntegerField()
    week = models.IntegerField(null=True)
    season_type = models.IntegerField(choices=SEASON_TYPE_CHOICES)
    home_team = models.CharField(max_length=128)
    home_rank = models.IntegerField(null=True)
    home_win_probability = models.DecimalField(max_digits=5, decimal_places=2)
    home_moneyline = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    is_home_win = models.BooleanField(default=False)
    away_team = models.CharField(max_length=128)
    away_rank = models.IntegerField(null=True)
    away_win_probability = models.DecimalField(max_digits=5, decimal_places=2)
    away_moneyline = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    is_away_win = models.BooleanField(default=False)
    is_neutral_site = models.BooleanField(default=False)
    both_ranked_matchup = models.BooleanField(default=False)
    one_ranked_matchup = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['league', 'espn_id'],
                name='unique_league_event_id_combination',
            )
        ]