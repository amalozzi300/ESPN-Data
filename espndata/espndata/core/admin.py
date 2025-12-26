from django.contrib import admin

from espndata.core.models import DataCollectionState, LeagueDetails, LeagueNamePair

admin.site.register(DataCollectionState)
admin.site.register(LeagueDetails)
admin.site.register(LeagueNamePair)