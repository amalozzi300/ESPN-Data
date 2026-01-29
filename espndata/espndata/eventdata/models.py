from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from espndata.core.models import League


class Event(models.Model):
    league = models.CharField(max_length=16)
    league_details = models.ForeignKey(League, on_delete=models.CASCADE, related_name='events')
    espn_id = models.CharField(max_length=24)
    date = models.DateField()
    season = models.IntegerField()
    week = models.IntegerField(null=True)
    season_type = models.IntegerField(choices=settings.SEASON_TYPE_CHOICES)
    winning_team = models.CharField(max_length=128, null=True, blank=True)
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
        ordering = ['league', '-espn_id']

    @cached_property
    def league_display(self):
        from espndata.core.models import LeagueDetails

        details = LeagueDetails.objects.get(league=self.league)
        return details.league_display

    def __str__(self):
        return f'{self.league_display} - {self.espn_id}'


class TeamPrediction(models.Model):
    HOME_AWAY_CHOICES = [
        ('home', 'Home'),
        ('away', 'Away'),
        ('neutral', 'Neutral'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='predictions')
    team_name = models.CharField(max_length=128)
    team_rank = models.IntegerField(null=True, blank=True)
    home_away = models.CharField(max_length=8, choices=HOME_AWAY_CHOICES)
    win_probability = models.DecimalField(max_digits=5, decimal_places=2)
    moneyline = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    is_winner = models.BooleanField()
    opponent_name = models.CharField(max_length=128)
    opponent_rank = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'team_name'],
                name='unique_event_team_combination',
            )
        ]
        ordering = ['event__league', 'event__date', '-event__espn_id']

    def __str__(self):
        vs_at = 'vs'

        if self.is_away:
            vs_at = '@'
        
        return f'{self.team_name} {vs_at} {self.opponent_name} ({self.event.date})'
    
    @property
    def is_home(self):
        return self.home_away == 'home'
    
    @property
    def is_away(self):
        return self.home_away == 'away'
    
    @property
    def is_ranked(self):
        return self.team_rank is not None
    
    @property
    def is_opponent_ranked(self):
        return self.opponent_rank is not None


class DataCollectionState(models.Model):
    league = models.OneToOneField(League, on_delete=models.CASCADE, related_name='data_collection_state')
    collection_date = models.DateField()
    event_date = models.DateField(null=True, blank=True)
    season_type = models.IntegerField(choices=settings.SEASON_TYPE_CHOICES)
    week = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.league_details.league_display