from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models
from django.utils.functional import cached_property


# Run `makemigrations` and `migrate` when you change the `_CHOICES` dicts
SEASON_TYPE_CHOICES = [
    (2, 'Regular Season'),
    (3, 'Post Season'),
]
CHECK_TYPE_CHOICES = [
    ('weekly', 'Weekly'),
    ('daily', 'Daily'),
]
HOME_AWAY_CHOICES = [
    ('home', 'Home'),
    ('away', 'Away'),
    ('neutral', 'Neutral'),
]


class League(models.Model):
    espn_name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=32, unique=True)
    sport = models.CharField(max_length=32)
    check_type = models.CharField(max_length=8, choices=CHECK_TYPE_CHOICES)
    check_day = models.IntegerField(null=True, blank=True)
    _season_types = models.JSONField(default=dict, blank=True)
    season_start = models.DateField()
    season_end = models.DateField()
    all_star_start = models.DateField(null=True, blank=True)
    all_star_end = models.DateField(null=True, blank=True)
    is_offseason = models.BooleanField()

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    @cached_property
    def season_types(self):
        return {int(s_type): week_list for s_type, week_list in self._season_types.items()}

    def clean(self):
        errors = {}

        if self.check_type == 'weekly':
            if self.check_day is None:
                errors['check_day'] = 'Weekly check leagues must specify a check day.'
            if not self._season_types:
                errors['_season_types'] = 'Weekly check leagues must have a season types JSON configured.'

        if self.season_start >= self.season_end:
            errors['season_start'] = "The season's start date must be before its end date."
            errors['season_end'] = "The season's end date must be after its start date."
        
        if (
            (self.all_star_start and not self.all_star_end)
            or (not self.all_star_start and self.all_star_end)
        ):
            errors['all_star_start'] = 'If there is an All Star break, it must have a start AND end date.'
            errors['all_star_end'] = 'If there is an All Star break, it must have a start AND end date.'
        
        if self.all_star_start and self.all_star_end:
            if self.all_star_start >= self.all_star_end:
                errors['all_star_start'] = "The All Star break's start date must be before its end date."
                errors['all_star_end'] = "The All Star break's end date must be after its start date."
            if not (self.season_start < self.all_star_start < self.all_star_end < self.season_end):
                errors[NON_FIELD_ERRORS] = "The All Star break must be within the season's start and end dates."

        if errors:
            raise ValidationError(errors)

        super().clean()


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Event(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='events')
    espn_id = models.CharField(max_length=24)
    date = models.DateField()
    season = models.IntegerField()
    week = models.IntegerField(null=True)
    season_type = models.IntegerField(choices=SEASON_TYPE_CHOICES)
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

    def __str__(self):
        return f'{self.league.display_name} - {self.espn_id}'


class TeamPrediction(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='predictions')
    team_name = models.CharField(max_length=128)
    team_rank = models.IntegerField(null=True, blank=True)
    home_away = models.CharField(max_length=8, choices=HOME_AWAY_CHOICES)
    win_probability = models.DecimalField(max_digits=5, decimal_places=2)
    moneyline = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    is_winner = models.BooleanField(null=True, blank=True)
    opponent_name = models.CharField(max_length=128)
    opponent_rank = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'team_name'],
                name='unique_event_team_combination',
            )
        ]
        ordering = ['event__league__display_name', 'event__date', '-event__espn_id']

    def __str__(self):
        vs_at = '@' if self.is_away else 'vs'
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