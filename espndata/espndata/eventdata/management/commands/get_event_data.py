from django.conf import settings
from django.core.management import BaseCommand

from dateutil import parser as dateparser
import json
import logging
import requests
import time
from tqdm import tqdm

from espndata.eventdata.models import Event, TeamPrediction
from espndata.core.utils import american_to_decimal
