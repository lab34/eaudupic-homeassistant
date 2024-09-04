import logging

DOMAIN = "saur_homeassistant"
_LOGGER = logging.getLogger(__name__)

AUTH_URL = "https://apib2c.azure.saurclient.fr/admin/auth"
CONSUMPTION_URL = "https://apib2c.azure.saurclient.fr/deli/section_subscription/{}/consumptions/weekly?year={}&month={}&day={}"