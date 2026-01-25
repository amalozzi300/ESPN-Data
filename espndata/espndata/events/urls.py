from django.urls import path

from espndata.events import views

urlpatterns = [
    path('', views.Homepage.as_view(), name='home'),
]
