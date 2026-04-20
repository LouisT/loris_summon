"""Runtime helpers for Lori's Summon."""

from __future__ import annotations

import asyncio
import base64
import dataclasses
from collections.abc import Callable
from datetime import datetime, time, timedelta
import html
import hashlib
import hmac
from io import BytesIO
from itertools import chain
import json
import logging
import mimetypes
import os
import random
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from aiohttp import FormData  # type: ignore
from PIL import Image, UnidentifiedImageError  # type: ignore

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.exceptions import HomeAssistantError  # type: ignore
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore
from homeassistant.helpers.event import async_track_point_in_time  # type: ignore
from homeassistant.helpers.storage import Store  # type: ignore
from homeassistant.helpers.template import Template  # type: ignore
from homeassistant.util import dt as dt_util  # type: ignore

from .const import (
    ALIVE_CHECK_MESSAGE,
    ALIVE_CHECK_TITLE,
    ALIVE_SCHEDULE_MAX_PER_DAY,
    ALIVE_SCHEDULE_MIN_PER_DAY,
    ALIVE_SOURCE_MANUAL,
    ALIVE_SOURCE_SCHEDULE,
    ATTACHMENT_FILE_PATH,
    ATTR_ACKNOWLEDGED_AT,
    ATTR_ACKNOWLEDGED_BY,
    ATTR_ACTIVE,
    ATTR_ATTACHMENT_PATH,
    ATTR_COOLDOWN_UNTIL,
    ATTR_DISPOSITION,
    ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS,
    ATTR_EVENT_ID,
    ATTR_EVENT_KIND,
    ATTR_HISTORY,
    ATTR_LAST_TRIGGERED_AT,
    ATTR_MESSAGE,
    ATTR_NEXT_REMINDER_AT,
    ATTR_PENDING_ACK,
    ATTR_PRIORITY,
    ATTR_PUSHOVER_ACKNOWLEDGED,
    ATTR_PUSHOVER_ACKNOWLEDGED_AT,
    ATTR_PUSHOVER_ACKNOWLEDGED_BY,
    ATTR_PUSHOVER_ACKNOWLEDGED_BY_DEVICE,
    ATTR_PUSHOVER_EXPIRED,
    ATTR_PUSHOVER_EXPIRES_AT,
    ATTR_PUSHOVER_LAST_DELIVERED_AT,
    ATTR_PUSHOVER_RECEIPT,
    ATTR_PUSHOVER_TITLE,
    ATTR_RATE_LIMITED_UNTIL,
    ATTR_REMINDER_COUNT,
    ATTR_SOURCE,
    ATTR_TRIGGERED_AT,
    ATTR_VOICE_NOTE_BASE_URL,
    ATTR_VOICE_NOTE_PATH,
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
    DEFAULT_PUSHOVER_EMERGENCY_EXPIRE,
    DEFAULT_PUSHOVER_EMERGENCY_RETRY,
    DEFAULT_PUSHOVER_SOUND_DEFAULT,
    DEFAULT_PUSHOVER_SOUND_EMERGENCY,
    DEFAULT_PUSHOVER_SOUND_LOW,
    DEFAULT_PUSHOVER_SOUND_LOWEST,
    DEFAULT_PUSHOVER_SOUND_NORMAL,
    DEFAULT_PUSHOVER_USER_KEY,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    DEFAULT_SUMMON_MESSAGE,
    DEFAULT_SUMMON_PRIORITY,
    DEFAULT_TRIGGER_LIGHTS,
    DEFAULT_WEB_PASSWORD,
    DEFAULT_WEB_USERNAME,
    DISPATCH_STATE_UPDATED,
    DOMAIN,
    EVENT_KIND_ALIVE,
    EVENT_ACKNOWLEDGED,
    EVENT_TRIGGERED,
    ICON_PATH,
    PUSHOVER_CALLBACK_PATH,
    PUSHOVER_PRIORITY_DEFAULT,
    PUSHOVER_PRIORITY_EMERGENCY,
    PUSHOVER_PRIORITY_LOW,
    PUSHOVER_PRIORITY_LOWEST,
    PUSHOVER_PRIORITY_NORMAL,
    VOICE_NOTE_FILE_PATH,
    VOICE_NOTE_PLAY_PATH,
    WEB_PATH,
    STORE_ALIVE_ACTIVE_EVENT_ID,
    STORE_ALIVE_HISTORY,
    STORE_ALIVE_SCHEDULE,
    STORE_ALIVE_WATCHED_EVENTS,
    STORE_WEB_PUSH_SUBSCRIPTIONS,
    STORE_WEB_PUSH_VAPID_PRIVATE,
    STORE_WEB_PUSH_VAPID_PUBLIC,
    WEB_PUSH_KEYS_DIR_NAME,
    WEB_PUSH_MAX_SUBSCRIPTIONS,
    WEB_PUSH_VAPID_PRIVATE_FILENAME,
    WEB_PUSH_VAPID_PUBLIC_FILENAME,
    WEB_PUSH_VAPID_SUB,
)

_LOGGER = logging.getLogger(__name__)

RESTORE_BASE_ATTRS = ("brightness", "effect")
RESTORE_COLOR_ATTRS = (
    "rgbww_color",
    "rgbw_color",
    "rgb_color",
    "hs_color",
    "xy_color",
    "color_temp_kelvin",
    "color_temp",
    "white",
)
LIGHT_RESTORE_RETRIES = 5
LIGHT_RESTORE_RETRY_DELAY = 0.5
REMINDER_INTERVAL_SECONDS = 300
STORE_VERSION = 1
STORE_ACTIVE_EVENT_ID = "active_event_id"
STORE_WATCHED_EVENTS = "watched_events"
SUMMARY_ACTIVE_EVENT = "active_event"
SUMMARY_HISTORY_COUNT = "history_count"
SUMMARY_LAST_EVENT = "last_event"
SUMMARY_MATCHING_EVENT = "matching_event"
SUMMARY_WATCHED_EVENTS = "watched_events"
WEB_JWT_MAX_AGE_SECONDS = 604800
WEB_JWT_REFRESH_WINDOW_SECONDS = 43200
ATTACHMENT_UPLOAD_MAX_BYTES = 26_214_400
VOICE_NOTE_MAX_BYTES = 78_643_200
IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".3gp", ".avi", ".m4v", ".mov", ".mp4", ".mpeg", ".mpg", ".ogv", ".webm"}
VOICE_NOTE_SUFFIXES = {".aac", ".m4a", ".mp3", ".mp4", ".oga", ".ogg", ".opus", ".wav", ".weba", ".webm"}
PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_RECEIPT_CANCEL_URL = "https://api.pushover.net/1/receipts/{receipt}/cancel.json"
PRIORITY_VALUE_MAP = {
    PUSHOVER_PRIORITY_LOWEST: -2,
    PUSHOVER_PRIORITY_LOW: -1,
    PUSHOVER_PRIORITY_DEFAULT: 0,
    PUSHOVER_PRIORITY_NORMAL: 1,
    PUSHOVER_PRIORITY_EMERGENCY: 2,
}
PRIORITY_ALIASES = {
    "-2": PUSHOVER_PRIORITY_LOWEST,
    "-1": PUSHOVER_PRIORITY_LOW,
    "0": PUSHOVER_PRIORITY_DEFAULT,
    "1": PUSHOVER_PRIORITY_NORMAL,
    "2": PUSHOVER_PRIORITY_EMERGENCY,
    "default": PUSHOVER_PRIORITY_DEFAULT,
    "emergency": PUSHOVER_PRIORITY_EMERGENCY,
    "low": PUSHOVER_PRIORITY_LOW,
    "lowest": PUSHOVER_PRIORITY_LOWEST,
    "normal": PUSHOVER_PRIORITY_DEFAULT,
    "high": PUSHOVER_PRIORITY_NORMAL,
}


@dataclasses.dataclass(slots=True)
class LightSnapshot:
    # Preserve the original light state so flashing can be reversed safely
    entity_id: str
    state: str
    attributes: dict[str, Any]


def _jwt_b64encode(data: bytes) -> str:
    # Encode JWT segments without padding so the token stays URL safe
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _jwt_b64decode(segment: str) -> bytes:
    # Restore missing padding because JWT omits it by design
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(f"{segment}{padding}")


def _normalize_priority(priority: Any) -> str | None:
    # Accept both labels and numeric inputs so every surface can use one shared mapping
    value = str(priority).strip().lower()
    if not value:
        return DEFAULT_SUMMON_PRIORITY
    return PRIORITY_ALIASES.get(value)


def _looks_like_image(filename: str, mime_type: str | None) -> bool:
    normalized_mime_type = _normalized_upload_mime_type(mime_type)
    if normalized_mime_type and normalized_mime_type.startswith("image/"):
        return True
    return Path(filename).suffix.lower() in IMAGE_SUFFIXES


def _looks_like_video(filename: str, mime_type: str | None) -> bool:
    normalized_mime_type = _normalized_upload_mime_type(mime_type)
    if normalized_mime_type and normalized_mime_type.startswith("video/"):
        return True
    return Path(filename).suffix.lower() in VIDEO_SUFFIXES


