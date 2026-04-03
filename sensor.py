"""Sensor entities for Lori's Summon."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.util import dt as dt_util  # type: ignore

from .const import (
    ATTR_ACKNOWLEDGED_AT,
    ATTR_ACKNOWLEDGED_BY,
    ATTR_DISPOSITION,
    ATTR_LAST_TRIGGERED_AT,
    ATTR_MESSAGE,
    ATTR_NEXT_REMINDER_AT,
    ATTR_REMINDER_COUNT,
    ATTR_SOURCE,
    ATTR_TRIGGERED_AT,
)
from .entity import LorisSummonEntity
from .runtime import LorisSummonRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LorisSummonRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    # Expose the latest summon time as a timestamp so automations can build on it
    runtime = entry.runtime_data
    async_add_entities(
        [
            LastSummonSensor(runtime),
            SavedSummonsSensor(runtime),
        ]
    )


class LastSummonSensor(LorisSummonEntity, SensorEntity):
    """Expose the latest summon timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "last_summon", "Last Summon")

    @property
    def native_value(self):
        # Parse the stored ISO timestamp back into a Home Assistant datetime value
        value = self._summary.get(ATTR_LAST_TRIGGERED_AT)
        return dt_util.parse_datetime(value) if value else None

    @property
    def extra_state_attributes(self) -> dict:
        # Surface the latest event and compact history for dashboards and automations
        last_event = self._last_event or {}
        return {
            ATTR_MESSAGE: last_event.get(ATTR_MESSAGE),
            ATTR_SOURCE: last_event.get(ATTR_SOURCE),
            ATTR_DISPOSITION: last_event.get(ATTR_DISPOSITION),
            ATTR_TRIGGERED_AT: last_event.get(ATTR_TRIGGERED_AT),
            ATTR_ACKNOWLEDGED_AT: last_event.get(ATTR_ACKNOWLEDGED_AT),
            ATTR_ACKNOWLEDGED_BY: last_event.get(ATTR_ACKNOWLEDGED_BY),
            ATTR_NEXT_REMINDER_AT: last_event.get(ATTR_NEXT_REMINDER_AT),
            ATTR_REMINDER_COUNT: last_event.get(ATTR_REMINDER_COUNT, 0),
            "history": self._history,
        }


class SavedSummonsSensor(LorisSummonEntity, SensorEntity):
    """Expose the number of saved summons."""

    _attr_icon = "mdi:archive-outline"

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "saved_summons", "Saved Summons")

    @property
    def native_value(self):
        return len(self._history)
