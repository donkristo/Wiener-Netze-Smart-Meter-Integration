from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from wiener_netze_smart_meter_api import WNAPIClient
from wiener_netze_smart_meter_api.exceptions import WNAPIAuthenticationError

from .const import DOMAIN, UPDATE_INTERVAL_HOURS
from .logic import MeterReading, latest_daily_reading

_LOGGER = logging.getLogger(__name__)


class WNSmartMeterCoordinator(DataUpdateCoordinator[dict[str, MeterReading]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: WNAPIClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict[str, MeterReading]:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except WNAPIAuthenticationError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err

    def _fetch(self) -> dict[str, MeterReading]:
        anlagen = self.client.get_anlagendaten()
        if isinstance(anlagen, dict):
            anlagen = [anlagen]

        readings: dict[str, MeterReading] = {}
        for anlage in anlagen or []:
            zaehlpunkt = anlage.get("zaehlpunktnummer")
            if not zaehlpunkt:
                continue
            reading = latest_daily_reading(self.client, zaehlpunkt)
            if reading:
                readings[zaehlpunkt] = reading
        return readings
