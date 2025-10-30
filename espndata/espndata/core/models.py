from django.conf import settings
from django.db import models

class DataCollectionState(models.Model):
    league = models.CharField(max_length=16, choices=settings.LEAGUE_CHOICES)
    collected = models.DateField()
    season_start = models.DateField()
    season_end = models.DateField()
    all_star_start = models.DateField()
    all_star_end = models.DateField()
    season_type = models.IntegerField(choices=settings.SEASON_TYPE_CHOICES)
    week = models.IntegerField()