"""Shared entity helpers for Lori's Summon."""

from __future__ import annotations

from homeassistant.core import callback  # type: ignore
from homeassistant.helpers.device_registry import DeviceInfo  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore
from homeassistant.helpers.entity import Entity  # type: ignore

from .const import DISPATCH_STATE_UPDATED, DOMAIN
from .runtime import LorisSummonRuntime


class LorisSummonEntity(Entity):
    """Base entity bound to the shared runtime."""

    _attr_has_entity_name = True

    def __init__(self, runtime: LorisSummonRuntime, key: str, name: str) -> None:
        # Keep entity ids stable because the integration exposes one shared summon device
        self.runtime = runtime
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = name

    @property
    def device_info(self) -> DeviceInfo:
        # Group the helper entities under one device so the summon workflow stays easy to browse
        return DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name=self.runtime.entry.title,
            manufacturer="LouisT",
            model="Summon Workflow",
        )

    async def async_added_to_hass(self) -> None:
        # React to dispatcher updates because runtime state changes are push based
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, DISPATCH_STATE_UPDATED, self._handle_runtime_update)
        )

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self) -> dict:
        return {}

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def _summary(self) -> dict:
        # Read from the runtime snapshot so each entity stays thin
        return self.runtime.state_summary

    @property
    def _active_event(self) -> dict | None:
        return self._summary.get("active_event")

    @property
    def _history_count(self) -> int:
        return int(self._summary.get("history_count") or 0)

    @property
    def _last_event(self) -> dict | None:
        return self._summary.get("last_event")

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()