def _normalized_upload_mime_type(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    normalized = mime_type.split(";", 1)[0].strip().lower()
    return normalized or None


def _looks_like_voice_note(filename: str, mime_type: str | None) -> bool:
    normalized_mime_type = _normalized_upload_mime_type(mime_type)
    if normalized_mime_type and normalized_mime_type.startswith("audio/"):
        return True
    return Path(filename).suffix.lower() in VOICE_NOTE_SUFFIXES


def _attachment_kind(filename: str, mime_type: str | None) -> str | None:
    if _looks_like_image(filename, mime_type):
        return "image"
    if _looks_like_video(filename, mime_type):
        return "video"
    return None


def _normalize_attachment_upload(
    filename: str,
    data: bytes,
    mime_type: str | None,
) -> tuple[str, bytes]:
    # Validate uploaded images and videos while preserving the original file for history previews and downloads
    if not data:
        raise ValueError("attachment is empty")
    kind = _attachment_kind(filename, mime_type)
    if kind is None:
        raise ValueError("attachment is not a supported image or video")
    if len(data) > ATTACHMENT_UPLOAD_MAX_BYTES:
        raise ValueError("attachment exceeds the 25 MB upload limit")
    if kind == "image":
        try:
            with Image.open(BytesIO(data)) as image:
                image.verify()
        except (OSError, UnidentifiedImageError, ValueError) as err:
            raise ValueError("attachment is not a supported image or video") from err
    normalized_mime_type = _normalized_upload_mime_type(mime_type)
    suffix = (
        Path(filename).suffix.lower()
        or mimetypes.guess_extension(normalized_mime_type or "")
        or (".png" if kind == "image" else ".mp4")
    )
    return f"{Path(filename).stem or 'attachment'}{suffix}", data


def _normalize_voice_note_upload(
    filename: str,
    data: bytes,
    mime_type: str | None,
) -> tuple[str, bytes]:
    # Validate recorded audio uploads before persisting them for later playback
    if len(data) > VOICE_NOTE_MAX_BYTES:
        raise ValueError("voice note exceeds the 75 MB upload limit")
    if not data:
        raise ValueError("voice note is empty")
    if not _looks_like_voice_note(filename, mime_type):
        raise ValueError("voice note is not a supported audio file")
    normalized_mime_type = _normalized_upload_mime_type(mime_type)
    suffix = (
        Path(filename).suffix.lower()
        or mimetypes.guess_extension(normalized_mime_type or "")
        or ".webm"
    )
    return f"{Path(filename).stem or 'voice_note'}{suffix}", data


@dataclasses.dataclass(slots=True)
class TriggerResult:
    # Carry the trigger outcome through HTTP and browser response helpers
    accepted: bool
    disposition: str
    message: str
    source: str
    priority: str | None = None
    event_id: str | None = None
    cooldown_until: str | None = None
    rate_limited_until: str | None = None


class LorisSummonRuntime:
    """Own the configured notification, throttling, and state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        # Keep runtime-only state in memory and persist only the summon history
        self.hass = hass
        self.entry = entry
        self._store = Store[dict[str, Any]](
            hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.state"
        )
        self._history: list[dict[str, Any]] = []
        self._active_event_id: str | None = None
        self._last_trigger_at: datetime | None = None
        self._recent_trigger_times: list[datetime] = []
        self._reminder_task: asyncio.Task[None] | None = None
        self._watched_events: dict[str, dict[str, Any]] = {}
        self._alive_history: list[dict[str, Any]] = []
        self._alive_active_event_id: str | None = None
        self._alive_watched_events: dict[str, dict[str, Any]] = {}
        self._alive_schedule_unsubs: list[Callable[[], None]] = []
        self._alive_schedule_blob: dict[str, Any] = {}
        self._web_push_vapid_private_pem: str | None = None
        self._web_push_vapid_public_b64u: str | None = None
        self._web_push_subscriptions: list[dict[str, Any]] = []

    async def async_initialize(self) -> None:
        # Restore persisted summon state so entities survive Home Assistant restarts
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            stored = {}

        history = stored.get(ATTR_HISTORY, [])
        if isinstance(history, list):
            self._history = [
                dict(item) for item in history if isinstance(item, dict)
            ][: self._history_size()]

        watched_events = stored.get(STORE_WATCHED_EVENTS, [])
        if isinstance(watched_events, list):
            self._watched_events = {}
            for item in watched_events:
                if not isinstance(item, dict):
                    continue
                event_id = str(item.get(ATTR_EVENT_ID) or "").strip()
                if not event_id:
                    continue
                history_item = next(
                    (
                        record
                        for record in self._history
                        if str(record.get(ATTR_EVENT_ID) or "") == event_id
                    ),
                    None,
                )
                self._watched_events[event_id] = history_item if history_item is not None else dict(item)

        self._active_event_id = stored.get(STORE_ACTIVE_EVENT_ID)
        last_triggered = stored.get(ATTR_LAST_TRIGGERED_AT)
        if isinstance(last_triggered, str):
            self._last_trigger_at = dt_util.parse_datetime(last_triggered)

        alive_history = stored.get(STORE_ALIVE_HISTORY, [])
        if isinstance(alive_history, list):
            self._alive_history = [
                self._normalize_loaded_alive_item(dict(item))
                for item in alive_history
                if isinstance(item, dict)
            ][: self._history_size()]

        self._alive_active_event_id = stored.get(STORE_ALIVE_ACTIVE_EVENT_ID)
        if not isinstance(self._alive_active_event_id, str):
            self._alive_active_event_id = None
        else:
            self._alive_active_event_id = self._alive_active_event_id.strip() or None

        alive_watched = stored.get(STORE_ALIVE_WATCHED_EVENTS, [])
        if isinstance(alive_watched, list):
            self._alive_watched_events = {}
            for item in alive_watched:
                if not isinstance(item, dict):
                    continue
                event_id = str(item.get(ATTR_EVENT_ID) or "").strip()
                if not event_id:
                    continue
                normalized_item = self._normalize_loaded_alive_item(dict(item))
                history_item = next(
                    (
                        record
                        for record in self._alive_history
                        if str(record.get(ATTR_EVENT_ID) or "") == event_id
                    ),
                    None,
                )
                self._alive_watched_events[event_id] = (
                    history_item if history_item is not None else normalized_item
                )

        schedule_blob = stored.get(STORE_ALIVE_SCHEDULE)
        if isinstance(schedule_blob, dict):
            self._alive_schedule_blob = dict(schedule_blob)

        subs = stored.get(STORE_WEB_PUSH_SUBSCRIPTIONS, [])
        if isinstance(subs, list):
            self._web_push_subscriptions = [
                dict(s) for s in subs if isinstance(s, dict)
            ][:WEB_PUSH_MAX_SUBSCRIPTIONS]

        await self._async_init_web_push_vapid(stored)

        self._debug(
            "restored %s history items with active event %s",
            len(self._history),
            self._active_event_id,
        )
        restored_outstanding = self._restore_outstanding_state()
        restored_alive = self._restore_alive_outstanding_state()
        if restored_outstanding or restored_alive:
            await self._async_save_state()
        self._notify_state_changed()
        self._ensure_alive_schedule()

    async def async_trigger(
        self,
        message: str,
        source: str = "external",
        priority: Any = None,
        attachment_path: str | None = None,
        voice_note_path: str | None = None,
        voice_note_base_url: str | None = None,
    ) -> TriggerResult:
        now = dt_util.utcnow()
        # Reuse the same admission checks everywhere so the web UI and API agree on throttling
        preview = self._preview_trigger(message, source, now, priority)
        if not preview.accepted:
            return preview
        cleaned_message = preview.message
        cleaned_source = preview.source
        cleaned_priority = preview.priority or DEFAULT_SUMMON_PRIORITY

        entry = self._create_history_entry(
            cleaned_message,
            cleaned_source,
            cleaned_priority,
            attachment_path,
            voice_note_path,
            voice_note_base_url,
            now,
        )
        payload = dict(entry)
        payload[ATTR_PENDING_ACK] = cleaned_priority == PUSHOVER_PRIORITY_EMERGENCY
        delivery_metadata = await self._send_notification(payload)
        entry.update(delivery_metadata)
        payload.update(delivery_metadata)
        requires_attention = self._event_requires_attention(entry)

        self._history.insert(0, entry)
        if requires_attention:
            self._supersede_previous_active(entry[ATTR_EVENT_ID])
            entry[ATTR_ACTIVE] = True
            self._active_event_id = entry[ATTR_EVENT_ID]
            self._watched_events[entry[ATTR_EVENT_ID]] = entry
        else:
            self._finalize_delivered_event(entry)
        payload[ATTR_ACTIVE] = entry[ATTR_ACTIVE]
        payload[ATTR_DISPOSITION] = entry[ATTR_DISPOSITION]
        payload[ATTR_PENDING_ACK] = requires_attention
        self._trim_history_entries()
        self._last_trigger_at = now
        self._recent_trigger_times.append(now)
        self._trim_recent_triggers(now)
        if self._lights_enabled():
            self.hass.async_create_task(self._async_flash_lights_safely())

        self.hass.bus.async_fire(EVENT_TRIGGERED, payload)
        await self._async_commit_state()
        self._debug("accepted summon %s from %s",
                    entry[ATTR_EVENT_ID], cleaned_source)
        return TriggerResult(
            accepted=True,
            disposition="triggered",
            message=cleaned_message,
            source=cleaned_source,
            priority=cleaned_priority,
            event_id=entry[ATTR_EVENT_ID],
        )

    def preview_trigger(
        self,
        message: str,
        source: str = "external",
        priority: Any = None,
    ) -> TriggerResult:
        # Let fast request paths check whether a summon would be accepted without waiting on slow actions
        return self._preview_trigger(message, source, dt_util.utcnow(), priority)

    async def async_test_actions(
        self,
        message: str = "Test summon",
        priority: Any = None,
        attachment_path: str | None = None,
        voice_note_path: str | None = None,
    ) -> TriggerResult:
        # Exercise notification and light actions without mutating summon history
        normalized_priority = _normalize_priority(
            priority) or DEFAULT_SUMMON_PRIORITY
        payload = {
            ATTR_EVENT_ID: "test",
            ATTR_MESSAGE: message.strip(),
            ATTR_PRIORITY: normalized_priority,
            ATTR_SOURCE: "test",
            ATTR_TRIGGERED_AT: dt_util.utcnow().isoformat(),
            ATTR_PENDING_ACK: False,
        }
        if attachment_path:
            payload[ATTR_ATTACHMENT_PATH] = attachment_path
        if voice_note_path:
            payload[ATTR_VOICE_NOTE_PATH] = voice_note_path
        await self._send_notification(payload)
        if self._lights_enabled():
            await self._flash_lights()
        self._debug("ran test actions")
        return TriggerResult(
            True,
            "test",
            payload[ATTR_MESSAGE],
            "test",
            priority=normalized_priority,
            event_id="test",
        )

    async def async_acknowledge(
        self,
        acknowledged_by: str = "service",
        source: str = "service",
        *,
        cancel_receipt: bool = True,
    ) -> dict[str, Any]:
        # Update the live record so persisted history and entities stay consistent
        active = self._active_event_record()
        if active is None:
            return {"acknowledged": False, "reason": "no_active_summon"}

        if cancel_receipt:
            await self._async_cancel_active_receipt(active)

        now = dt_util.utcnow().isoformat()
        self._apply_local_acknowledgment(active, acknowledged_by, now)
        self._active_event_id = None
        self._cancel_reminder_task()
        self._watched_events.pop(str(active.get(ATTR_EVENT_ID) or ""), None)
        payload = dict(active)
        payload[ATTR_SOURCE] = source
        self.hass.bus.async_fire(EVENT_ACKNOWLEDGED, payload)
        await self._async_commit_state()
        self._debug("acknowledged summon %s from %s",
                    active[ATTR_EVENT_ID], source)
        return {
            "acknowledged": True,
            "event_id": active[ATTR_EVENT_ID],
            "acknowledged_at": now,
        }

    async def async_acknowledge_all(
        self,
        acknowledged_by: str = "service",
        source: str = "service",
        *,
        cancel_receipts: bool = True,
    ) -> dict[str, Any]:
        # Acknowledge the active summon and any still-watched emergencies in one pass
        outstanding_events = self._outstanding_events()
        if not outstanding_events:
            return {"acknowledged": False, "reason": "no_outstanding_summons", "count": 0}

        now = dt_util.utcnow().isoformat()
        event_ids: list[str] = []
        for event in outstanding_events:
            if cancel_receipts:
                await self._async_cancel_active_receipt(event)
            self._apply_local_acknowledgment(event, acknowledged_by, now)
            payload = dict(event)
            payload[ATTR_SOURCE] = source
            self.hass.bus.async_fire(EVENT_ACKNOWLEDGED, payload)
            event_ids.append(str(event.get(ATTR_EVENT_ID) or ""))

        self._active_event_id = None
        self._cancel_reminder_task()
        self._watched_events.clear()
        await self._async_commit_state()
        self._debug(
            "acknowledged %s outstanding summons from %s",
            len(event_ids),
            source,
        )
        return {
            "acknowledged": True,
            "count": len(event_ids),
            "event_ids": event_ids,
            "acknowledged_at": now,
        }

    async def async_handle_pushover_callback(self, data: dict[str, Any]) -> dict[str, Any]:
        # Apply Pushover emergency callback data to summons or alive checks that created the receipt
        receipt = str(data.get("receipt", "")).strip()
        if not receipt:
            return {"ok": False, "reason": "missing_receipt"}

        event = self._watched_event_by_receipt(receipt)
        if event is None:
            event = self._alive_watched_event_by_receipt(receipt)
        is_alive = self._is_alive_event(event) if event is not None else False
        was_watched = False
        if event is not None:
            event_id = str(event.get(ATTR_EVENT_ID) or "").strip()
            if is_alive:
                was_watched = event_id in self._alive_watched_events
            else:
                was_watched = event_id in self._watched_events
        if event is None:
            # Accept callbacks for known cleared events so Pushover does not keep retrying them
            event = self._event_by_receipt(receipt)
            if event is None:
                event = self._alive_event_by_receipt(receipt)
            if event is None:
                return {"ok": False, "reason": "unknown_receipt"}
            is_alive = self._is_alive_event(event)

        prev_expired = bool(event.get(ATTR_PUSHOVER_EXPIRED))
        self._apply_pushover_callback_data(event, data)
        if str(data.get("acknowledged", "0")).strip() != "1":
            expired_now = bool(event.get(ATTR_PUSHOVER_EXPIRED)) and not prev_expired
            if expired_now:
                await self._async_finalize_emergency_expired(event, is_alive=is_alive)
            else:
                await self._async_commit_state()
            return {"ok": True, "receipt": receipt, "acknowledged": False}

        acknowledged_by = str(
            data.get("acknowledged_by_device")
            or data.get("acknowledged_by")
            or "pushover"
        ).strip() or "pushover"
        now = dt_util.utcnow().isoformat()
        event[ATTR_ACKNOWLEDGED_AT] = now
        event[ATTR_ACKNOWLEDGED_BY] = acknowledged_by
        event[ATTR_ACTIVE] = False
        event[ATTR_NEXT_REMINDER_AT] = None
        self._set_acknowledgment_duration(
            event,
            str(event.get(ATTR_PUSHOVER_ACKNOWLEDGED_AT) or "").strip() or now,
        )
        if event.get(ATTR_DISPOSITION) != "cancelled":
            event[ATTR_DISPOSITION] = "acknowledged"
        event_id = str(event.get(ATTR_EVENT_ID) or "")
        if is_alive:
            if event_id == str(self._alive_active_event_id or ""):
                self._alive_active_event_id = None
            self._alive_watched_events.pop(event_id, None)
        else:
            if event_id == str(self._active_event_id or ""):
                self._active_event_id = None
                self._cancel_reminder_task()
            self._watched_events.pop(event_id, None)
        if was_watched and not is_alive:
            payload = dict(event)
            payload[ATTR_SOURCE] = "pushover_callback"
            self.hass.bus.async_fire(EVENT_ACKNOWLEDGED, payload)
        await self._async_commit_state()
        return {
            "ok": True,
            "receipt": receipt,
            "acknowledged": True,
        }

    @property
    def active_event(self) -> dict[str, Any] | None:
        # Return the primary outstanding emergency so dashboards still surface receipts that need attention
        active = self._primary_outstanding_event_record()
        return dict(active) if active else None

    @property
    def state_summary(self) -> dict[str, Any]:
        # Keep entity-facing state compact; rich history stays available through the browser API only
        active = self.active_event
        last_event = dict(self._history[0]) if self._history else None
        return {
            ATTR_LAST_TRIGGERED_AT: (
                self._last_trigger_at.isoformat() if self._last_trigger_at else None
            ),
            ATTR_PENDING_ACK: bool(self._outstanding_events()),
            ATTR_COOLDOWN_UNTIL: self._cooldown_until_iso(),
            ATTR_RATE_LIMITED_UNTIL: self._rate_limited_until_iso(),
            SUMMARY_ACTIVE_EVENT: active,
            SUMMARY_HISTORY_COUNT: len(self._history),
            SUMMARY_LAST_EVENT: last_event,
            SUMMARY_WATCHED_EVENTS: [dict(item) for item in self._watched_events.values()],
        }

    def browser_status(self, event_id: str | None = None) -> dict[str, Any]:
        # Include watched and recent records so the browser can reconcile SSE removals without polling
        matching = (
            self._watched_event(event_id) or self._event_record(event_id)
        ) if event_id else None
        return {
            ATTR_PENDING_ACK: bool(self._outstanding_events()),
            ATTR_HISTORY: [dict(item) for item in self._history],
            SUMMARY_ACTIVE_EVENT: self.active_event,
            SUMMARY_MATCHING_EVENT: dict(matching) if matching else None,
            SUMMARY_WATCHED_EVENTS: [dict(item) for item in self._watched_events.values()],
            "alive_history": [dict(item) for item in self._alive_history],
            "alive_active_event": self._alive_active_event_record_public(),
            "alive_watched_events": [
                dict(item) for item in self._alive_watched_events.values()
            ],
            "alive_schedule_per_day": self._alive_checks_per_day(),
            "alive_schedule_day": str(self._alive_schedule_blob.get("day") or ""),
            "alive_schedule_slots": self._alive_schedule_slots_for_status(),
            "web_push": {
                "subscription_count": len(self._web_push_subscriptions),
                "max_subscriptions": WEB_PUSH_MAX_SUBSCRIPTIONS,
            },
        }

    def alive_checks_browser_page(self) -> dict[str, Any]:
        return {
            "items": [self._alive_check_browser_item(item) for item in self._alive_history],
            "alive_schedule_day": str(self._alive_schedule_blob.get("day") or ""),
            "alive_schedule_slots": self._alive_schedule_slots_for_status(),
        }

    async def async_send_alive_check(self, source: str) -> dict[str, Any]:
        now = dt_util.utcnow()
        entry = self._create_history_entry(
            ALIVE_CHECK_MESSAGE,
            source,
            PUSHOVER_PRIORITY_EMERGENCY,
            None,
            None,
            None,
            now,
        )
        entry[ATTR_EVENT_KIND] = EVENT_KIND_ALIVE
        entry[ATTR_PUSHOVER_TITLE] = ALIVE_CHECK_TITLE
        try:
            delivery_metadata = await self._send_notification(entry)
        except Exception as err:
            _LOGGER.warning("Alive check Pushover delivery failed: %s", err)
            return {"ok": False, "error": str(err)}
        entry.update(delivery_metadata)
        requires_attention = self._event_requires_attention(entry)
        self._alive_history.insert(0, entry)
        event_id = str(entry.get(ATTR_EVENT_ID) or "")
        if requires_attention:
            self._supersede_previous_alive_active(event_id)
            entry[ATTR_ACTIVE] = True
            self._alive_active_event_id = event_id
            self._alive_watched_events[event_id] = entry
        else:
            self._finalize_alive_delivered_event(entry)
        entry[ATTR_ACTIVE] = bool(entry.get(ATTR_ACTIVE))
        self._trim_alive_history()
        await self._async_commit_state()
        self._notify_state_changed()
        return {"ok": True, "event_id": event_id}

    async def async_delete_alive_check(self, event_id: str) -> dict[str, Any]:
        eid = str(event_id or "").strip()
        if not eid:
            return {"ok": False, "reason": "missing_event_id"}
        event = self._alive_event_record(eid)
        if event is None:
            return {"ok": False, "reason": "not_found"}
        if (
            bool(event.get(ATTR_ACTIVE))
            or str(self._alive_active_event_id or "") == eid
            or eid in self._alive_watched_events
        ):
            return {"ok": False, "reason": "active_alive_check"}
        self._alive_history = [
            item
            for item in self._alive_history
            if str(item.get(ATTR_EVENT_ID) or "").strip() != eid
        ]
        self._alive_watched_events.pop(eid, None)
        if str(self._alive_active_event_id or "") == eid:
            self._alive_active_event_id = None
        self._delete_attachment_file(event.get(ATTR_ATTACHMENT_PATH))
        self._delete_attachment_file(event.get(ATTR_VOICE_NOTE_PATH))
        await self._async_commit_state()
        self._notify_state_changed()
        return {"ok": True, "event_id": eid}

    async def async_flush_alive_history(self) -> dict[str, Any]:
        to_cancel = [
            dict(e)
            for e in self._alive_watched_events.values()
            if self._event_requires_attention(e)
        ]
        for event in to_cancel:
            await self._async_cancel_active_receipt(event)
        attachment_paths: set[str] = set()
        voice_note_paths: set[str] = set()
        for item in self._alive_history:
            ap = str(item.get(ATTR_ATTACHMENT_PATH) or "").strip()
            vn = str(item.get(ATTR_VOICE_NOTE_PATH) or "").strip()
            if ap:
                attachment_paths.add(ap)
            if vn:
                voice_note_paths.add(vn)
        removed = len(self._alive_history)
        self._alive_watched_events.clear()
        self._alive_active_event_id = None
        self._alive_history = []
        for path in attachment_paths | voice_note_paths:
            self._delete_attachment_file(path)
        await self._async_commit_state()
        self._notify_state_changed()
        return {"ok": True, "removed": removed}

    @staticmethod
    def _alive_seconds_to_ack_value(seconds: Any) -> int | None:
        try:
            value = int(seconds)
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    def _alive_check_browser_item(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event.get(ATTR_EVENT_ID) or "").strip()
        ack_at = (
            str(event.get(ATTR_PUSHOVER_ACKNOWLEDGED_AT) or "").strip()
            or str(event.get(ATTR_ACKNOWLEDGED_AT) or "").strip()
        )
        return {
            "event_id": event_id,
            "triggered_at": event.get(ATTR_TRIGGERED_AT),
            "acknowledged_at": ack_at or None,
            "seconds_to_ack": self._alive_seconds_to_ack_value(
                event.get(ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS)
            ),
            "pending": self._event_requires_attention(event),
            "source": str(event.get(ATTR_SOURCE) or ""),
        }

    def _is_alive_event(self, event: dict[str, Any] | None) -> bool:
        if event is None:
            return False
        if str(event.get(ATTR_EVENT_KIND) or "") == EVENT_KIND_ALIVE:
            return True
        source = str(event.get(ATTR_SOURCE) or "")
        return source in {ALIVE_SOURCE_MANUAL, ALIVE_SOURCE_SCHEDULE} or source.startswith(
            "alive_"
        )

    def _normalize_loaded_alive_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if self._is_alive_event(item):
            item.setdefault(ATTR_EVENT_KIND, EVENT_KIND_ALIVE)
        return item

    def _alive_active_event_record(self) -> dict[str, Any] | None:
        if not self._alive_active_event_id:
            return None
        return next(
            (
                item
                for item in self._alive_history
                if item.get(ATTR_EVENT_ID) == self._alive_active_event_id
            ),
            None,
        )

    def _alive_active_event_record_public(self) -> dict[str, Any] | None:
        active = self._alive_active_event_record()
        return dict(active) if active else None

    def _alive_watched_event_by_receipt(self, receipt: str) -> dict[str, Any] | None:
        watched_receipt = str(receipt or "").strip()
        if not watched_receipt:
            return None
        return next(
            (
                item
                for item in self._alive_watched_events.values()
                if str(item.get(ATTR_PUSHOVER_RECEIPT) or "") == watched_receipt
            ),
            None,
        )

    def _alive_event_by_receipt(self, receipt: str) -> dict[str, Any] | None:
        watched_receipt = str(receipt or "").strip()
        if not watched_receipt:
            return None
        return next(
            (
                item
                for item in self._alive_history
                if str(item.get(ATTR_PUSHOVER_RECEIPT) or "") == watched_receipt
            ),
            None,
        )

    def _alive_event_record(self, event_id: str) -> dict[str, Any] | None:
        eid = str(event_id or "").strip()
        if not eid:
            return None
        for item in self._alive_history:
            if str(item.get(ATTR_EVENT_ID) or "").strip() == eid:
                return item
        return None

    def _supersede_previous_alive_active(self, new_event_id: str) -> None:
        active = self._alive_active_event_record()
        if active is None or str(active.get(ATTR_EVENT_ID) or "") == new_event_id:
            return
        active[ATTR_ACTIVE] = False
        active[ATTR_NEXT_REMINDER_AT] = None
        if active.get(ATTR_DISPOSITION) == "triggered":
            active[ATTR_DISPOSITION] = "superseded"

    def _finalize_alive_delivered_event(self, event: dict[str, Any]) -> bool:
        return self._finalize_delivered_event(event)

    def _trim_alive_history(self) -> None:
        max_items = self._history_size()
        watched_ids = set(self._alive_watched_events)
        kept: list[dict[str, Any]] = []
        non_watched_kept = 0
        for item in self._alive_history:
            event_id = str(item.get(ATTR_EVENT_ID) or "")
            if event_id in watched_ids:
                kept.append(item)
                continue
            if non_watched_kept < max_items:
                kept.append(item)
                non_watched_kept += 1
        self._alive_history = kept

    def _restore_alive_outstanding_state(self) -> bool:
        state_changed = False
        watched_events: dict[str, dict[str, Any]] = {}
        for event_id, event in self._alive_watched_events.items():
            if self._event_requires_attention(event):
                watched_events[event_id] = event
                continue
            state_changed = self._finalize_alive_delivered_event(event) or state_changed
        if watched_events != self._alive_watched_events:
            self._alive_watched_events = watched_events
            state_changed = True
        active = self._alive_active_event_record()
        if active is None:
            if self._alive_active_event_id is not None:
                self._alive_active_event_id = None
                state_changed = True
            return state_changed
        if self._event_requires_attention(active):
            event_id = str(active.get(ATTR_EVENT_ID) or "").strip()
            if event_id and event_id not in self._alive_watched_events:
                self._alive_watched_events[event_id] = active
                state_changed = True
            return state_changed
        state_changed = self._finalize_alive_delivered_event(active) or state_changed
        if self._alive_active_event_id is not None:
            self._alive_active_event_id = None
            state_changed = True
        return state_changed

    def _cancel_alive_schedule_handles(self) -> None:
        for unsub in self._alive_schedule_unsubs:
            try:
                unsub()
            except Exception:  # noqa: BLE001
                pass
        self._alive_schedule_unsubs.clear()

    def _time_zone(self):
        return dt_util.get_time_zone(self.hass.config.time_zone) or dt_util.UTC

    def _alive_schedule_target_local_date(self) -> datetime:
        tz = self._time_zone()
        now_local = dt_util.now(tz)
        end_window = datetime.combine(now_local.date(), time(22, 30), tzinfo=tz)
        if now_local > end_window:
            return datetime.combine(
                now_local.date() + timedelta(days=1), time(0, 0), tzinfo=tz
            )
        return datetime.combine(now_local.date(), time(0, 0), tzinfo=tz)

    def _alive_schedule_day_key(self, day_anchor: datetime) -> str:
        return day_anchor.date().isoformat()

    def _alive_schedule_slots_for_status(self) -> list[dict[str, Any]]:
        """Return today's scheduled alive times for the browser (Home Assistant local time)."""
        slots_raw = self._alive_schedule_blob.get("slots")
        if not isinstance(slots_raw, list):
            return []
        tz = self._time_zone()
        out: list[dict[str, Any]] = []
        for slot in slots_raw:
            if not isinstance(slot, dict):
                continue
            when = dt_util.parse_datetime(str(slot.get("at") or "").strip())
            if when is None:
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt_util.UTC)
            local_when = when.astimezone(tz)
            hour12 = local_when.strftime("%I").lstrip("0") or "12"
            minute = local_when.strftime("%M")
            ampm = local_when.strftime("%p").lower()
            local_label = f"{hour12}:{minute} {ampm}"
            out.append(
                {
                    "at": when.isoformat(),
                    "fired": bool(slot.get("fired")),
                    "local_time": local_label,
                }
            )
        out.sort(key=lambda x: x["at"])
        return out

    def _build_new_alive_schedule(self, day_anchor: datetime, tz) -> dict[str, Any]:
        target_date = day_anchor.date()
        start_local = datetime.combine(target_date, time(8, 30), tzinfo=tz)
        end_local = datetime.combine(target_date, time(22, 30), tzinfo=tz)
        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(end_local)
        span = max(0, int((end_utc - start_utc).total_seconds()))
        per_day = self._alive_checks_per_day()
        if span <= 0:
            fire_times = [start_utc] * per_day
        else:
            pool = span + 1
            sample_n = min(per_day, pool)
            offsets = sorted(random.sample(range(pool), sample_n))
            fire_times = [start_utc + timedelta(seconds=int(o)) for o in offsets]
        slots = [{"at": t.isoformat(), "fired": False} for t in fire_times]
        return {
            "day": target_date.isoformat(),
            "slots": slots,
            "scheduled_per_day": per_day,
        }

    def _ensure_alive_schedule(self) -> None:
        if not self.hass.is_running:
            return
        self._cancel_alive_schedule_handles()
        tz = self._time_zone()
        day_anchor = self._alive_schedule_target_local_date()
        day_key = self._alive_schedule_day_key(day_anchor)
        want = self._alive_checks_per_day()
        slots = self._alive_schedule_blob.get("slots")
        stored_per = self._alive_schedule_blob.get("scheduled_per_day")
        if stored_per is None and isinstance(slots, list):
            stored_per = len(slots)
        if (
            self._alive_schedule_blob.get("day") != day_key
            or not isinstance(slots, list)
            or len(slots) != want
            or stored_per != want
        ):
            self._alive_schedule_blob = self._build_new_alive_schedule(day_anchor, tz)
            self.hass.async_create_task(self._async_commit_state())
        slots_list = self._alive_schedule_blob.get("slots")
        if not isinstance(slots_list, list):
            return
        now_utc = dt_util.utcnow()
        for index, slot in enumerate(slots_list):
            if not isinstance(slot, dict) or slot.get("fired"):
                continue
            when = dt_util.parse_datetime(str(slot.get("at") or "").strip())
            if when is None or when <= now_utc:
                continue

            async def _fire_scheduled_alive(_now: datetime, idx: int = index) -> None:
                await self._async_fire_alive_schedule_slot(idx)

            unsub = async_track_point_in_time(self.hass, _fire_scheduled_alive, when)
            self._alive_schedule_unsubs.append(unsub)

    async def _async_fire_alive_schedule_slot(self, slot_index: int) -> None:
        slots_raw = self._alive_schedule_blob.get("slots")
        if not isinstance(slots_raw, list) or slot_index < 0 or slot_index >= len(slots_raw):
            return
        slot = slots_raw[slot_index]
        if not isinstance(slot, dict) or slot.get("fired"):
            return
        result = await self.async_send_alive_check(ALIVE_SOURCE_SCHEDULE)
        if result.get("ok"):
            slot["fired"] = True
            await self._async_commit_state()
        self._ensure_alive_schedule()

    async def _async_finalize_emergency_expired(
        self,
        event: dict[str, Any],
        *,
        is_alive: bool,
    ) -> None:
        # Pushover ended the emergency retry window without an acknowledgment
        event[ATTR_ACTIVE] = False
        event[ATTR_NEXT_REMINDER_AT] = None
        if str(event.get(ATTR_DISPOSITION) or "").strip() == "triggered":
            event[ATTR_DISPOSITION] = "expired"
        event_id = str(event.get(ATTR_EVENT_ID) or "")
        if is_alive:
            if event_id == str(self._alive_active_event_id or ""):
                self._alive_active_event_id = None
            self._alive_watched_events.pop(event_id, None)
        else:
            if event_id == str(self._active_event_id or ""):
                self._active_event_id = None
                self._cancel_reminder_task()
            self._watched_events.pop(event_id, None)
        await self._async_send_web_push_missing_ack(event, is_alive=is_alive)
        await self._async_commit_state()
        self._notify_state_changed()

    async def _async_send_web_push_missing_ack(
        self,
        event: dict[str, Any],
        *,
        is_alive: bool,
    ) -> None:
        try:
            import pywebpush  # noqa: F401
        except ImportError:
            self._debug("pywebpush is not installed; skipping web push")
            return
        if not self._web_push_subscriptions:
            return
        if not self._web_push_vapid_private_pem:
            if not await self.async_ensure_web_push_vapid_keys():
                return
        private_pem = self._web_push_vapid_private_pem
        if not private_pem:
            return
        event_id = str(event.get(ATTR_EVENT_ID) or "").strip()
        title = (
            "Alive check not acknowledged"
            if is_alive
            else "Emergency summon not acknowledged"
        )
        if is_alive:
            body = (
                "The Pushover emergency window ended with no acknowledgment for an Alive Check."
            )
        else:
            msg_preview = str(event.get(ATTR_MESSAGE) or "").strip().replace("\n", " ")
            if len(msg_preview) > 120:
                msg_preview = f"{msg_preview[:117]}..."
            body = (
                "The Pushover emergency window ended with no acknowledgment."
                + (f' Summon: "{msg_preview}"' if msg_preview else "")
            )
        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "path": f"{WEB_PATH}#{'alive' if is_alive else 'sent-summons'}",
                "tag": f"loris-{event_id}-{'alive' if is_alive else 'summon'}",
                "icon": ICON_PATH,
            },
            separators=(",", ":"),
        )
        dead_endpoints: set[str] = set()
        for sub in list(self._web_push_subscriptions):
            endpoint = str(sub.get("endpoint") or "").strip()
            if not endpoint:
                continue
            result = await self.hass.async_add_executor_job(
                _web_push_send_sync,
                sub,
                payload,
                private_pem,
                WEB_PUSH_VAPID_SUB,
            )
            if result == "gone":
                dead_endpoints.add(endpoint)
        if dead_endpoints:
            self._web_push_subscriptions = [
                s
                for s in self._web_push_subscriptions
                if str(s.get("endpoint") or "").strip() not in dead_endpoints
            ]
            await self._async_save_state()

    async def async_ensure_web_push_vapid_keys(self) -> bool:
        if self._web_push_vapid_private_pem and self._web_push_vapid_public_b64u:
            return True
        if await self._async_load_web_push_vapid_from_disk():
            return True
        return await self._async_generate_and_write_web_push_vapid()

    async def async_regenerate_web_push_keys(self) -> dict[str, Any]:
        """Rotate VAPID keys on disk and clear subscriptions (clients must re-subscribe)."""
        try:
            import pywebpush  # noqa: F401
        except ImportError:
            return {"ok": False, "error": "webpush_unavailable"}
        await self.hass.async_add_executor_job(self._sync_remove_web_push_vapid_files)
        self._web_push_vapid_private_pem = None
        self._web_push_vapid_public_b64u = None
        self._web_push_subscriptions = []
        if not await self._async_generate_and_write_web_push_vapid():
            return {"ok": False, "error": "vapid_generation_failed"}
        await self._async_save_state()
        self._notify_state_changed()
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Lori's Summon: Web Push keys rotated",
                    "message": (
                        "New VAPID keys were written to disk and saved subscriptions were cleared. "
                        "Open the summon page and enable browser notifications again."
                    ),
                    "notification_id": f"{DOMAIN}_webpush_keys_regenerated",
                },
            )
        except (HomeAssistantError, ValueError, TypeError) as err:
            _LOGGER.info(
                "Web Push keys rotated (notification not shown: %s); "
                "re-enable browser notifications on the summon page.",
                err,
            )
        return {
            "ok": True,
            "public_key": self._web_push_vapid_public_b64u or "",
        }

    def _web_push_keys_dir(self) -> Path:
        return Path(self.hass.config.path(DOMAIN)) / WEB_PUSH_KEYS_DIR_NAME

    def _web_push_private_key_path(self) -> Path:
        return self._web_push_keys_dir() / WEB_PUSH_VAPID_PRIVATE_FILENAME

    def _web_push_public_key_path(self) -> Path:
        return self._web_push_keys_dir() / WEB_PUSH_VAPID_PUBLIC_FILENAME

    def _sync_load_web_push_vapid_files(self) -> tuple[str, str] | None:
        priv_path = self._web_push_private_key_path()
        pub_path = self._web_push_public_key_path()
        if not priv_path.is_file() or not pub_path.is_file():
            return None
        pem = priv_path.read_text(encoding="utf-8").strip()
        pub_b64 = pub_path.read_text(encoding="utf-8").strip()
        if not pem or not pub_b64:
            return None
        derived_pub = _sync_vapid_public_b64u_from_private_pem(pem)
        if derived_pub is None or derived_pub != pub_b64:
            _LOGGER.warning(
                "Ignoring invalid Web Push VAPID key files at %s and %s",
                priv_path,
                pub_path,
            )
            return None
        return pem, pub_b64

    def _sync_write_web_push_vapid_files(self, pem: str, pub_b64u: str) -> None:
        base = self._web_push_keys_dir()
        base.mkdir(parents=True, exist_ok=True)
        priv_path = self._web_push_private_key_path()
        pub_path = self._web_push_public_key_path()
        pem_text = pem if pem.endswith("\n") else f"{pem}\n"
        priv_path.write_text(pem_text, encoding="utf-8")
        os.chmod(priv_path, 0o600)
        pub_path.write_text(f"{pub_b64u.strip()}\n", encoding="utf-8")
        os.chmod(pub_path, 0o644)

    def _sync_remove_web_push_vapid_files(self) -> None:
        for path in (self._web_push_private_key_path(), self._web_push_public_key_path()):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    async def _async_load_web_push_vapid_from_disk(self) -> bool:
        loaded = await self.hass.async_add_executor_job(
            self._sync_load_web_push_vapid_files
        )
        if loaded is None:
            return False
        pem, pub_b64 = loaded
        self._web_push_vapid_private_pem = pem
        self._web_push_vapid_public_b64u = pub_b64
        return True

    async def _async_write_web_push_vapid_to_disk(self, pem: str, pub_b64u: str) -> None:
        def _write() -> None:
            self._sync_write_web_push_vapid_files(pem, pub_b64u)

        await self.hass.async_add_executor_job(_write)

    def _stored_has_legacy_web_push_vapid(self, stored: dict[str, Any]) -> bool:
        priv = stored.get(STORE_WEB_PUSH_VAPID_PRIVATE)
        pub = stored.get(STORE_WEB_PUSH_VAPID_PUBLIC)
        return (isinstance(priv, str) and priv.strip()) or (
            isinstance(pub, str) and pub.strip()
        )

    async def _async_init_web_push_vapid(self, stored: dict[str, Any]) -> None:
        # Prefer PEM + public on disk; migrate from JSON store once; otherwise generate on first use.
        if await self._async_load_web_push_vapid_from_disk():
            if self._stored_has_legacy_web_push_vapid(stored):
                await self._async_save_state()
            return

        vapid_priv = stored.get(STORE_WEB_PUSH_VAPID_PRIVATE)
        vapid_pub = stored.get(STORE_WEB_PUSH_VAPID_PUBLIC)
        if (
            isinstance(vapid_priv, str)
            and vapid_priv.strip()
            and isinstance(vapid_pub, str)
            and vapid_pub.strip()
        ):
            pem = vapid_priv.strip()
            pub_b64 = vapid_pub.strip()
            derived_pub = await self.hass.async_add_executor_job(
                _sync_vapid_public_b64u_from_private_pem,
                pem,
            )
            if derived_pub is None or derived_pub != pub_b64:
                _LOGGER.warning(
                    "Ignoring invalid legacy Web Push VAPID keys from stored state; generating new keys"
                )
                if not await self._async_generate_and_write_web_push_vapid():
                    self._debug("web push vapid keys were not created at startup (optional)")
                return
            self._web_push_vapid_private_pem = pem
            self._web_push_vapid_public_b64u = pub_b64
            await self._async_write_web_push_vapid_to_disk(pem, pub_b64)
            await self._async_save_state()
            return

        if not await self._async_generate_and_write_web_push_vapid():
            self._debug("web push vapid keys were not created at startup (optional)")

    async def _async_generate_and_write_web_push_vapid(self) -> bool:
        try:
            pem, pub_b64 = await self.hass.async_add_executor_job(
                _sync_generate_web_push_vapid_pair
            )
        except Exception as err:
            _LOGGER.warning("Web Push VAPID key generation failed: %s", err)
            return False
        self._web_push_vapid_private_pem = pem
        self._web_push_vapid_public_b64u = pub_b64
        await self._async_write_web_push_vapid_to_disk(pem, pub_b64)
        return True

    def web_push_public_config(self) -> dict[str, Any]:
        return {
            "public_key": self._web_push_vapid_public_b64u or "",
            "subscription_count": len(self._web_push_subscriptions),
            "max_subscriptions": WEB_PUSH_MAX_SUBSCRIPTIONS,
        }

    async def async_register_web_push_subscription(self, info: Any) -> dict[str, Any]:
        try:
            import pywebpush  # noqa: F401
        except ImportError:
            return {"ok": False, "reason": "webpush_unavailable"}
        if not isinstance(info, dict):
            return {"ok": False, "reason": "invalid_body"}
        endpoint = str(info.get("endpoint") or "").strip()
        keys = info.get("keys")
        if not endpoint or not isinstance(keys, dict):
            return {"ok": False, "reason": "invalid_subscription"}
        p256 = str(keys.get("p256dh") or "").strip()
        auth_k = str(keys.get("auth") or "").strip()
        if not p256 or not auth_k:
            return {"ok": False, "reason": "invalid_keys"}
        sub_record: dict[str, Any] = {
            "endpoint": endpoint,
            "keys": {"p256dh": p256, "auth": auth_k},
        }
        exp = info.get("expirationTime")
        if exp is not None:
            sub_record["expirationTime"] = exp
        if not await self.async_ensure_web_push_vapid_keys():
            return {"ok": False, "reason": "vapid_unavailable"}
        self._web_push_subscriptions = [
            s
            for s in self._web_push_subscriptions
            if str(s.get("endpoint") or "").strip() != endpoint
        ]
        self._web_push_subscriptions.insert(0, sub_record)
        self._web_push_subscriptions = self._web_push_subscriptions[
            :WEB_PUSH_MAX_SUBSCRIPTIONS
        ]
        await self._async_save_state()
        return {"ok": True, "count": len(self._web_push_subscriptions)}

    async def async_unregister_web_push_subscription(self, endpoint: str) -> dict[str, Any]:
        ep = str(endpoint or "").strip()
        if not ep:
            return {"ok": False, "reason": "missing_endpoint"}
        before = len(self._web_push_subscriptions)
        self._web_push_subscriptions = [
            s
            for s in self._web_push_subscriptions
            if str(s.get("endpoint") or "").strip() != ep
        ]
        if len(self._web_push_subscriptions) == before:
            return {"ok": False, "reason": "not_found"}
        await self._async_save_state()
        return {"ok": True, "count": len(self._web_push_subscriptions)}

    async def async_clear_watched_events(self) -> int:
        # Cancel watched emergency retries and close them locally so the UI stops waiting on them
        watched_items = list(self._watched_events.values())
        for item in watched_items:
            await self._async_cancel_active_receipt(item)
            item[ATTR_ACTIVE] = False
            item[ATTR_NEXT_REMINDER_AT] = None
            if item.get(ATTR_DISPOSITION) == "triggered":
                item[ATTR_DISPOSITION] = "cancelled"
            if str(item.get(ATTR_EVENT_ID) or "") == str(self._active_event_id or ""):
                self._active_event_id = None
                self._cancel_reminder_task()
        if not watched_items:
            return 0
        self._watched_events.clear()
        await self._async_commit_state()
        return len(watched_items)

    def api_token_matches(self, token: str | None) -> bool:
        # Compare against the stored API token for generic external callers
        expected = str(self._value(CONF_API_TOKEN) or "")
        return bool(token) and token == expected

    def web_page_enabled(self) -> bool:
        # Infer the enabled state for older entries so existing page setups keep working
        configured_value = self._value(CONF_ENABLE_WEB)
        if configured_value is None:
            return bool(self._web_page_username() and self._web_page_password())
        return bool(configured_value)

    def has_web_page_auth(self) -> bool:
        return self.web_page_enabled() and bool(
            self._web_page_username() and self._web_page_password()
        )

    def web_page_auth_matches(self, username: str, password: str) -> bool:
        # Compare the configured login credentials using constant time checks because this endpoint is browser facing
        expected_username = self._web_page_username()
        expected_password = self._web_page_password()
        return (
            bool(expected_username and expected_password)
            and secrets.compare_digest(username, expected_username)
            and secrets.compare_digest(password, expected_password)
        )

    def web_page_access_token(self) -> tuple[str, int]:
        # Issue a signed JWT style token so the web UI can persist auth in local storage
        issued_at = int(dt_util.utcnow().timestamp())
        expires_at = issued_at + WEB_JWT_MAX_AGE_SECONDS
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "exp": expires_at,
            "iat": issued_at,
            "iss": DOMAIN,
            "sub": self._web_page_username(),
            "type": "web_access",
        }
        encoded_header = _jwt_b64encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        encoded_payload = _jwt_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signing_input = f"{encoded_header}.{encoded_payload}"
        signature = hmac.new(
            self._web_page_jwt_secret(),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{_jwt_b64encode(signature)}", expires_at

    def web_page_token_claims(self, token: str | None) -> dict[str, Any] | None:
        # Verify the token signature and claims before trusting browser auth state
        if not token:
            return None
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
            signing_input = f"{encoded_header}.{encoded_payload}"
            signature = _jwt_b64decode(encoded_signature)
            claims = json.loads(_jwt_b64decode(encoded_payload).decode("utf-8"))
        except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        expected = hmac.new(
            self._web_page_jwt_secret(),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not secrets.compare_digest(signature, expected):
            return None
        if claims.get("iss") != DOMAIN or claims.get("type") != "web_access":
            return None
        if claims.get("sub") != self._web_page_username():
            return None
        expires_at = int(claims.get("exp") or 0)
        if expires_at <= int(dt_util.utcnow().timestamp()):
            return None
        return claims

    def web_page_token_matches(self, token: str | None) -> bool:
        # Keep auth checks simple at the call sites by exposing a boolean wrapper
        return self.web_page_token_claims(token) is not None

    def web_page_token_refresh_window_seconds(self) -> int:
        # Let the frontend renew early without hard coding token timing
        return WEB_JWT_REFRESH_WINDOW_SECONDS

    async def async_shutdown(self) -> None:
        # Cancel background reminders so unloads do not leave orphaned tasks behind
        self._cancel_alive_schedule_handles()
        task = self._reminder_task
        self._reminder_task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def async_store_attachment(
        self,
        filename: str,
        data: bytes,
        mime_type: str | None = None,
    ) -> str:
        # Persist the original uploaded attachment so history previews and downloads keep the source file intact
        normalized_filename, normalized_data = await self.hass.async_add_executor_job(
            _normalize_attachment_upload,
            filename,
            data,
            mime_type,
        )
        # Keep attachments under the config directory because this integration reads them directly
        uploads_dir = self._attachment_uploads_dir()
        await self.hass.async_add_executor_job(
            lambda: uploads_dir.mkdir(parents=True, exist_ok=True)
        )
        suffix = (
            Path(normalized_filename).suffix.lower()
            or mimetypes.guess_extension(mime_type or "")
            or ".png"
        )
        target = uploads_dir / f"{uuid4().hex}{suffix}"
        await self.hass.async_add_executor_job(target.write_bytes, normalized_data)
        return str(target)

    async def async_store_voice_note(
        self,
        filename: str,
        data: bytes,
        mime_type: str | None = None,
    ) -> str:
        # Persist voice notes locally so notification links can play back the original recording
        normalized_filename, normalized_data = await self.hass.async_add_executor_job(
            _normalize_voice_note_upload,
            filename,
            data,
            mime_type,
        )
        uploads_dir = self._voice_note_uploads_dir()
        await self.hass.async_add_executor_job(
            lambda: uploads_dir.mkdir(parents=True, exist_ok=True)
        )
        suffix = (
            Path(normalized_filename).suffix.lower()
            or mimetypes.guess_extension(_normalized_upload_mime_type(mime_type) or "")
            or ".webm"
        )
        target = uploads_dir / f"{uuid4().hex}{suffix}"
        await self.hass.async_add_executor_job(target.write_bytes, normalized_data)
        return str(target)

    async def async_clone_voice_note(self, voice_note_path: str) -> str:
        # Duplicate stored audio before resending so history cleanup never invalidates a newer summon
        return await self._async_clone_stored_file(
            voice_note_path,
            self._voice_note_uploads_dir(),
            missing_reason="voice note not found",
            default_suffix=".webm",
        )

    async def async_clone_attachment(self, attachment_path: str) -> str:
        # Duplicate stored image attachments before resending so trimmed history cannot orphan the new summon
        return await self._async_clone_stored_file(
            attachment_path,
            self._attachment_uploads_dir(),
            missing_reason="attachment not found",
            default_suffix=".png",
        )

    async def _async_clone_stored_file(
        self,
        source_path_text: str,
        target_dir: Path,
        *,
        missing_reason: str,
        default_suffix: str,
    ) -> str:
        source_path = Path(source_path_text)
        if not await self.hass.async_add_executor_job(source_path.exists):
            raise ValueError(missing_reason)
        await self.hass.async_add_executor_job(
            lambda: target_dir.mkdir(parents=True, exist_ok=True)
        )
        target = target_dir / f"{uuid4().hex}{source_path.suffix.lower() or default_suffix}"
        payload = await self.hass.async_add_executor_job(source_path.read_bytes)
        await self.hass.async_add_executor_job(target.write_bytes, payload)
        return str(target)

    def summon_history_page(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        search_text: str = "",
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        safe_offset = max(0, offset)
        safe_limit = min(50, max(1, limit))
        normalized_search_text = str(search_text or "").strip().lower()
        normalized_sort_by = (
            str(sort_by or "").strip().lower()
            if str(sort_by or "").strip().lower() in {"date", "priority"}
            else "date"
        )
        normalized_sort_order = "asc" if str(sort_order or "").strip().lower() == "asc" else "desc"
        filtered_summons = [
            item
            for item in self._history
            if self._summon_matches_search(item, normalized_search_text)
        ]
        sorted_summons = sorted(
            filtered_summons,
            key=lambda item: self._summon_sort_key(item, normalized_sort_by),
            reverse=normalized_sort_order == "desc",
        )
        summons = sorted_summons[safe_offset: safe_offset + safe_limit]
        items = [self._summon_browser_item(item) for item in summons]
        next_offset = safe_offset + len(items)
        has_more = next_offset < len(sorted_summons)
        return {
            "items": items,
            "next_offset": next_offset if has_more else None,
            "has_more": has_more,
        }

    def _summon_matches_search(self, event: dict[str, Any], search_text: str) -> bool:
        if not search_text:
            return True
        attachment_path = str(event.get(ATTR_ATTACHMENT_PATH) or "").strip()
        voice_note_path = str(event.get(ATTR_VOICE_NOTE_PATH) or "").strip()
        searchable_parts = (
            str(event.get(ATTR_MESSAGE) or ""),
            str(event.get(ATTR_SOURCE) or ""),
            str(event.get(ATTR_DISPOSITION) or ""),
            str(event.get(ATTR_PRIORITY) or ""),
            Path(attachment_path).name if attachment_path else "",
            Path(voice_note_path).name if voice_note_path else "",
        )
        haystack = " ".join(searchable_parts).lower()
        return search_text in haystack

    def _summon_sort_key(self, event: dict[str, Any], sort_by: str) -> tuple[Any, ...]:
        priority_value = PRIORITY_VALUE_MAP.get(
            _normalize_priority(event.get(ATTR_PRIORITY)) or DEFAULT_SUMMON_PRIORITY,
            PRIORITY_VALUE_MAP[DEFAULT_SUMMON_PRIORITY],
        )
        event_timestamp = self._event_time(event).timestamp()
        if sort_by == "priority":
            return (
                priority_value,
                event_timestamp,
            )
        return (
            event_timestamp,
            priority_value,
        )

    async def async_delete_summon(self, event_id: str) -> dict[str, Any]:
        event = self._event_record(event_id)
        if event is None:
            return {"ok": False, "reason": "not_found"}
        if (
            bool(event.get(ATTR_ACTIVE))
            or str(self._active_event_id or "") == event_id
            or event_id in self._watched_events
        ):
            return {"ok": False, "reason": "active_summon"}
        self._history = [
            item
            for item in self._history
            if str(item.get(ATTR_EVENT_ID) or "") != event_id
        ]
        self._watched_events.pop(event_id, None)
        self._delete_attachment_file(event.get(ATTR_ATTACHMENT_PATH))
        self._delete_attachment_file(event.get(ATTR_VOICE_NOTE_PATH))
        await self._async_commit_state()
        return {"ok": True, "event_id": event_id}

    async def async_purge_saved_summons(
        self,
        *,
        cancel_receipts: bool = True,
    ) -> dict[str, Any]:
        # Remove all retained summon records and their stored files from Home Assistant
        stored_events: list[dict[str, Any]] = []
        seen_event_ids: set[str] = set()

        for candidate in chain(self._history, self._watched_events.values()):
            event_id = str(candidate.get(ATTR_EVENT_ID) or "").strip()
            if event_id and event_id in seen_event_ids:
                continue
            if event_id:
                seen_event_ids.add(event_id)
            stored_events.append(candidate)

        active = self._active_event_record()
        if active is not None:
            event_id = str(active.get(ATTR_EVENT_ID) or "").strip()
            if not event_id or event_id not in seen_event_ids:
                if event_id:
                    seen_event_ids.add(event_id)
                stored_events.append(active)

        if cancel_receipts:
            for event in stored_events:
                if self._event_requires_attention(event):
                    await self._async_cancel_active_receipt(event)

        attachment_paths: set[str] = set()
        voice_note_paths: set[str] = set()
        for event in stored_events:
            attachment_path = str(event.get(ATTR_ATTACHMENT_PATH) or "").strip()
            voice_note_path = str(event.get(ATTR_VOICE_NOTE_PATH) or "").strip()
            if attachment_path:
                attachment_paths.add(attachment_path)
            if voice_note_path:
                voice_note_paths.add(voice_note_path)

        self._cancel_reminder_task()
        self._active_event_id = None
        self._watched_events.clear()
        self._history = []

        for attachment_path in attachment_paths:
            self._delete_attachment_file(attachment_path)
        for voice_note_path in voice_note_paths:
            self._delete_attachment_file(voice_note_path)

        await self._async_commit_state()
        self._debug("purged %s saved summons", len(stored_events))
        return {"ok": True, "count": len(stored_events)}

    async def async_resend_summon(
        self,
        event_id: str,
        *,
        source: str = "web_page_summon_resend",
        voice_note_base_url: str | None = None,
    ) -> TriggerResult:
        event = self._event_record(event_id)
        if event is None:
            return TriggerResult(
                accepted=False,
                disposition="not_found",
                message=DEFAULT_SUMMON_MESSAGE,
                source=source,
            )

        original_attachment_path = str(event.get(ATTR_ATTACHMENT_PATH) or "").strip()
        original_voice_note_path = str(event.get(ATTR_VOICE_NOTE_PATH) or "").strip()
        cloned_attachment_path: str | None = None
        cloned_voice_note_path: str | None = None
        if original_attachment_path and Path(original_attachment_path).exists():
            cloned_attachment_path = await self.async_clone_attachment(original_attachment_path)
        if original_voice_note_path and Path(original_voice_note_path).exists():
            cloned_voice_note_path = await self.async_clone_voice_note(original_voice_note_path)

        try:
            result = await self.async_trigger(
                str(event.get(ATTR_MESSAGE) or DEFAULT_SUMMON_MESSAGE),
                source=source,
                priority=event.get(ATTR_PRIORITY),
                attachment_path=cloned_attachment_path,
                voice_note_path=cloned_voice_note_path,
                voice_note_base_url=voice_note_base_url,
            )
        except Exception:
            self._delete_attachment_file(cloned_attachment_path)
            self._delete_attachment_file(cloned_voice_note_path)
            raise
        if not result.accepted:
            self._delete_attachment_file(cloned_attachment_path)
            self._delete_attachment_file(cloned_voice_note_path)
        return result

    async def _send_notification(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # Send notifications directly to Pushover so emergency receipts and callbacks can be tracked
        form = await self._pushover_form_data(payload)
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(PUSHOVER_MESSAGES_URL, data=form) as response:
                raw = await response.text()
        except Exception as err:
            raise HomeAssistantError(f"Failed to contact Pushover: {err}") from err

        try:
            response_data = json.loads(raw)
        except Exception as err:
            raise HomeAssistantError(
                f"Pushover returned an invalid response: {raw[:200]}"
            ) from err

        if int(response_data.get("status", 0)) != 1:
            errors = response_data.get("errors") or [raw[:200] or "unknown error"]
            raise HomeAssistantError(
                f"Pushover send failed: {', '.join(str(item) for item in errors)}"
            )

        return self._pushover_delivery_metadata(payload, response_data)

    async def _async_save_state(self) -> None:
        # Persist only the pieces that need to survive a restart
        await self._store.async_save(
            {
                ATTR_HISTORY: self._history[: self._history_size()],
                STORE_ACTIVE_EVENT_ID: self._active_event_id,
                STORE_WATCHED_EVENTS: [dict(item) for item in self._watched_events.values()],
                ATTR_LAST_TRIGGERED_AT: (
                    self._last_trigger_at.isoformat() if self._last_trigger_at else None
                ),
                STORE_ALIVE_HISTORY: self._alive_history[: self._history_size()],
                STORE_ALIVE_ACTIVE_EVENT_ID: self._alive_active_event_id,
                STORE_ALIVE_WATCHED_EVENTS: [
                    dict(item) for item in self._alive_watched_events.values()
                ],
                STORE_ALIVE_SCHEDULE: dict(self._alive_schedule_blob),
                STORE_WEB_PUSH_SUBSCRIPTIONS: [
                    dict(s) for s in self._web_push_subscriptions
                ],
            }
        )

    def _value(self, key: str) -> Any:
        return self.entry.options.get(key, self.entry.data.get(key))

    def _bool_value(self, key: str, default: bool) -> bool:
        # Respect explicit false values while still handling missing options from older entries
        value = self._value(key)
        return default if value is None else bool(value)

    def _lights_enabled(self) -> bool:
        return self._bool_value(CONF_TRIGGER_LIGHTS, DEFAULT_TRIGGER_LIGHTS)

    def _debug(self, message: str, *args: Any) -> None:
        # Emit optional runtime logs without polluting normal Home Assistant logs
        if self._bool_value(CONF_DEBUG_LOGGING, False):
            _LOGGER.info(
                "Lori's Summon debug [%s] " + message, self.entry.title, *args)

    def _active_event_record(self) -> dict[str, Any] | None:
        if not self._active_event_id:
            return None
        return next(
            (
                item
                for item in self._history
                if item.get(ATTR_EVENT_ID) == self._active_event_id
            ),
            None,
        )

    def _render_message(self, payload: dict[str, Any]) -> str:
        # Fall back to the raw summon message so delivery still works if the template breaks
        template_text = self._value(
            CONF_MESSAGE_TEMPLATE) or DEFAULT_MESSAGE_TEMPLATE
        try:
            rendered_message = Template(template_text, self.hass).async_render(
                payload, parse_result=False
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Failed to render Lori's Summon template: %s", err)
            rendered_message = str(payload[ATTR_MESSAGE])
        return self._message_with_media_links(rendered_message, payload)

    def _message_with_media_links(
        self,
        message_text: str,
        payload: dict[str, Any],
    ) -> str:
        # Render short labeled media links so Pushover does not need to show raw URLs in the message body
        links: list[str] = []
        voice_note_url = self.voice_note_player_url_for_payload(payload)
        if voice_note_url:
            links.append(
                f'<a href="{html.escape(voice_note_url, quote=True)}">Voice Note</a>'
            )
        elif (
            str(payload.get(ATTR_VOICE_NOTE_PATH) or "").strip()
            and not payload.get("reminder")
        ):
            self._debug(
                "voice note present for %s but no reachable playback URL could be built",
                str(payload.get(ATTR_EVENT_ID) or ""),
            )
        attachment_url = self.attachment_url_for_payload(payload)
        if attachment_url:
            links.append(
                f'<a href="{html.escape(attachment_url, quote=True)}">Attachment</a>'
            )
        elif (
            str(payload.get(ATTR_ATTACHMENT_PATH) or "").strip()
            and not payload.get("reminder")
        ):
            self._debug(
                "attachment present for %s but no reachable download URL could be built",
                str(payload.get(ATTR_EVENT_ID) or ""),
            )
        if not links:
            return message_text
        escaped_message = html.escape(message_text).replace("\n", "<br>")
        separator = "<br><br>" if escaped_message else ""
        return f"{escaped_message}{separator}" + "<br>".join(links)

    async def _pushover_form_data(
        self,
        payload: dict[str, Any],
    ) -> FormData:
        # Build one request so Pushover can receive the summon text plus any signed media links
        priority_label = _normalize_priority(payload.get(ATTR_PRIORITY)) or DEFAULT_SUMMON_PRIORITY
        form = FormData()
        form.add_field("token", self._pushover_app_token())
        form.add_field("user", self._pushover_user_key())
        device = self._pushover_device()
        if device:
            form.add_field("device", device)
        form.add_field(
            "title",
            str(
                payload.get(ATTR_PUSHOVER_TITLE)
                or self._value(CONF_ALERT_TITLE)
                or DEFAULT_ALERT_TITLE
            ),
        )
        voice_note_url = self.voice_note_player_url_for_payload(payload)
        attachment_url = self.attachment_url_for_payload(payload)
        form.add_field("message", self._render_message(payload))
        if voice_note_url or attachment_url:
            form.add_field("html", "1")
        form.add_field("priority", str(PRIORITY_VALUE_MAP[priority_label]))
        pushover_sound = self._pushover_sound_for_priority(priority_label)
        if pushover_sound:
            form.add_field("sound", pushover_sound)
        if priority_label == PUSHOVER_PRIORITY_EMERGENCY:
            form.add_field("retry", str(DEFAULT_PUSHOVER_EMERGENCY_RETRY))
            form.add_field("expire", str(DEFAULT_PUSHOVER_EMERGENCY_EXPIRE))
            callback_url = self._pushover_callback_url()
            if callback_url:
                form.add_field("callback", callback_url)
            else:
                _LOGGER.warning(
                    "Lori's Summon could not determine a public Home Assistant URL for the Pushover callback"
                )
        return form

    def _pushover_delivery_metadata(
        self,
        payload: dict[str, Any],
        response_data: dict[str, Any],
    ) -> dict[str, Any]:
        # Persist receipt details for emergency messages so callbacks and UI polling can find them later
        priority_label = _normalize_priority(payload.get(ATTR_PRIORITY)) or DEFAULT_SUMMON_PRIORITY
        if priority_label != PUSHOVER_PRIORITY_EMERGENCY:
            return {}
        receipt = str(response_data.get("receipt", "")).strip()
        metadata: dict[str, Any] = {
            ATTR_PUSHOVER_ACKNOWLEDGED: False,
            ATTR_PUSHOVER_ACKNOWLEDGED_AT: None,
            ATTR_PUSHOVER_ACKNOWLEDGED_BY: None,
            ATTR_PUSHOVER_ACKNOWLEDGED_BY_DEVICE: None,
            ATTR_PUSHOVER_EXPIRED: False,
            ATTR_PUSHOVER_EXPIRES_AT: _unix_timestamp_to_iso(
                dt_util.parse_datetime(str(payload.get(ATTR_TRIGGERED_AT) or "")).timestamp()
                + DEFAULT_PUSHOVER_EMERGENCY_EXPIRE
                if dt_util.parse_datetime(str(payload.get(ATTR_TRIGGERED_AT) or "")) is not None
                else None
            ),
            ATTR_PUSHOVER_LAST_DELIVERED_AT: payload.get(ATTR_TRIGGERED_AT),
            ATTR_PUSHOVER_RECEIPT: receipt or None,
        }
        if receipt:
            self._debug("received Pushover emergency receipt %s", receipt)
        else:
            _LOGGER.warning("Emergency Pushover send did not return a receipt")
        return metadata

    def _pushover_sound_for_priority(self, priority: str) -> str:
        # Resolve sounds from the priority specific config so the caller can shape alert tone per urgency
        sound_map = {
            PUSHOVER_PRIORITY_LOWEST: str(
                self._value(
                    CONF_PUSHOVER_SOUND_LOWEST) or DEFAULT_PUSHOVER_SOUND_LOWEST
            ).strip(),
            PUSHOVER_PRIORITY_LOW: str(
                self._value(
                    CONF_PUSHOVER_SOUND_LOW) or DEFAULT_PUSHOVER_SOUND_LOW
            ).strip(),
            PUSHOVER_PRIORITY_DEFAULT: str(
                self._value(
                    CONF_PUSHOVER_SOUND_DEFAULT) or DEFAULT_PUSHOVER_SOUND_DEFAULT
            ).strip(),
            PUSHOVER_PRIORITY_NORMAL: str(
                self._value(
                    CONF_PUSHOVER_SOUND_NORMAL) or DEFAULT_PUSHOVER_SOUND_NORMAL
            ).strip(),
            PUSHOVER_PRIORITY_EMERGENCY: str(
                self._value(
                    CONF_PUSHOVER_SOUND_EMERGENCY) or DEFAULT_PUSHOVER_SOUND_EMERGENCY
            ).strip(),
        }
        return sound_map.get(priority, "")

    def _attachment_uploads_dir(self) -> Path:
        # Keep upload files inside the Home Assistant config directory for reminders and retries
        return Path(self.hass.config.path("loris_summon_uploads"))

    def _voice_note_uploads_dir(self) -> Path:
        # Keep voice-note files in the Home Assistant config directory so the player endpoint can read them back
        return Path(self.hass.config.path("loris_summon_voice_notes"))

    def _pushover_app_token(self) -> str:
        return str(self._value(CONF_PUSHOVER_APP_TOKEN) or DEFAULT_PUSHOVER_APP_TOKEN).strip()

    def _pushover_user_key(self) -> str:
        return str(self._value(CONF_PUSHOVER_USER_KEY) or DEFAULT_PUSHOVER_USER_KEY).strip()

    def _pushover_device(self) -> str:
        return str(self._value(CONF_PUSHOVER_DEVICE) or DEFAULT_PUSHOVER_DEVICE).strip()

    def _pushover_callback_url(self) -> str | None:
        # Prefer the configured external URL so Pushover can reach the callback endpoint from the Internet
        base_url = self._public_base_url()
        api_token = str(self._value(CONF_API_TOKEN) or "").strip()
        if not base_url or not api_token:
            return None
        return f"{base_url}{PUSHOVER_CALLBACK_PATH}?token={quote(api_token, safe='')}"

    def _public_base_url(self) -> str | None:
        # Read the public base URL defensively because Home Assistant stores it in different places across versions
        candidates = (
            getattr(self.hass.config, "external_url", None),
            getattr(getattr(self.hass.config, "api", None), "base_url", None),
        )
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.rstrip("/")
        return None

    def voice_note_player_url_for_payload(self, payload: dict[str, Any]) -> str | None:
        return self._voice_note_url_for_payload(payload, path=VOICE_NOTE_PLAY_PATH)

    def voice_note_file_url_for_request(self, event_id: str, token: str) -> str:
        return (
            f"{VOICE_NOTE_FILE_PATH}"
            f"?event_id={quote(event_id, safe='')}&token={quote(token, safe='')}"
        )

    def attachment_file_url_for_request(self, event_id: str, token: str) -> str:
        return (
            f"{ATTACHMENT_FILE_PATH}"
            f"?event_id={quote(event_id, safe='')}&token={quote(token, safe='')}"
        )

    def voice_note_relative_urls(self, event_id: str, voice_note_path: str) -> tuple[str, str]:
        token = self._voice_note_access_token(event_id, voice_note_path)
        return (
            f"{VOICE_NOTE_PLAY_PATH}?event_id={quote(event_id, safe='')}&token={quote(token, safe='')}",
            self.voice_note_file_url_for_request(event_id, token),
        )

    def attachment_relative_url(self, event_id: str, attachment_path: str) -> str:
        token = self._attachment_access_token(event_id, attachment_path)
        return self.attachment_file_url_for_request(event_id, token)

    def attachment_url_for_payload(self, payload: dict[str, Any]) -> str | None:
        base_url = (
            str(payload.get(ATTR_VOICE_NOTE_BASE_URL) or "").strip().rstrip("/")
            or self._voice_note_base_url()
        )
        event_id = str(payload.get(ATTR_EVENT_ID) or "").strip()
        attachment_path = str(payload.get(ATTR_ATTACHMENT_PATH) or "").strip()
        if not base_url or not event_id or not attachment_path:
            return None
        if not Path(attachment_path).exists():
            return None
        token = self._attachment_access_token(event_id, attachment_path)
        return (
            f"{base_url}{ATTACHMENT_FILE_PATH}"
            f"?event_id={quote(event_id, safe='')}&token={quote(token, safe='')}"
        )

    def resolve_voice_note_path(self, event_id: str | None, token: str | None) -> Path | None:
        # Validate the signed playback token against the stored summon record before serving audio
        event = self._watched_event(event_id) or self._event_record(event_id)
        if event is None:
            return None
        event_id_text = str(event.get(ATTR_EVENT_ID) or "").strip()
        voice_note_path = str(event.get(ATTR_VOICE_NOTE_PATH) or "").strip()
        if not event_id_text or not voice_note_path or not token:
            return None
        expected_token = self._voice_note_access_token(event_id_text, voice_note_path)
        if not secrets.compare_digest(token, expected_token):
            return None
        path = Path(voice_note_path)
        try:
            resolved_path = path.resolve()
            resolved_path.relative_to(self._voice_note_uploads_dir().resolve())
        except (OSError, ValueError):
            return None
        return resolved_path if resolved_path.exists() else None

    def resolve_attachment_path(self, event_id: str | None, token: str | None) -> Path | None:
        event = self._watched_event(event_id) or self._event_record(event_id)
        if event is None:
            return None
        event_id_text = str(event.get(ATTR_EVENT_ID) or "").strip()
        attachment_path = str(event.get(ATTR_ATTACHMENT_PATH) or "").strip()
        if not event_id_text or not attachment_path or not token:
            return None
        expected_token = self._attachment_access_token(event_id_text, attachment_path)
        if not secrets.compare_digest(token, expected_token):
            return None
        path = Path(attachment_path)
        try:
            resolved_path = path.resolve()
            resolved_path.relative_to(self._attachment_uploads_dir().resolve())
        except (OSError, ValueError):
            return None
        return resolved_path if resolved_path.exists() else None

    def _voice_note_url_for_payload(
        self,
        payload: dict[str, Any],
        *,
        path: str,
    ) -> str | None:
        base_url = (
            str(payload.get(ATTR_VOICE_NOTE_BASE_URL) or "").strip().rstrip("/")
            or self._voice_note_base_url()
        )
        event_id = str(payload.get(ATTR_EVENT_ID) or "").strip()
        voice_note_path = str(payload.get(ATTR_VOICE_NOTE_PATH) or "").strip()
        if not base_url or not event_id or not voice_note_path:
            return None
        if not Path(voice_note_path).exists():
            return None
        token = self._voice_note_access_token(event_id, voice_note_path)
        return (
            f"{base_url}{path}"
            f"?event_id={quote(event_id, safe='')}&token={quote(token, safe='')}"
        )

    def _voice_note_base_url(self) -> str | None:
        # Media links can fall back to the internal URL because the client device, not Pushover's servers, opens them
        candidates = (
            getattr(self.hass.config, "external_url", None),
            getattr(self.hass.config, "internal_url", None),
            getattr(getattr(self.hass.config, "api", None), "base_url", None),
        )
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.rstrip("/")
        return None

    def _summon_browser_item(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event.get(ATTR_EVENT_ID) or "").strip()
        attachment_path = str(event.get(ATTR_ATTACHMENT_PATH) or "").strip()
        voice_note_path = str(event.get(ATTR_VOICE_NOTE_PATH) or "").strip()
        acknowledged = bool(
            str(event.get(ATTR_ACKNOWLEDGED_AT) or "").strip()
            or str(event.get(ATTR_PUSHOVER_ACKNOWLEDGED_AT) or "").strip()
            or str(event.get(ATTR_DISPOSITION) or "").strip() == "acknowledged"
        )
        has_attachment = bool(attachment_path and Path(attachment_path).exists())
        has_voice_note = bool(voice_note_path and Path(voice_note_path).exists())
        attachment_kind = (
            _attachment_kind(
                Path(attachment_path).name,
                mimetypes.guess_type(attachment_path)[0],
            )
            if has_attachment
            else None
        )
        attachment_url: str | None = None
        play_url: str | None = None
        download_url: str | None = None
        if has_attachment:
            attachment_url = self.attachment_relative_url(event_id, attachment_path)
        if has_voice_note:
            play_url, download_url = self.voice_note_relative_urls(event_id, voice_note_path)
        return {
            "event_id": event_id,
            "message": str(event.get(ATTR_MESSAGE) or ""),
            "priority": _normalize_priority(event.get(ATTR_PRIORITY)) or DEFAULT_SUMMON_PRIORITY,
            "source": str(event.get(ATTR_SOURCE) or ""),
            "triggered_at": event.get(ATTR_TRIGGERED_AT),
            "active": bool(event.get(ATTR_ACTIVE)),
            "acknowledged": acknowledged,
            "disposition": str(event.get(ATTR_DISPOSITION) or ""),
            "has_attachment": has_attachment,
            "attachment_kind": attachment_kind,
            "attachment_filename": Path(attachment_path).name if has_attachment else None,
            "attachment_url": attachment_url,
            "has_voice_note": has_voice_note,
            "voice_note_filename": Path(voice_note_path).name if has_voice_note else None,
            "play_url": play_url,
            "download_url": download_url,
        }

    def _voice_note_access_token(self, event_id: str, voice_note_path: str) -> str:
        signature = hmac.new(
            self._voice_note_secret(),
            f"{event_id}|{voice_note_path}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return _jwt_b64encode(signature)

    def _attachment_access_token(self, event_id: str, attachment_path: str) -> str:
        signature = hmac.new(
            self._attachment_secret(),
            f"{event_id}|{attachment_path}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return _jwt_b64encode(signature)

    def _voice_note_secret(self) -> bytes:
        # Scope signed playback links to this config entry without exposing the main API token in the URL
        return "|".join(
            (
                self.entry.entry_id,
                str(self._value(CONF_API_TOKEN) or ""),
                "voice_note",
            )
        ).encode("utf-8")

    def _attachment_secret(self) -> bytes:
        return "|".join(
            (
                self.entry.entry_id,
                str(self._value(CONF_API_TOKEN) or ""),
                "attachment",
            )
        ).encode("utf-8")

    def _web_page_username(self) -> str:
        return str(self._value(CONF_WEB_USERNAME) or DEFAULT_WEB_USERNAME).strip()

    def _web_page_password(self) -> str:
        return str(self._value(CONF_WEB_PASSWORD) or DEFAULT_WEB_PASSWORD).strip()

    def _web_page_jwt_secret(self) -> bytes:
        # Bind web auth tokens to this config entry and the current web credentials
        return "|".join(
            (
                self.entry.entry_id,
                str(self._value(CONF_API_TOKEN) or ""),
                self._web_page_username(),
                self._web_page_password(),
            )
        ).encode("utf-8")

    async def _async_send_reminder(self, active: dict[str, Any]) -> None:
        # Reuse the summon payload so reminder notifications follow the same template and target
        now = dt_util.utcnow()
        next_reminder_at = self._next_reminder_at(now).isoformat()
        next_count = int(active.get(ATTR_REMINDER_COUNT, 0)) + 1
        payload = dict(active)
        payload[ATTR_REMINDER_COUNT] = next_count
        payload[ATTR_PENDING_ACK] = True
        payload["reminder"] = True
        try:
            await self._send_notification(payload)
        except Exception as err:
            # Move the schedule forward even on delivery failures so retries stay bounded
            active[ATTR_NEXT_REMINDER_AT] = next_reminder_at
            await self._async_commit_state()
            _LOGGER.warning("Failed to send Lori's Summon reminder: %s", err)
            return
        active[ATTR_REMINDER_COUNT] = next_count
        active[ATTR_NEXT_REMINDER_AT] = next_reminder_at
        await self._async_commit_state()
        self._debug(
            "sent reminder %s for summon %s",
            active[ATTR_REMINDER_COUNT],
            active[ATTR_EVENT_ID],
        )

    async def _async_flash_lights_safely(self) -> None:
        # Keep light failures out of the HTTP response path because summon delivery is the primary action
        try:
            await self._flash_lights()
        except Exception as err:
            _LOGGER.warning("Failed to flash Lori's Summon lights: %s", err)

    async def _async_commit_state(self) -> None:
        # Save then fan out dispatcher updates so entities always read persisted state
        await self._async_save_state()
        self._notify_state_changed()

    def _notify_state_changed(self) -> None:
        async_dispatcher_send(self.hass, DISPATCH_STATE_UPDATED)

    def _history_size(self) -> int:
        return int(self._value(CONF_HISTORY_SIZE) or DEFAULT_HISTORY_SIZE)

    def _alive_checks_per_day(self) -> int:
        raw = self._value(CONF_ALIVE_CHECKS_PER_DAY)
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = DEFAULT_ALIVE_CHECKS_PER_DAY
        return max(ALIVE_SCHEDULE_MIN_PER_DAY, min(n, ALIVE_SCHEDULE_MAX_PER_DAY))

    def _preview_trigger(
        self,
        message: str,
        source: str,
        now: datetime,
        priority: Any = None,
    ) -> TriggerResult:
        # Normalize inputs once so every caller gets the same acceptance result
        cleaned_message = message.strip() or DEFAULT_SUMMON_MESSAGE
        cleaned_source = source.strip() or "external"
        cleaned_priority = _normalize_priority(priority)
        if cleaned_priority is None:
            return TriggerResult(
                accepted=False,
                disposition="invalid_priority",
                message=cleaned_message,
                source=cleaned_source,
            )

        cooldown_until = self._cooldown_until()
        if cooldown_until and now < cooldown_until:
            self._debug(
                "rejected summon from %s because cooldown is active", cleaned_source)
            return TriggerResult(
                accepted=False,
                disposition="cooldown",
                message=cleaned_message,
                source=cleaned_source,
                priority=cleaned_priority,
                cooldown_until=cooldown_until.isoformat(),
            )

        rate_limited_until = self._rate_limited_until(now)
        if rate_limited_until is not None:
            self._debug(
                "rejected summon from %s because rate limit is active", cleaned_source)
            return TriggerResult(
                accepted=False,
                disposition="rate_limited",
                message=cleaned_message,
                source=cleaned_source,
                priority=cleaned_priority,
                rate_limited_until=rate_limited_until.isoformat(),
            )

        return TriggerResult(
            accepted=True,
            disposition="triggered",
            message=cleaned_message,
            source=cleaned_source,
            priority=cleaned_priority,
        )

    def _restore_reminder_state(self) -> None:
        # Backfill reminder metadata for summons created before reminders were added
        active = self._active_event_record()
        if active is None:
            return
        if self._is_emergency_event(active):
            active[ATTR_NEXT_REMINDER_AT] = None
            return
        active.setdefault(ATTR_REMINDER_COUNT, 0)
        active.setdefault(
            ATTR_NEXT_REMINDER_AT,
            self._next_reminder_at(self._event_time(active)).isoformat(),
        )

    def _ensure_reminder_task(self) -> None:
        # Run at most one reminder loop because only one summon can be active
        active = self._active_event_record()
        if active is None or self._is_emergency_event(active):
            return
        if self._reminder_task is not None and not self._reminder_task.done():
            return
        self._reminder_task = self.hass.async_create_task(
            self._async_reminder_loop())

    def _cancel_reminder_task(self) -> None:
        # Cancel the current reminder loop before switching the active summon
        if self._reminder_task is None:
            return
        self._reminder_task.cancel()
        self._reminder_task = None

    async def _async_reminder_loop(self) -> None:
        # Keep reminding until the summon is acknowledged or superseded
        try:
            while True:
                active = self._active_event_record()
                if active is None:
                    return
                await asyncio.sleep(self._seconds_until_reminder(active))
                active = self._active_event_record()
                if active is None:
                    return
                await self._async_send_reminder(active)
        except asyncio.CancelledError:
            raise

    def _seconds_until_reminder(self, active: dict[str, Any]) -> float:
        # Honor the stored next reminder time so reminders resume cleanly after restarts
        next_reminder = dt_util.parse_datetime(
            str(active.get(ATTR_NEXT_REMINDER_AT) or ""))
        if next_reminder is None:
            next_reminder = self._next_reminder_at(dt_util.utcnow())
            active[ATTR_NEXT_REMINDER_AT] = next_reminder.isoformat()
        return max(0.0, (next_reminder - dt_util.utcnow()).total_seconds())

    def _next_reminder_at(self, base_time: datetime) -> datetime:
        return base_time + timedelta(seconds=REMINDER_INTERVAL_SECONDS)

    def _event_time(self, event: dict[str, Any]) -> datetime:
        # Fall back to now so malformed restored state does not break the reminder loop
        triggered_at = dt_util.parse_datetime(
            str(event.get(ATTR_TRIGGERED_AT) or ""))
        return triggered_at or dt_util.utcnow()

    def _is_emergency_event(self, event: dict[str, Any]) -> bool:
        # Let Pushover own the retry loop for emergency summons
        return (
            _normalize_priority(event.get(ATTR_PRIORITY)) or DEFAULT_SUMMON_PRIORITY
        ) == PUSHOVER_PRIORITY_EMERGENCY

    def _event_requires_attention(self, event: dict[str, Any] | None) -> bool:
        if event is None or not self._is_emergency_event(event):
            return False
        if not str(event.get(ATTR_PUSHOVER_RECEIPT) or "").strip():
            return False
        if str(event.get(ATTR_ACKNOWLEDGED_AT) or "").strip():
            return False
        if str(event.get(ATTR_PUSHOVER_ACKNOWLEDGED_AT) or "").strip():
            return False
        if bool(event.get(ATTR_PUSHOVER_EXPIRED)):
            return False
        return str(event.get(ATTR_DISPOSITION) or "").strip() != "cancelled"

    def _restore_outstanding_state(self) -> bool:
        state_changed = False
        watched_events: dict[str, dict[str, Any]] = {}

        for event_id, event in self._watched_events.items():
            if self._event_requires_attention(event):
                watched_events[event_id] = event
                continue
            state_changed = self._finalize_delivered_event(event) or state_changed

        if watched_events != self._watched_events:
            self._watched_events = watched_events
            state_changed = True

        active = self._active_event_record()
        if active is None:
            if self._active_event_id is not None:
                self._active_event_id = None
                state_changed = True
            return state_changed

        if self._event_requires_attention(active):
            event_id = str(active.get(ATTR_EVENT_ID) or "").strip()
            if event_id and event_id not in self._watched_events:
                self._watched_events[event_id] = active
                state_changed = True
            return state_changed

        state_changed = self._finalize_delivered_event(active) or state_changed
        if self._active_event_id is not None:
            self._active_event_id = None
            state_changed = True
        return state_changed

    def _cooldown_until(self) -> datetime | None:
        # Base cooldown on the last accepted summon so retries do not spam the target
        if self._last_trigger_at is None:
            return None
        seconds = int(self._value(CONF_COOLDOWN_SECONDS)
                      or DEFAULT_COOLDOWN_SECONDS)
        if seconds <= 0:
            return None
        return self._last_trigger_at + timedelta(seconds=seconds)

    def _cooldown_until_iso(self) -> str | None:
        cooldown_until = self._cooldown_until()
        if cooldown_until is None or dt_util.utcnow() >= cooldown_until:
            return None
        return cooldown_until.isoformat()

    def _trim_recent_triggers(self, now: datetime) -> None:
        # Drop old trigger timestamps before evaluating the sliding rate limit window
        window = int(self._value(CONF_RATE_LIMIT_WINDOW_SECONDS)
                     or DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
        threshold = now - timedelta(seconds=window)
        self._recent_trigger_times = [
            stamp for stamp in self._recent_trigger_times if stamp > threshold]

    def _rate_limited_until(self, now: datetime) -> datetime | None:
        self._trim_recent_triggers(now)
        limit = int(self._value(CONF_MAX_TRIGGERS_PER_WINDOW)
                    or DEFAULT_MAX_TRIGGERS_PER_WINDOW)
        if len(self._recent_trigger_times) < limit:
            return None
        window = int(self._value(CONF_RATE_LIMIT_WINDOW_SECONDS)
                     or DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
        return self._recent_trigger_times[0] + timedelta(seconds=window)

    def _rate_limited_until_iso(self) -> str | None:
        blocked_until = self._rate_limited_until(dt_util.utcnow())
        if blocked_until is None or dt_util.utcnow() >= blocked_until:
            return None
        return blocked_until.isoformat()

    def _create_history_entry(
        self,
        message: str,
        source: str,
        priority: str,
        attachment_path: str | None,
        voice_note_path: str | None,
        voice_note_base_url: str | None,
        now: datetime,
    ) -> dict[str, Any]:
        # Record full summon details so history and audit state stay useful after restarts
        entry = {
            ATTR_EVENT_ID: uuid4().hex,
            ATTR_MESSAGE: message,
            ATTR_NEXT_REMINDER_AT: None,
            ATTR_REMINDER_COUNT: 0,
            ATTR_PRIORITY: priority,
            ATTR_SOURCE: source,
            ATTR_TRIGGERED_AT: now.isoformat(),
            ATTR_ACKNOWLEDGED_AT: None,
            ATTR_ACKNOWLEDGED_BY: None,
            ATTR_DISPOSITION: "triggered",
            ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS: None,
            ATTR_ACTIVE: False,
            ATTR_PUSHOVER_ACKNOWLEDGED: False,
            ATTR_PUSHOVER_ACKNOWLEDGED_AT: None,
            ATTR_PUSHOVER_ACKNOWLEDGED_BY: None,
            ATTR_PUSHOVER_ACKNOWLEDGED_BY_DEVICE: None,
            ATTR_PUSHOVER_EXPIRED: False,
            ATTR_PUSHOVER_EXPIRES_AT: None,
            ATTR_PUSHOVER_LAST_DELIVERED_AT: None,
            ATTR_PUSHOVER_RECEIPT: None,
        }
        if attachment_path:
            entry[ATTR_ATTACHMENT_PATH] = attachment_path
        if voice_note_path:
            entry[ATTR_VOICE_NOTE_PATH] = voice_note_path
        normalized_base_url = str(voice_note_base_url or "").strip().rstrip("/")
        if normalized_base_url:
            entry[ATTR_VOICE_NOTE_BASE_URL] = normalized_base_url
        return entry

    def _event_record(self, event_id: str | None) -> dict[str, Any] | None:
        # Look up a stored summon by event id so the browser can poll one specific event
        if not event_id:
            return None
        return next(
            (
                item
                for item in self._history
                if item.get(ATTR_EVENT_ID) == event_id
            ),
            None,
        )

    def _primary_outstanding_event_record(self) -> dict[str, Any] | None:
        active = self._active_event_record()
        if self._event_requires_attention(active):
            return active
        return max(
            (
                item
                for item in self._watched_events.values()
                if self._event_requires_attention(item)
            ),
            key=self._event_time,
            default=None,
        )

    def _watched_event(self, event_id: str | None) -> dict[str, Any] | None:
        # Prefer the live watched snapshot so browser status can survive history trimming
        watched_id = str(event_id or "").strip()
        if not watched_id:
            return None
        return self._watched_events.get(watched_id)

    def _event_by_receipt(self, receipt: str) -> dict[str, Any] | None:
        # Map Pushover callback receipts back to the summon that created them
        return next(
            (
                item
                for item in self._history
                if str(item.get(ATTR_PUSHOVER_RECEIPT) or "") == receipt
            ),
            None,
        )

    def _watched_event_by_receipt(self, receipt: str) -> dict[str, Any] | None:
        # Resolve callbacks from the active watch snapshot before falling back to archived history
        watched_receipt = str(receipt or "").strip()
        if not watched_receipt:
            return None
        return next(
            (
                item
                for item in self._watched_events.values()
                if str(item.get(ATTR_PUSHOVER_RECEIPT) or "") == watched_receipt
            ),
            None,
        )

    def _apply_pushover_callback_data(self, event: dict[str, Any], data: dict[str, Any]) -> None:
        # Copy callback fields onto the stored summon record before any local acknowledgment happens
        event[ATTR_PUSHOVER_ACKNOWLEDGED] = str(data.get("acknowledged", "0")).strip() == "1"
        event[ATTR_PUSHOVER_ACKNOWLEDGED_AT] = _unix_timestamp_to_iso(data.get("acknowledged_at"))
        event[ATTR_PUSHOVER_ACKNOWLEDGED_BY] = str(data.get("acknowledged_by") or "").strip() or None
        event[ATTR_PUSHOVER_ACKNOWLEDGED_BY_DEVICE] = str(
            data.get("acknowledged_by_device") or ""
        ).strip() or None
        if str(data.get("expired", "0")).strip() == "1":
            event[ATTR_PUSHOVER_EXPIRED] = True

    def _apply_local_acknowledgment(
        self,
        event: dict[str, Any],
        acknowledged_by: str,
        acknowledged_at_iso: str,
    ) -> None:
        # Keep manual acknowledgments aligned across the active event and watched emergencies
        event[ATTR_ACKNOWLEDGED_AT] = acknowledged_at_iso
        event[ATTR_ACKNOWLEDGED_BY] = acknowledged_by
        event[ATTR_DISPOSITION] = "acknowledged"
        event[ATTR_ACTIVE] = False
        event[ATTR_NEXT_REMINDER_AT] = None
        self._set_acknowledgment_duration(event, acknowledged_at_iso)

    def _set_acknowledgment_duration(
        self,
        event: dict[str, Any],
        acknowledged_at_iso: str | None,
    ) -> None:
        # Persist emergency acknowledgment latency so browser toasts and history stay consistent
        if not self._is_emergency_event(event):
            event[ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS] = None
            return
        triggered_at = dt_util.parse_datetime(str(event.get(ATTR_TRIGGERED_AT) or ""))
        acknowledged_at = dt_util.parse_datetime(str(acknowledged_at_iso or ""))
        if triggered_at is None or acknowledged_at is None:
            event[ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS] = None
            return
        event[ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS] = max(
            0,
            int((acknowledged_at - triggered_at).total_seconds()),
        )

    def _outstanding_events(self) -> list[dict[str, Any]]:
        # Dedupe every still-outstanding emergency so Home Assistant can clear them in one action
        outstanding: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        active = self._active_event_record()
        if self._event_requires_attention(active):
            event_id = str(active.get(ATTR_EVENT_ID) or "")
            if event_id:
                seen_ids.add(event_id)
                outstanding.append(active)
        for event in self._watched_events.values():
            if not self._event_requires_attention(event):
                continue
            event_id = str(event.get(ATTR_EVENT_ID) or "")
            if not event_id or event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            outstanding.append(event)
        return outstanding

    async def _async_cancel_active_receipt(self, active: dict[str, Any]) -> None:
        # Cancel outstanding emergency retries when a local acknowledgment happens first
        receipt = str(active.get(ATTR_PUSHOVER_RECEIPT) or "").strip()
        if not receipt:
            return
        session = async_get_clientsession(self.hass)
        action_url = PUSHOVER_RECEIPT_CANCEL_URL.format(receipt=receipt)
        try:
            async with session.post(
                action_url,
                data={"token": self._pushover_app_token()},
            ) as response:
                raw = await response.text()
        except Exception as err:
            _LOGGER.warning(
                "Failed to cancel Lori's Summon Pushover receipt %s: %s",
                receipt,
                err,
            )
            return

        try:
            response_data = json.loads(raw)
        except Exception:
            response_data = {"status": 0, "raw": raw}
        if int(response_data.get("status", 0)) != 1:
            self._debug("failed to cancel receipt %s with response %s", receipt, raw)

    def _trim_history_entries(self) -> None:
        # Keep watched emergencies in retained state until they resolve so SSE clients can reconcile removals
        max_items = self._history_size()
        watched_ids = set(self._watched_events)
        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        non_watched_kept = 0

        for item in self._history:
            event_id = str(item.get(ATTR_EVENT_ID) or "")
            if event_id in watched_ids:
                kept.append(item)
                continue
            if non_watched_kept < max_items:
                kept.append(item)
                non_watched_kept += 1
                continue
            removed.append(item)

        self._history = kept
        for item in removed:
            self._delete_attachment_file(item.get(ATTR_ATTACHMENT_PATH))
            self._delete_attachment_file(item.get(ATTR_VOICE_NOTE_PATH))

    def _delete_attachment_file(self, attachment_path: Any) -> None:
        # Clean up orphaned upload files so images and voice notes do not grow without bound
        path_text = str(attachment_path or "").strip()
        if not path_text:
            return
        path = Path(path_text)
        if not path.exists():
            return
        try:
            path.unlink()
        except OSError:
            self._debug("failed to remove upload file %s", path)

    def _supersede_previous_active(self, new_event_id: str) -> None:
        # Keep one primary tracked emergency while older emergency receipts remain watchable
        active = self._active_event_record()
        if active is None or active.get(ATTR_EVENT_ID) == new_event_id:
            return
        active[ATTR_ACTIVE] = False
        active[ATTR_NEXT_REMINDER_AT] = None
        if active.get(ATTR_DISPOSITION) == "triggered":
            active[ATTR_DISPOSITION] = "superseded"

    def _finalize_delivered_event(self, event: dict[str, Any]) -> bool:
        state_changed = False
        if bool(event.get(ATTR_ACTIVE)):
            event[ATTR_ACTIVE] = False
            state_changed = True
        if event.get(ATTR_NEXT_REMINDER_AT) is not None:
            event[ATTR_NEXT_REMINDER_AT] = None
            state_changed = True
        if event.get(ATTR_DISPOSITION) == "triggered":
            event[ATTR_DISPOSITION] = "delivered"
            state_changed = True
        return state_changed

    def _light_target(self) -> dict[str, Any]:
        target = self._value(CONF_LIGHT_TARGET)
        return target if isinstance(target, dict) else {}

    def _light_entity_ids(self) -> list[str]:
        # Resolve all selected lights once so flashing and restore work across entities areas and devices
        target = self._light_target()
        if not target:
            return []
        registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        entity_ids: set[str] = set()
        raw_entities = target.get(ATTR_ENTITY_ID, [])
        if isinstance(raw_entities, str):
            raw_entities = [raw_entities]
        entity_ids.update(
            entity_id
            for entity_id in raw_entities
            if isinstance(entity_id, str) and entity_id.startswith("light.")
        )
        for area_id in _as_list(target.get("area_id")):
            if area_registry.async_get_area(area_id):
                entity_ids.update(
                    entry.entity_id
                    for entry in er.async_entries_for_area(registry, area_id)
                    if entry.entity_id.startswith("light.")
                )
        for device_id in _as_list(target.get("device_id")):
            if device_registry.async_get(device_id):
                entity_ids.update(
                    entry.entity_id
                    for entry in er.async_entries_for_device(registry, device_id)
                    if entry.entity_id.startswith("light.")
                )
        return sorted(entity_ids)

    def _light_entity_snapshots(self) -> list[LightSnapshot]:
        # Snapshot attributes before flashing so restore can preserve color and brightness
        snapshots: list[LightSnapshot] = []
        for entity_id in self._light_entity_ids():
            state = self.hass.states.get(entity_id)
            if state is not None:
                snapshots.append(LightSnapshot(
                    entity_id, state.state, dict(state.attributes)))
        return snapshots

    async def _flash_lights(self) -> None:
        # Always restore the original light state even if a flash call fails midway through
        snapshot = self._light_entity_snapshots()
        if not snapshot:
            return
        entity_ids = [light.entity_id for light in snapshot]
        flash_data: dict[str, Any] = {
            "brightness": int(
                self._value(CONF_LIGHT_FLASH_BRIGHTNESS)
                or DEFAULT_LIGHT_FLASH_BRIGHTNESS
            )
        }
        color = self._normalize_flash_color(
            self._value(CONF_LIGHT_FLASH_COLOR) or DEFAULT_LIGHT_FLASH_COLOR
        )
        if color is not None:
            flash_data["rgb_color"] = color
        count = max(1, int(self._value(CONF_LIGHT_FLASH_COUNT)
                    or DEFAULT_LIGHT_FLASH_COUNT))
        duration = float(self._value(CONF_LIGHT_FLASH_DURATION)
                         or DEFAULT_LIGHT_FLASH_DURATION)
        try:
            for _ in range(count):
                await self._flash_turn_on(entity_ids, flash_data)
                await asyncio.sleep(duration)
                await self._call_light_service(entity_ids, "turn_off")
                await asyncio.sleep(duration)
        finally:
            await self._restore_lights(snapshot)

    async def _flash_turn_on(self, entity_ids: list[str], flash_data: dict[str, Any]) -> None:
        # Retry without color data because some light platforms reject rgb payloads
        try:
            await self._call_light_service(entity_ids, "turn_on", flash_data)
        except HomeAssistantError:
            fallback = dict(flash_data)
            fallback.pop("rgb_color", None)
            await self._call_light_service(entity_ids, "turn_on", fallback)

    async def _call_light_service(
        self,
        entity_ids: list[str],
        service: str,
        service_data: dict[str, Any] | None = None,
    ) -> None:
        # Skip unavailable lights so one dead device does not break the whole summon flow
        for entity_id in entity_ids:
            if not self._is_light_available(entity_id):
                continue
            await self.hass.services.async_call(
                "light",
                service,
                {ATTR_ENTITY_ID: entity_id, **(service_data or {})},
                blocking=True,
            )

    async def _restore_lights(self, snapshot: list[LightSnapshot]) -> None:
        for light in snapshot:
            await self._restore_light(light)

    async def _restore_light(self, light: LightSnapshot) -> None:
        # Retry restoration because some integrations report unavailable briefly after flashing
        for _ in range(LIGHT_RESTORE_RETRIES):
            if not self._is_light_available(light.entity_id):
                await asyncio.sleep(LIGHT_RESTORE_RETRY_DELAY)
                continue
            if light.state != STATE_ON:
                await self.hass.services.async_call(
                    "light",
                    "turn_off",
                    {ATTR_ENTITY_ID: light.entity_id},
                    blocking=True,
                )
                return
            restore_data = self._restore_turn_on_data(light)
            try:
                await self.hass.services.async_call("light", "turn_on", restore_data, blocking=True)
            except Exception:
                # Drop the first color attribute that failed because restore compatibility varies by light platform
                fallback = dict(restore_data)
                removed = next(
                    (attr for attr in RESTORE_COLOR_ATTRS if attr in fallback), None)
                if removed is None:
                    raise
                fallback.pop(removed, None)
                await self.hass.services.async_call("light", "turn_on", fallback, blocking=True)
            return

    def _is_light_available(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        return state is not None and state.state not in {STATE_UNAVAILABLE, STATE_UNKNOWN}

    @staticmethod
    def _restore_turn_on_data(light: LightSnapshot) -> dict[str, Any]:
        # Prefer the original color model because switching models can produce the wrong hue
        restore_data: dict[str, Any] = {ATTR_ENTITY_ID: light.entity_id}
        for attr in RESTORE_BASE_ATTRS:
            if attr in light.attributes:
                restore_data[attr] = light.attributes[attr]
        for attr in RESTORE_COLOR_ATTRS:
            if attr in light.attributes:
                restore_data[attr] = _normalize_restore_value(
                    attr, light.attributes[attr])
                break
        return restore_data

    @staticmethod
    def _normalize_flash_color(value: Any) -> list[int] | None:
        # Clamp flash color values so invalid config data cannot break the light service call
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            return None
        try:
            return [max(0, min(255, int(channel))) for channel in value]
        except (TypeError, ValueError):
            return None


def _sync_generate_web_push_vapid_pair() -> tuple[str, str]:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return pem, _jwt_b64encode(pub_bytes)


def _sync_vapid_public_b64u_from_private_pem(private_pem: str) -> str | None:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    try:
        private_key = serialization.load_pem_private_key(
            private_pem.encode("utf-8"),
            password=None,
            backend=default_backend(),
        )
    except Exception:
        return None
    try:
        pub_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
    except Exception:
        return None
    return _jwt_b64encode(pub_bytes)


def _web_push_send_sync(
    subscription_info: dict[str, Any],
    data: str,
    private_pem: str,
    sub_claim: str,
) -> str | None:
    """Return None on success, or \"gone\" if the subscription should be removed."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=private_pem,
            vapid_claims={"sub": sub_claim},
            ttl=3600,
            timeout=20,
        )
        return None
    except WebPushException as exc:
        resp = getattr(exc, "response", None)
        code = getattr(resp, "status_code", None) if resp is not None else None
        if code in (404, 410):
            return "gone"
        _LOGGER.warning("Web Push delivery failed: %s", exc)
        return None
    except Exception as exc:
        _LOGGER.warning("Web Push delivery error: %s", exc)
        return None


def _as_list(value: Any) -> list[str]:
    # Normalize selectors because Home Assistant may store one or many target values
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _normalize_restore_value(attr: str, value: Any) -> Any:
    # Convert mutable list states back into tuples because light services expect immutable coordinates
    tuple_attrs = {"rgb_color", "rgbw_color",
                   "rgbww_color", "hs_color", "xy_color"}
    if attr in tuple_attrs and isinstance(value, (list, tuple)):
        return tuple(value)
    return value


def _unix_timestamp_to_iso(value: Any) -> str | None:
    # Convert callback timestamps into ISO strings so the rest of the integration can stay consistent
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return dt_util.utc_from_timestamp(timestamp).isoformat()
