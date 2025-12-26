from django.contrib import admin

from espndata.core.models import DataCollectionState, LeagueDetails

admin.site.register(DataCollectionState)
admin.site.register(LeagueDetails)