import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EauDuPicAPI
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD

_LOGGER = logging.getLogger(__name__)


class EauDuPicDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching data from the Eau du Pic API."""

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        self.api = EauDuPicAPI(email, password)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self):
        """Fetch data from API. This is the place to handle authentication and data retrieval."""
        try:
            # Ensure we are authenticated before fetching data
            if not self.api.token:
                await self.api.async_authenticate()
            
            # Get contract ID
            contract_id = await self.api.async_get_contract_id()

            # Fetch consumption data
            # We will fetch data for the last 7 days to ensure we get the latest daily reading
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            daily_data = await self.api.async_get_daily_consumption_data(contract_id, start_date, end_date)

            if not daily_data or not daily_data.get("data"):
                raise UpdateFailed("No daily consumption data available.")

            # Find the latest daily consumption
            latest_reading = None
            latest_date = None

            for entry in daily_data["data"]:
                if entry["type"] == "PORLV_Teleconso":
                    reading_date_str = entry["attributes"]["dateni"]
                    reading_date = datetime.fromisoformat(reading_date_str.replace(" 00:00:00", ""))
                    if latest_date is None or reading_date > latest_date:
                        latest_date = reading_date
                        latest_reading = entry["attributes"]["ni"]
            
            if latest_reading is None:
                raise UpdateFailed("No valid daily consumption reading found.")

            return {
                "value": latest_reading,
                "startDate": latest_date.strftime("%Y-%m-%d"),
                "endDate": latest_date.strftime("%Y-%m-%d"),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eau du Pic from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = EauDuPicDataUpdateCoordinator(
        hass,
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
