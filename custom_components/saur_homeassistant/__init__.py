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
import aiohttp
from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

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
    
    coordinator = WaterConsumptionCoordinator(hass, session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    
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
    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, email: str, password: str):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )
        self.session = session
        self.email = email
        self.password = password
        self.access_token = None
        self.section_id = None

    async def _async_update_data(self):
        if not self.access_token:
            await self._authenticate()

        try:
            async with async_timeout.timeout(10):
                today = datetime.now()
                data = await self._fetch_consumption_data(today)
                
                # Si pas de données pour aujourd'hui, essayons hier
                if not data:
                    yesterday = today - timedelta(days=1)
                    data = await self._fetch_consumption_data(yesterday)
                
                if not data:
                    raise UpdateFailed("No consumption data available for today or yesterday")
                
                return data
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout error")
        except (aiohttp.ClientError, aiohttp.ServerDisconnectedError):
            raise UpdateFailed("Error communicating with API")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")

    async def _fetch_consumption_data(self, date):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = await self.session.get(CONSUMPTION_URL.format(
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
            async with async_timeout.timeout(10):
                payload = {
                    "username": self.email,
                    "password": self.password,
                    "client_id": "frontjs-client",
                    "grant_type": "password",
                    "scope": "api-scope",
                    "isRecaptchaV3": True,
                    "captchaToken": True
                }
                response = await self.session.post(AUTH_URL, json=payload)
                response.raise_for_status()
                data = await response.json()
                self.access_token = data["token"]["access_token"]
                self.section_id = data["defaultSectionId"]
        except Exception as err:
            raise UpdateFailed(f"Authentication failed: {err}")