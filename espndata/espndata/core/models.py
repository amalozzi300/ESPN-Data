from django.conf import settings
from django.db import models

class LeagueDetails(models.Model):
    espn_name = models.CharField(max_length=16, unique=True)
    display_name = models.CharField(max_length=16, unique=True)
    sport = models.CharField(max_length=16)
    _check_type = models.CharField(max_length=8, choices=settings.CHECK_TYPE_CHOICES)
    check_day = models.IntegerField(null=True, blank=True)
    _season_types = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['display_name']
        verbose_name = 'League Details'
        verbose_name_plural = 'League Details'


    @property
    def check_type(self):
        return self.get__check_type_display()

    @property
    def season_types(self):
        return {int(s_type): week_list for s_type, week_list in self._season_types.items()}

    def __str__(self):
        return self.display_name