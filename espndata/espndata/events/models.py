from django.db import models


# Run `makemigrations` and `migrate` when you change the _CHOICES dicts
SEASON_TYPE_CHOICES = [
    (2, 'Regular Season'),
    (3, 'Post Season'),
]
CHECK_TYPE_CHOICES = [
    ('weekly', 'Weekly'),
    ('daily', 'Daily'),
]


class LeagueDetails(models.Model):
    espn_name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=32, unique=True)
    sport = models.CharField(max_length=32)
    _check_type = models.CharField(max_length=8, choices=CHECK_TYPE_CHOICES)
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