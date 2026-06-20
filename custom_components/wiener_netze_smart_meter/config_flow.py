from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from wiener_netze_smart_meter_api import WNAPIClient
from wiener_netze_smart_meter_api.exceptions import WNAPIAuthenticationError

from .const import CONF_API_KEY, CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_API_KEY): str,
    }
)


def _validate(client_id: str, client_secret: str, api_key: str) -> None:
    client = WNAPIClient(client_id=client_id, client_secret=client_secret, api_key=api_key)
    client.get_anlagendaten()


class WNSmartMeterConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match({CONF_CLIENT_ID: user_input[CONF_CLIENT_ID]})
            try:
                await self.hass.async_add_executor_job(
                    _validate,
                    user_input[CONF_CLIENT_ID],
                    user_input[CONF_CLIENT_SECRET],
                    user_input[CONF_API_KEY],
                )
            except WNAPIAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Wiener Netze Smart Meter",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
