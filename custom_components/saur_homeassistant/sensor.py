from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import DOMAIN, WaterConsumptionCoordinator

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WaterConsumptionSensor(coordinator)])

class WaterConsumptionSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: WaterConsumptionCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Water Consumption"
        self._attr_unique_id = f"{DOMAIN}_water_consumption"
        self._attr_native_unit_of_measurement = "m³"
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        return self.coordinator.data["value"] if self.coordinator.data else None