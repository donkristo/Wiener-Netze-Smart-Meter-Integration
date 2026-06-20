from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WNSmartMeterCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: WNSmartMeterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DailyEnergySensor(coordinator, zaehlpunkt) for zaehlpunkt in coordinator.data
    )


class DailyEnergySensor(CoordinatorEntity[WNSmartMeterCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_has_entity_name = True
    _attr_name = "Daily energy"

    def __init__(self, coordinator: WNSmartMeterCoordinator, zaehlpunkt: str) -> None:
        super().__init__(coordinator)
        self._zaehlpunkt = zaehlpunkt
        self._attr_unique_id = f"{zaehlpunkt}_daily_energy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, zaehlpunkt)},
            name=f"Smart meter {zaehlpunkt[-6:]}",
            manufacturer="Wiener Netze",
        )

    @property
    def native_value(self) -> float | None:
        reading = self.coordinator.data.get(self._zaehlpunkt)
        return reading.daily_wh if reading else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        reading = self.coordinator.data.get(self._zaehlpunkt)
        return {"reading_date": reading.reading_date} if reading else {}

    @property
    def last_reset(self):
        reading = self.coordinator.data.get(self._zaehlpunkt)
        if not reading:
            return None
        day = datetime.strptime(reading.reading_date, "%Y-%m-%d")
        return day - timedelta(days=1)
