import logging
from datetime import timedelta, datetime
import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

import asyncio
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from homeassistant.util import dt as dt_util
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

DOMAIN = "saur_homeassistant"
_LOGGER = logging.getLogger(__name__)

AUTH_URL = "https://apib2c.azure.saurclient.fr/admin/auth"
CONSUMPTION_URL = "https://apib2c.azure.saurclient.fr/deli/section_subscription/{}/consumptions/weekly?year={}&month={}&day={}"
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp.ClientSession()
    
    coordinator = WaterConsumptionCoordinator(
        hass,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD]
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    return True

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Water Consumption component."""
    conf = config.get(DOMAIN)
    hass.data.setdefault(DOMAIN, {})

    if conf is not None:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
            )
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["sensor"]):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
    
class WaterConsumptionCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, email, password):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),  # Mise à jour toutes les 15 minutes
        )
        self.hass = hass
        self.email = email
        self.password = password
        self.access_token = None
        self.section_id = None
        self.token_expiration = None

    async def _async_update_data(self):
        # Refresh the token if it's expired or doesn't exist
        if self._is_token_expired():
            await self._authenticate()

        try:
            async with asyncio.timeout(10):
                today = dt_util.now()
                data = await self._fetch_consumption_data(today)
                
                # Si pas de données pour aujourd'hui, essayer hier
                if not data:
                    yesterday = today - timedelta(days=1)
                    data = await self._fetch_consumption_data(yesterday)
                
                # Si toujours pas de données, essayer les 7 derniers jours
                if not data:
                    for i in range(2, 8):  # De 2 à 7 jours en arrière
                        past_date = today - timedelta(days=i)
                        data = await self._fetch_consumption_data(past_date)
                        if data:
                            break
                
                if not data:
                    raise UpdateFailed("Aucune donnée de consommation disponible sur les 7 derniers jours")
                
                return data
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout error")
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")

    async def _fetch_consumption_data(self, date):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        session = async_get_clientsession(self.hass)
        response = await session.get(CONSUMPTION_URL.format(
            self.section_id, 
            date.year, 
            date.month, 
            date.day
        ), headers=headers)
        response.raise_for_status()
        data = await response.json()
        
        if "consumptions" in data and data["consumptions"]:
            return data["consumptions"][0]
        return None

    async def _authenticate(self):
        try:
            async with asyncio.timeout(10):
                payload = {
                    "username": self.email,
                    "password": self.password,
                    "client_id": "frontjs-client",
                    "grant_type": "password",
                    "scope": "api-scope",
                    "isRecaptchaV3": True,
                    "captchaToken": True
                }
                session = async_get_clientsession(self.hass)
                response = await session.post(AUTH_URL, json=payload)
                response.raise_for_status()
                data = await response.json()
                self.access_token = data["token"]["access_token"]
                self.section_id = data["defaultSectionId"]
                expires_in = int(data["token"]["expires_in"])
                self.token_expiration = dt_util.utcnow() + timedelta(seconds=expires_in)
                _LOGGER.info(f"Token will expire at {self.token_expiration}")
        except Exception as err:
            raise UpdateFailed(f"Authentication failed: {err}")

    def _is_token_expired(self):
        # Check if token is expired or doesn't exist
        if not self.access_token or not self.token_expiration:
            return True
        # Check if current time is past the expiration time
        return dt_util.utcnow() >= self.token_expiration