import logging
from datetime import timedelta, datetime
import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

DOMAIN = "saur_homeassistant"
_LOGGER = logging.getLogger(__name__)

AUTH_URL = "https://apib2c.azure.saurclient.fr/admin/auth"
CONSUMPTION_URL = "https://apib2c.azure.saurclient.fr/deli/section_subscription/{}/consumptions/weekly?year={}&month={}&day={}"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp.ClientSession()
    
    coordinator = WaterConsumptionCoordinator(hass, session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    return True

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Water Consumption component."""
    hass.data.setdefault(DOMAIN, {})
    return True

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
        self.last_update_date = None

    async def _async_update_data(self):
        if not self.access_token:
            await self._authenticate()

        try:
            async with async_timeout.timeout(10):
                today = datetime.now()
                if self.last_update_date != today.date():
                    self.last_update_date = today.date()
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    response = await self.session.get(CONSUMPTION_URL.format(
                        self.section_id, 
                        today.year, 
                        today.month, 
                        today.day
                    ), headers=headers)
                    response.raise_for_status()
                    data = await response.json()
                    return data["consumptions"][0]
                else:
                    return self.data  # Return the last known data if we've already updated today
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

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