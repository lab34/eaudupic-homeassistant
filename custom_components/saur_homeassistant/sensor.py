from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import VOLUME_CUBIC_METERS
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

class WaterConsumptionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Water Consumption sensor."""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self._attr_name = f"{config_entry.title} Water Consumption"
        self._attr_unique_id = f"{config_entry.entry_id}_water_consumption"
        self._attr_native_unit_of_measurement = VOLUME_CUBIC_METERS
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
        return {
            "last_period": self.coordinator.data.get("startDate") if self.coordinator.data else None,
            "current_period": self.coordinator.data.get("endDate") if self.coordinator.data else None,
        }