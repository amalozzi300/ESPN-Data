from django.conf import settings
from django.db import models

class ProbabilityDataCollectionState(models.Model):
    league = models.CharField(max_length=16, choices=settings.LEAGUE_CHOICES)
    