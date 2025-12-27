from django.urls import path

from espndata.core import views

urlpatterns = [
    path('', views.Home.as_view(), name='home')
]
