"""Binary sensors for Lori's Summon."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .const import (
    ATTR_COOLDOWN_UNTIL,
    ATTR_EVENT_ID,
    ATTR_MESSAGE,
    ATTR_NEXT_REMINDER_AT,
    ATTR_PENDING_ACK,
    ATTR_RATE_LIMITED_UNTIL,
    ATTR_REMINDER_COUNT,
    ATTR_SOURCE,
)
from .entity import LorisSummonEntity
from .runtime import LorisSummonRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LorisSummonRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    # Expose whether any tracked notifications still need attention from Pushover or Home Assistant
    runtime = entry.runtime_data
    async_add_entities([PendingAcknowledgmentBinarySensor(runtime)])


class PendingAcknowledgmentBinarySensor(LorisSummonEntity, BinarySensorEntity):
    """Show whether any tracked notifications still need acknowledgment."""

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "pending_ack", "Outstanding Notifications")

    @property
    def is_on(self) -> bool:
        # Mirror the runtime attention flag directly so the entity stays on for any outstanding emergency
        return bool(self._summary.get(ATTR_PENDING_ACK))

    @property
    def extra_state_attributes(self) -> dict:
        # Include the primary outstanding event context so the binary sensor is useful on its own
        active = self._active_event or {}
        return {
            ATTR_EVENT_ID: active.get(ATTR_EVENT_ID),
            ATTR_MESSAGE: active.get(ATTR_MESSAGE),
            ATTR_NEXT_REMINDER_AT: active.get(ATTR_NEXT_REMINDER_AT),
            ATTR_SOURCE: active.get(ATTR_SOURCE),
            ATTR_REMINDER_COUNT: active.get(ATTR_REMINDER_COUNT, 0),
            ATTR_COOLDOWN_UNTIL: self._summary.get(ATTR_COOLDOWN_UNTIL),
            ATTR_RATE_LIMITED_UNTIL: self._summary.get(ATTR_RATE_LIMITED_UNTIL),
        }
