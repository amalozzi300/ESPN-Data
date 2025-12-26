from django.conf import settings
from django.db import models

class LeagueDetails(models.Model):
    league = models.CharField(max_length=16)
    league_display = models.CharField(max_length=16)
    sport = models.CharField(max_length=16)
    check_type = models.CharField(max_length=8, choices=settings.CHECK_TYPE_CHOICES)
    check_day = models.IntegerField(null=True, blank=True)
    season_types = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.league_display

class DataCollectionState(models.Model):
    league_details = models.OneToOneField(LeagueDetails, on_delete=models.CASCADE, related_name='data_collection_state')
    collected = models.DateField()
    season_start = models.DateField()
    season_end = models.DateField()
    is_offseason = models.BooleanField()
    all_star_start = models.DateField(null=True, blank=True)
    all_star_end = models.DateField(null=True, blank=True)
    season_type = models.IntegerField(choices=settings.SEASON_TYPE_CHOICES)
    week = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.league_details.league_display