"""Config flow for Lori's Summon."""

from __future__ import annotations

from typing import Any

import voluptuous as vol  # type: ignore

from homeassistant import config_entries  # type: ignore
from homeassistant.const import CONF_NAME  # type: ignore
from homeassistant.data_entry_flow import FlowResult  # type: ignore
from homeassistant.helpers.selector import (  # type: ignore
    ColorRGBSelector,
    EntityFilterSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TargetSelector,
    TargetSelectorConfig,
)

from .const import (
    CONF_ALERT_TITLE,
    CONF_ALIVE_CHECKS_PER_DAY,
    CONF_API_TOKEN,
    CONF_COOLDOWN_SECONDS,
    CONF_DEBUG_LOGGING,
    CONF_ENABLE_WEB,
    CONF_HISTORY_SIZE,
    CONF_LIGHT_FLASH_BRIGHTNESS,
    CONF_LIGHT_FLASH_COLOR,
    CONF_LIGHT_FLASH_COUNT,
    CONF_LIGHT_FLASH_DURATION,
    CONF_LIGHT_TARGET,
    CONF_MAX_TRIGGERS_PER_WINDOW,
    CONF_MESSAGE_TEMPLATE,
    CONF_PUSHOVER_APP_TOKEN,
    CONF_PUSHOVER_DEVICE,
    CONF_PUSHOVER_SOUND_DEFAULT,
    CONF_PUSHOVER_SOUND_EMERGENCY,
    CONF_PUSHOVER_SOUND_LOW,
    CONF_PUSHOVER_SOUND_LOWEST,
    CONF_PUSHOVER_SOUND_NORMAL,
    CONF_PUSHOVER_USER_KEY,
    CONF_RATE_LIMIT_WINDOW_SECONDS,
    CONF_TRIGGER_LIGHTS,
    CONF_WEB_PASSWORD,
    CONF_WEB_USERNAME,
    DEFAULT_ALERT_TITLE,
    DEFAULT_ALIVE_CHECKS_PER_DAY,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_ENABLE_WEB,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_LIGHT_FLASH_BRIGHTNESS,
    DEFAULT_LIGHT_FLASH_COLOR,
    DEFAULT_LIGHT_FLASH_COUNT,
    DEFAULT_LIGHT_FLASH_DURATION,
    DEFAULT_MAX_TRIGGERS_PER_WINDOW,
    DEFAULT_MESSAGE_TEMPLATE,
    DEFAULT_PUSHOVER_APP_TOKEN,
    DEFAULT_PUSHOVER_DEVICE,
    DEFAULT_PUSHOVER_SOUND_DEFAULT,
    DEFAULT_PUSHOVER_SOUND_EMERGENCY,
    DEFAULT_PUSHOVER_SOUND_LOW,
    DEFAULT_PUSHOVER_SOUND_LOWEST,
    DEFAULT_PUSHOVER_SOUND_NORMAL,
    DEFAULT_PUSHOVER_USER_KEY,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    DEFAULT_TRIGGER_LIGHTS,
    DEFAULT_WEB_PASSWORD,
    DEFAULT_WEB_USERNAME,
    DOMAIN,
    ALIVE_SCHEDULE_MAX_PER_DAY,
    ALIVE_SCHEDULE_MIN_PER_DAY,
)


class LorisSummonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lori's Summon."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "LorisSummonOptionsFlowHandler":
        # Reuse the same schema so setup and later edits stay aligned
        return LorisSummonOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        # Keep the integration single-instance because the runtime stores one shared summon state
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input.copy(),
                )

            return self.async_show_form(
                step_id="user",
                errors=errors,
                data_schema=self.add_suggested_values_to_schema(
                    _build_schema(), user_input
                ),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _build_schema(), _defaults(include_name=True)
            ),
        )


class LorisSummonOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Lori's Summon."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        # Start from defaults so newly added options appear when older entries are edited
        suggested = {
            **_defaults(include_name=False),
            **self._config_entry.data,
            **self._config_entry.options,
        }
        # Preserve older web setups when the toggle did not exist yet
        suggested.setdefault(
            CONF_ENABLE_WEB,
            bool(
                str(suggested.get(CONF_WEB_USERNAME, "")).strip()
                and str(suggested.get(CONF_WEB_PASSWORD, "")).strip()
            ),
        )

        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

            suggested.update(user_input)
            return self.async_show_form(
                step_id="init",
                errors=errors,
                data_schema=self.add_suggested_values_to_schema(
                    _build_schema(include_name=False), suggested
                ),
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _build_schema(include_name=False), suggested
            ),
        )


def _build_schema(*, include_name: bool = True) -> vol.Schema:
    # Keep selectors centralized so the setup and options forms stay in lockstep
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Required(CONF_NAME)] = str

    fields[vol.Required(CONF_PUSHOVER_APP_TOKEN)] = str
    fields[vol.Required(CONF_PUSHOVER_USER_KEY)] = str
    fields[vol.Optional(CONF_PUSHOVER_DEVICE)] = str
    fields[vol.Optional(CONF_PUSHOVER_SOUND_LOWEST)] = str
    fields[vol.Optional(CONF_PUSHOVER_SOUND_LOW)] = str
    fields[vol.Optional(CONF_PUSHOVER_SOUND_DEFAULT)] = str
    fields[vol.Optional(CONF_PUSHOVER_SOUND_NORMAL)] = str
    fields[vol.Optional(CONF_PUSHOVER_SOUND_EMERGENCY)] = str
    fields[vol.Optional(CONF_WEB_USERNAME)] = str
    fields[vol.Optional(CONF_WEB_PASSWORD)] = str
    fields[vol.Optional(CONF_ALERT_TITLE)] = str
    fields[vol.Optional(CONF_MESSAGE_TEMPLATE)] = str
    fields[vol.Required(CONF_API_TOKEN)] = str
    fields[vol.Optional(CONF_COOLDOWN_SECONDS)] = NumberSelector(
        NumberSelectorConfig(min=0, max=3600, step=1,
                             mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_RATE_LIMIT_WINDOW_SECONDS)] = NumberSelector(
        NumberSelectorConfig(min=1, max=3600, step=1,
                             mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_MAX_TRIGGERS_PER_WINDOW)] = NumberSelector(
        NumberSelectorConfig(min=1, max=100, step=1,
                             mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_HISTORY_SIZE)] = NumberSelector(
        NumberSelectorConfig(min=5, max=100, step=1,
                             mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_ALIVE_CHECKS_PER_DAY)] = NumberSelector(
        NumberSelectorConfig(
            min=ALIVE_SCHEDULE_MIN_PER_DAY,
            max=ALIVE_SCHEDULE_MAX_PER_DAY,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )
    fields[vol.Optional(CONF_LIGHT_TARGET)] = TargetSelector(
        TargetSelectorConfig(entity=EntityFilterSelectorConfig(domain="light"))
    )
    fields[vol.Optional(CONF_TRIGGER_LIGHTS)] = bool
    fields[vol.Optional(CONF_LIGHT_FLASH_COUNT)] = NumberSelector(
        NumberSelectorConfig(min=1, max=20, step=1,
                             mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_LIGHT_FLASH_BRIGHTNESS)] = NumberSelector(
        NumberSelectorConfig(min=1, max=255, step=1,
                             mode=NumberSelectorMode.SLIDER)
    )
    fields[vol.Optional(CONF_LIGHT_FLASH_DURATION)] = NumberSelector(
        NumberSelectorConfig(min=0.1, max=5, step=0.1,
                             mode=NumberSelectorMode.BOX)
    )
    fields[vol.Optional(CONF_LIGHT_FLASH_COLOR)] = ColorRGBSelector()
    fields[vol.Optional(CONF_ENABLE_WEB)] = bool
    fields[vol.Optional(CONF_DEBUG_LOGGING)] = bool
    return vol.Schema(fields)


def _defaults(*, include_name: bool) -> dict[str, Any]:
    # Keep default values together so the UI and runtime stay consistent
    values: dict[str, Any] = {
        CONF_PUSHOVER_APP_TOKEN: DEFAULT_PUSHOVER_APP_TOKEN,
        CONF_PUSHOVER_USER_KEY: DEFAULT_PUSHOVER_USER_KEY,
        CONF_PUSHOVER_DEVICE: DEFAULT_PUSHOVER_DEVICE,
        CONF_PUSHOVER_SOUND_LOWEST: DEFAULT_PUSHOVER_SOUND_LOWEST,
        CONF_PUSHOVER_SOUND_LOW: DEFAULT_PUSHOVER_SOUND_LOW,
        CONF_PUSHOVER_SOUND_DEFAULT: DEFAULT_PUSHOVER_SOUND_DEFAULT,
        CONF_PUSHOVER_SOUND_NORMAL: DEFAULT_PUSHOVER_SOUND_NORMAL,
        CONF_PUSHOVER_SOUND_EMERGENCY: DEFAULT_PUSHOVER_SOUND_EMERGENCY,
        CONF_WEB_USERNAME: DEFAULT_WEB_USERNAME,
        CONF_WEB_PASSWORD: DEFAULT_WEB_PASSWORD,
        CONF_ALERT_TITLE: DEFAULT_ALERT_TITLE,
        CONF_MESSAGE_TEMPLATE: DEFAULT_MESSAGE_TEMPLATE,
        CONF_API_TOKEN: "",
        CONF_COOLDOWN_SECONDS: DEFAULT_COOLDOWN_SECONDS,
        CONF_RATE_LIMIT_WINDOW_SECONDS: DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        CONF_MAX_TRIGGERS_PER_WINDOW: DEFAULT_MAX_TRIGGERS_PER_WINDOW,
        CONF_HISTORY_SIZE: DEFAULT_HISTORY_SIZE,
        CONF_ALIVE_CHECKS_PER_DAY: DEFAULT_ALIVE_CHECKS_PER_DAY,
        CONF_LIGHT_TARGET: {},
        CONF_TRIGGER_LIGHTS: DEFAULT_TRIGGER_LIGHTS,
        CONF_LIGHT_FLASH_COUNT: DEFAULT_LIGHT_FLASH_COUNT,
        CONF_LIGHT_FLASH_BRIGHTNESS: DEFAULT_LIGHT_FLASH_BRIGHTNESS,
        CONF_LIGHT_FLASH_DURATION: DEFAULT_LIGHT_FLASH_DURATION,
        CONF_LIGHT_FLASH_COLOR: DEFAULT_LIGHT_FLASH_COLOR,
        CONF_ENABLE_WEB: DEFAULT_ENABLE_WEB,
        CONF_DEBUG_LOGGING: DEFAULT_DEBUG_LOGGING,
    }
    if include_name:
        values[CONF_NAME] = "Lori's Summon"
    return values


def _validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    # Validate the minimum runtime requirements before Home Assistant stores the entry
    api_token = str(user_input.get(CONF_API_TOKEN, "")).strip()
    enable_web = bool(user_input.get(CONF_ENABLE_WEB, DEFAULT_ENABLE_WEB))
    pushover_app_token = str(user_input.get(CONF_PUSHOVER_APP_TOKEN, "")).strip()
    pushover_user_key = str(user_input.get(CONF_PUSHOVER_USER_KEY, "")).strip()
    web_username = str(user_input.get(CONF_WEB_USERNAME, "")).strip()
    web_password = str(user_input.get(CONF_WEB_PASSWORD, "")).strip()

    if not api_token:
        return {"base": "api_token_required"}
    if not pushover_app_token:
        return {"base": "pushover_app_token_required"}
    if not pushover_user_key:
        return {"base": "pushover_user_key_required"}
    if enable_web and bool(web_username) != bool(web_password):
        return {"base": "web_auth_incomplete"}
    return {}
