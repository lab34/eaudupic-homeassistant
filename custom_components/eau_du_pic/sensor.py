from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


class EauDuPicSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Eau du Pic sensor."""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self._attr_name = f"{config_entry.title} Water Consumption"
        self._attr_unique_id = f"{config_entry.entry_id}_water_consumption"
        self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("value")
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        if self.coordinator.data:
            return {
                "last_period": self.coordinator.data.get("startDate"),
                "current_period": self.coordinator.data.get("endDate"),
            }
        return {}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Eau du Pic sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EauDuPicSensor(coordinator, entry)])
