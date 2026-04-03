"""Button entities for Lori's Summon."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore

from .entity import LorisSummonEntity
from .runtime import LorisSummonRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[LorisSummonRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    # Expose manual controls so the summon flow can be tested without external callers
    runtime = entry.runtime_data
    async_add_entities(
        [
            TestActionsButton(runtime),
            AcknowledgeButton(runtime),
            ClearWatchedEmergenciesButton(runtime),
            PurgeSavedSummonsButton(runtime),
        ]
    )


class TestActionsButton(LorisSummonEntity, ButtonEntity):
    """Run a test summon."""

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "test_actions", "Test Actions")

    async def async_press(self) -> None:
        # Run the configured actions without creating a real summon record
        await self.runtime.async_test_actions()


class AcknowledgeButton(LorisSummonEntity, ButtonEntity):
    """Acknowledge all outstanding notifications."""

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "acknowledge", "Acknowledge All")

    async def async_press(self) -> None:
        # Clear the full outstanding set so dashboard acknowledgments also resolve watched emergencies
        await self.runtime.async_acknowledge_all(acknowledged_by="button", source="button")


class ClearWatchedEmergenciesButton(LorisSummonEntity, ButtonEntity):
    """Clear watched emergency events."""

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "clear_watched_emergencies", "Clear Watched Emergencies")

    async def async_press(self) -> None:
        # Stop watching all emergency receipts and cancel their Pushover retry loops
        await self.runtime.async_clear_watched_events()


class PurgeSavedSummonsButton(LorisSummonEntity, ButtonEntity):
    """Purge all saved summon history."""

    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, runtime: LorisSummonRuntime) -> None:
        super().__init__(runtime, "purge_saved_summons", "Purge Saved Summons")

    async def async_press(self) -> None:
        # Remove retained summon history and uploaded files from Home Assistant storage
        await self.runtime.async_purge_saved_summons()
