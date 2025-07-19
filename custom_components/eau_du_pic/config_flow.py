import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .api import EauDuPicAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

class EauDuPicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Eau du Pic config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle a flow initiated by the user."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                api = EauDuPicAPI(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
                await api.async_authenticate()
                return self.async_create_entry(title="Eau du Pic", data=user_input)
            except Exception:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )
