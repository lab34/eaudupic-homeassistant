
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


class EauDuPicDailyDataAvailableSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a sensor to indicate if daily data is available."""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self._attr_name = f"{config_entry.title} Daily Data Available"
        self._attr_unique_id = f"{config_entry.entry_id}_daily_data_available"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self):
        """Return true if the daily data is available."""
        return self.coordinator.data and self.coordinator.data.get("data")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.is_on:
            return {"last_update": self.coordinator.last_update_success_time}
        return {}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Eau du Pic binary sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EauDuPicDailyDataAvailableSensor(coordinator, entry)])
