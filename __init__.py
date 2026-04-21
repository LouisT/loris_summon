"""Lori's Summon integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import html
import json
import mimetypes
from pathlib import Path
import random
from typing import Any

from aiohttp import web  # type: ignore
from homeassistant.components.http import HomeAssistantView  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant, ServiceCall  # type: ignore
from homeassistant.exceptions import HomeAssistantError  # type: ignore
from homeassistant.helpers import config_validation as cv  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore
from homeassistant.helpers.typing import ConfigType  # type: ignore
import voluptuous as vol  # type: ignore

from .const import (
    ACKNOWLEDGE_PATH,
    ATTACHMENT_FILE_PATH,
    ATTR_ACKNOWLEDGED_BY,
    ATTR_MESSAGE,
    ATTR_PRIORITY,
    ATTR_SOURCE,
    DEFAULT_SUMMON_MESSAGE,
    DEFAULT_SUMMON_PRIORITY,
    DOMAIN,
    ICON_PATH,
    PLATFORMS,
    PUSHOVER_CALLBACK_PATH,
    PUSHOVER_PRIORITY_DEFAULT,
    PUSHOVER_PRIORITY_EMERGENCY,
    PUSHOVER_PRIORITY_LOW,
    PUSHOVER_PRIORITY_LOWEST,
    PUSHOVER_PRIORITY_NORMAL,
    SERVICE_ACKNOWLEDGE,
    SERVICE_TEST_ACTIONS,
    SERVICE_TRIGGER,
    STATUS_PATH,
    STATUS_STREAM_PATH,
    TRIGGER_PATH,
    VOICE_NOTES_PATH,
    VOICE_NOTE_FILE_PATH,
    VOICE_NOTE_PLAY_PATH,
    WEB_PATH,
    WEB_LOGIN_PATH,
    WEB_REFRESH_PATH,
    DISPATCH_STATE_UPDATED,
)
from .runtime import LorisSummonRuntime, TriggerResult

SERVICES_REGISTERED_KEY = "services_registered"
VIEWS_REGISTERED_KEY = "views_registered"
TEMPLATES_DIR = Path(__file__).with_name("templates")
WEB_PAGE_TEMPLATE_PATH = TEMPLATES_DIR / "web_page.html"
VOICE_NOTE_PAGE_TEMPLATE_PATH = TEMPLATES_DIR / "voice_note_page.html"
WEB_PAGE_ICON_PATH = Path(__file__).with_name("brand") / "icon.png"
WEB_PLACEHOLDERS = (
    "Command your sub to bend sweetly to your every desire.",
    "Let your sub yield to whatever your heart desires.",
    "Remind your submissive that their place is to serve your will.",
    "Command your sub to bow to your every whim.",
    "Have your submissive bend to your will and indulge your desires.",
    "Direct your sub to surrender to whatever you please.",
    "Make your submissive yield to the pull of your desires.",
    "Command your sub to exist for your pleasure and your will alone.",
    "Let your sub melt into obedience to your every wish.",
    "Instruct your submissive to bend eagerly to your desires.",
    "Have your sub submit to your whims with proper devotion.",
    "Command your sub to yield gracefully to your every craving.",
    "Remind your sub that their purpose is to please you.",
    "Let your submissive be guided entirely by your desire.",
    "Command your sub to bend, yield, and obey your will.",
    "Command your pet to bend sweetly to your every desire.",
    "Remind your pet that their place is at the mercy of your will.",
    "Let your pet yield eagerly to whatever your heart desires.",
    "Command your pet to bow to your every whim.",
    "Have your pet bend obediently to your will.",
    "Direct your pet to surrender to your every desire.",
    "Remind your pet that they exist to please you.",
    "Let your pet be guided by your every whim.",
    "Command your pet to yield gracefully to your desires.",
    "Have your pet submit sweetly to your will.",
    "Instruct your pet to follow wherever your desire leads.",
    "Let your pet learn how lovely it is to bend to your will.",
)
SUCCESS_MESSAGES = (
    "Your summons has gone out; what happens next is up to you.",
    "Your sub has been summoned; please do with them as you wish.",
    "Your sub has been called; now let the anticipation build.",
    "Your summons has been sent; let them wonder what awaits.",
    "Your pet has been summoned; the rest is your pleasure.",
    "Your sub has been sent for; now the fun begins.",
    "Your call has gone out; no doubt they are already thinking of you.",
    "Your submissive has been summoned; what comes next is yours to decide.",
    "Your sub has been beckoned; let them wait and wonder.",
    "Your summons has been sent; now let them ache for what is next.",
    "Your sub has been called; the teasing starts now.",
    "Your summons is on its way; let them wonder what you have in mind.",
    "Your submissive has been summoned; now keep them guessing.",
    "Your summons has been delivered; the rest is where the fun begins.",
    "Your sub has been sent for; now let the tension build.",
    "Your summons has gone out; let their imagination do the work.",
    "Your sub has been called; what awaits is entirely your choice.",
    "Your pet has been sent for; now let them squirm a little.",
    "Your summons has been issued; the waiting is part of the fun.",
    "Your call has gone out; let them feel it sink in.",
    "Your pet has been summoned; now let the anticipation linger.",
)
ERROR_MESSAGES = (
    "Summons failed; your sub will have to answer for this lapse.",
    "Your summons did not go through; such disappointment may warrant correction.",
    "Summons failed; your submissive may owe you an apology.",
    "Your call was not delivered; your sub can expect to make up for it.",
    "The summons failed; someone may be due for a little discipline.",
    "Your sub escaped the summons this time; they will not escape the consequences.",
    "Summons unsuccessful; your submissive may have earned a stern reminder.",
    "Your call did not reach its target; your sub will have to make amends.",
    "The summons was not delivered; your pet may need a lesson in attentiveness.",
    "Summons failed; this little failure may require proper correction.",
    "Summons failed; your pet seems to need better training.",
    "Your pet missed the summons; how disappointing.",
    "Summons unsuccessful; your pet will have to be corrected.",
    "Your call went unanswered; your pet may need a reminder of their place.",
    "The summons failed; your pet has been very naughty indeed.",
    "Your pet slipped the leash this time; that will not go unnoticed.",
    "Summons failed; your pet clearly requires firmer handling.",
    "Your call did not reach your pet; such poor behavior deserves notice.",
    "Your pet failed to respond to the summons; how unbecoming.",
    "Summons undelivered; your pet may be due for a little discipline.",
    "Your pet ignored the call; that lapse will need addressing.",
    "The summons failed; your pet has earned your displeasure.",
)
WEB_PRIORITY_OPTIONS = (
    (PUSHOVER_PRIORITY_LOWEST, "Lowest"),
    (PUSHOVER_PRIORITY_LOW, "Low"),
    (PUSHOVER_PRIORITY_DEFAULT, "Normal"),
    (PUSHOVER_PRIORITY_NORMAL, "High"),
    (PUSHOVER_PRIORITY_EMERGENCY, "Emergency"),
)
WEB_PRIORITY_VALUES = frozenset(value for value, _ in WEB_PRIORITY_OPTIONS)
type LorisSummonConfigEntry = ConfigEntry[LorisSummonRuntime]  # type: ignore
TRIGGER_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_PRIORITY): vol.Any(cv.string, vol.Coerce(int)),
        vol.Optional(ATTR_SOURCE): cv.string,
    }
)
TEST_ACTIONS_SERVICE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_MESSAGE): cv.string})
ACKNOWLEDGE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ACKNOWLEDGED_BY): cv.string,
        vol.Optional(ATTR_SOURCE): cv.string,
    }
)
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # Register services and HTTP views once because the config entry owns the runtime state
    hass.data.setdefault(DOMAIN, {})
    _ensure_component_setup(hass)
    return True


def _ensure_component_setup(hass: HomeAssistant) -> None:
    # Re-run safely from setup entry because Home Assistant reloads do not call async_setup again
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(SERVICES_REGISTERED_KEY):
        _register_services(hass)
        domain_data[SERVICES_REGISTERED_KEY] = True
    if not domain_data.get(VIEWS_REGISTERED_KEY):
        _register_views(hass)
        domain_data[VIEWS_REGISTERED_KEY] = True


def _register_services(hass: HomeAssistant) -> None:
    # Keep schemas centralized so service behavior stays aligned with README examples
    async def handle_trigger(call: ServiceCall) -> None:
        await _async_handle_trigger_service(hass, call)

    async def handle_test_actions(call: ServiceCall) -> None:
        await _async_handle_test_actions_service(hass, call)

    async def handle_acknowledge(call: ServiceCall) -> None:
        await _async_handle_acknowledge_service(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER,
        handle_trigger,
        schema=TRIGGER_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_ACTIONS,
        handle_test_actions,
        schema=TEST_ACTIONS_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACKNOWLEDGE,
        handle_acknowledge,
        schema=ACKNOWLEDGE_SERVICE_SCHEMA,
    )

def _register_views(hass: HomeAssistant) -> None:
    # Expose the HTTP endpoints from the component bootstrap so webhooks survive reloads
    hass.http.register_view(LorisSummonTriggerView(hass))
    hass.http.register_view(LorisSummonAcknowledgeView(hass))
    hass.http.register_view(LorisSummonPushoverCallbackView(hass))
    hass.http.register_view(LorisSummonWebLoginView(hass))
    hass.http.register_view(LorisSummonWebRefreshView(hass))
    hass.http.register_view(LorisSummonStatusView(hass))
    hass.http.register_view(LorisSummonStatusStreamView(hass))
    hass.http.register_view(LorisSummonIconView(hass))
    hass.http.register_view(LorisSummonVoiceNotesView(hass))
    hass.http.register_view(LorisSummonAttachmentFileView(hass))
    hass.http.register_view(LorisSummonVoiceNotePageView(hass))
    hass.http.register_view(LorisSummonVoiceNoteFileView(hass))
    hass.http.register_view(LorisSummonPageView(hass))


async def _async_handle_trigger_service(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    runtime = _configured_runtime(hass)
    result = await runtime.async_trigger(
        call.data.get(ATTR_MESSAGE, ""),
        call.data.get(ATTR_SOURCE, "service"),
        priority=call.data.get(ATTR_PRIORITY, DEFAULT_SUMMON_PRIORITY),
    )
    if not result.accepted:
        raise vol.Invalid(f"Summon rejected: {result.disposition}")


async def _async_handle_test_actions_service(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    runtime = _configured_runtime(hass)
    await runtime.async_test_actions(call.data.get(ATTR_MESSAGE, "Test summon"))


async def _async_handle_acknowledge_service(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    runtime = _configured_runtime(hass)
    result = await runtime.async_acknowledge_all(
        call.data.get(ATTR_ACKNOWLEDGED_BY, "service"),
        call.data.get(ATTR_SOURCE, "service"),
    )
    if not result.get("acknowledged"):
        raise vol.Invalid("No outstanding notifications to acknowledge")


async def async_setup_entry(hass: HomeAssistant, entry: LorisSummonConfigEntry) -> bool:
    # Create one runtime per config entry and share it with the entity platforms
    _ensure_component_setup(hass)
    runtime = LorisSummonRuntime(hass, entry)
    await runtime.async_initialize()
    entry.runtime_data = runtime
    hass.data.setdefault(DOMAIN, {})["runtime"] = runtime
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LorisSummonConfigEntry) -> bool:
    # Stop background reminder work before unloading platforms
    await entry.runtime_data.async_shutdown()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop("runtime", None)
        entry.runtime_data = None
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: LorisSummonConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _configured_runtime(hass: HomeAssistant) -> LorisSummonRuntime:
    # Fail fast for service calls because they cannot return HTTP style responses
    runtime = _runtime(hass)
    if runtime is None:
        raise vol.Invalid("Lori's Summon is not configured")
    return runtime


def _runtime(hass: HomeAssistant) -> LorisSummonRuntime | None:
    return hass.data.get(DOMAIN, {}).get("runtime")


class LorisSummonView(HomeAssistantView):
    # Share common request helpers across the external and browser endpoints
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def _runtime_or_response(self) -> tuple[LorisSummonRuntime | None, web.Response | None]:
        runtime = _runtime(self.hass)
        if runtime is None:
            return None, self.json_message("Integration is not configured", status_code=503)
        return runtime, None

    def _authorized_runtime_or_response(
        self, request: web.Request
    ) -> tuple[LorisSummonRuntime | None, web.Response | None]:
        runtime, error = self._runtime_or_response()
        if error is not None or runtime is None:
            return runtime, error

        token = _extract_bearer_token(
            request) or request.headers.get("X-Loris-Token")
        if not runtime.api_token_matches(token):
            return None, self.json_message("Unauthorized", status_code=401)
        return runtime, None

    def _pushover_callback_runtime_or_response(
        self, request: web.Request
    ) -> tuple[LorisSummonRuntime | None, web.Response | None]:
        runtime, error = self._runtime_or_response()
        if error is not None or runtime is None:
            return runtime, error
        if not runtime.api_token_matches(request.query.get("token")):
            return None, self.json_message("Unauthorized", status_code=401)
        return runtime, None

    def _web_page_runtime_or_response(
        self, request: web.Request
    ) -> tuple[LorisSummonRuntime | None, web.Response | None]:
        runtime, error = self._runtime_or_response()
        if error is not None or runtime is None:
            return runtime, error
        if not runtime.web_page_enabled():
            return None, web.Response(status=404, text="Web summon page is disabled")
        if not runtime.has_web_page_auth():
            return None, web.Response(status=503, text="Web summon page is not configured")
        return runtime, None

    def _web_token_runtime_or_response(
        self,
        request: web.Request,
        *,
        allow_query_token: bool = False,
    ) -> tuple[LorisSummonRuntime | None, dict[str, Any] | None, web.Response | None]:
        runtime, error = self._web_page_runtime_or_response(request)
        if error is not None or runtime is None:
            return runtime, None, error

        token = _extract_web_page_token(request, allow_query_token=allow_query_token)
        claims = runtime.web_page_token_claims(token)
        if claims is None:
            return None, None, _web_page_auth_error_response(stream=allow_query_token)
        return runtime, claims, None

    def _voice_note_path_or_response(
        self, request: web.Request
    ) -> tuple[LorisSummonRuntime | None, Path | None, web.Response | None]:
        runtime, error = self._runtime_or_response()
        if error is not None or runtime is None:
            return runtime, None, error
        voice_note_path = runtime.resolve_voice_note_path(
            request.query.get("event_id"),
            request.query.get("token"),
        )
        if voice_note_path is None:
            return runtime, None, web.Response(status=404, text="Voice note not found")
        return runtime, voice_note_path, None

    def _attachment_path_or_response(
        self, request: web.Request
    ) -> tuple[LorisSummonRuntime | None, Path | None, web.Response | None]:
        runtime, error = self._runtime_or_response()
        if error is not None or runtime is None:
            return runtime, None, error
        attachment_path = runtime.resolve_attachment_path(
            request.query.get("event_id"),
            request.query.get("token"),
        )
        if attachment_path is None:
            return runtime, None, web.Response(status=404, text="Attachment not found")
        return runtime, attachment_path, None


class LorisSummonTriggerView(LorisSummonView):
    url = TRIGGER_PATH
    name = "api:loris_summon:trigger"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        runtime, error = self._authorized_runtime_or_response(request)
        if error is not None or runtime is None:
            return error

        data = await _parse_request_body(request)
        message = _extract_message(data) or DEFAULT_SUMMON_MESSAGE
        priority = _extract_priority(data)
        source = _extract_source(data, default="external")
        try:
            attachment_path = await _async_store_optional_attachment(runtime, data.get("attachment"))
            voice_note_path = await _async_store_optional_voice_note(runtime, data.get("voice_note"))
        except ValueError as err:
            return web.json_response(
                {"ok": False, "message": str(err), "disposition": "invalid"},
                status=400,
            )
        try:
            result = await runtime.async_trigger(
                message,
                source=source,
                priority=priority,
                attachment_path=attachment_path,
                voice_note_path=voice_note_path,
                voice_note_base_url=_request_base_url(request),
            )
        except HomeAssistantError as err:
            return web.json_response(
                {"ok": False, "message": str(err), "disposition": "delivery_failed"},
                status=502,
            )
        return web.json_response(
            _trigger_result_payload(result),
            status=_trigger_result_status(result),
        )


class LorisSummonAcknowledgeView(LorisSummonView):
    url = ACKNOWLEDGE_PATH
    name = "api:loris_summon:acknowledge"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        runtime, error = self._authorized_runtime_or_response(request)
        if error is not None or runtime is None:
            return error

        data = await _parse_request_body(request)
        acknowledged_by = str(
            data.get("acknowledged_by", "external")).strip() or "external"
        source = _extract_source(data, default="external_ack")
        result = await runtime.async_acknowledge_all(
            acknowledged_by=acknowledged_by,
            source=source,
        )
        return web.json_response(result, status=200 if result.get("acknowledged") else 409)


class LorisSummonPushoverCallbackView(LorisSummonView):
    url = PUSHOVER_CALLBACK_PATH
    name = "api:loris_summon:pushover_callback"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        runtime, error = self._pushover_callback_runtime_or_response(request)
        if error is not None or runtime is None:
            return error

        data = await _parse_request_body(request)
        result = await runtime.async_handle_pushover_callback(data)
        if result.get("ok"):
            return web.json_response(result, status=200)
        if result.get("reason") == "missing_receipt":
            return web.json_response(result, status=400)
        return web.json_response(result, status=409)


class LorisSummonWebLoginView(LorisSummonView):
    url = WEB_LOGIN_PATH
    name = "api:loris_summon:web_login"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        runtime, error = self._web_page_runtime_or_response(request)
        if error is not None or runtime is None:
            return error

        data = await _parse_request_body(request)
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        if not runtime.web_page_auth_matches(username, password):
            return web.json_response(
                {"ok": False, "message_text": "Incorrect username or password."},
                status=401,
            )
        token, expires_at = runtime.web_page_access_token()
        return web.json_response(
            {
                "ok": True,
                "token": token,
                "expires_at": expires_at,
                "refresh_window_seconds": runtime.web_page_token_refresh_window_seconds(),
            }
        )


class LorisSummonWebRefreshView(LorisSummonView):
    url = WEB_REFRESH_PATH
    name = "api:loris_summon:web_refresh"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        runtime, claims, error = self._web_token_runtime_or_response(request)
        if error is not None or runtime is None or claims is None:
            return error

        token, expires_at = runtime.web_page_access_token()
        return web.json_response(
            {
                "ok": True,
                "token": token,
                "expires_at": expires_at,
                "refresh_window_seconds": runtime.web_page_token_refresh_window_seconds(),
            }
        )


class LorisSummonStatusView(LorisSummonView):
    url = STATUS_PATH
    name = "api:loris_summon:status"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        runtime, claims, error = self._web_token_runtime_or_response(request)
        if error is not None or runtime is None or claims is None:
            return error

        return web.json_response(
            {
                "ok": True,
                **runtime.browser_status(request.query.get("event_id")),
            }
        )


class LorisSummonStatusStreamView(LorisSummonView):
    url = STATUS_STREAM_PATH
    name = "api:loris_summon:status_stream"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        runtime, claims, error = self._web_token_runtime_or_response(
            request,
            allow_query_token=True,
        )
        if error is not None or runtime is None or claims is None:
            return error

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        await response.prepare(request)

        status_changed = asyncio.Event()

        def handle_status_change() -> None:
            # Wake the stream loop whenever runtime state changes
            status_changed.set()

        unsubscribe = async_dispatcher_connect(
            self.hass,
            DISPATCH_STATE_UPDATED,
            handle_status_change,
        )

        try:
            snapshot = {"ok": True, **runtime.browser_status()}
            await _async_write_sse_event(response, "status", snapshot)

            while True:
                try:
                    await asyncio.wait_for(status_changed.wait(), timeout=20)
                    status_changed.clear()
                    snapshot = {"ok": True, **runtime.browser_status()}
                    await _async_write_sse_event(response, "status", snapshot)
                except asyncio.TimeoutError:
                    await response.write(b": keep-alive\n\n")
        except (ConnectionResetError, RuntimeError):
            pass
        finally:
            unsubscribe()
            with suppress(ConnectionResetError, RuntimeError):
                await response.write_eof()
        return response


class LorisSummonVoiceNotesView(LorisSummonView):
    url = VOICE_NOTES_PATH
    name = "api:loris_summon:voice_notes"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        runtime, claims, error = self._web_token_runtime_or_response(request)
        if error is not None or runtime is None or claims is None:
            return error

        try:
            offset = max(0, int(request.query.get("offset", "0")))
        except (TypeError, ValueError):
            offset = 0
        try:
            limit = min(50, max(1, int(request.query.get("limit", "20"))))
        except (TypeError, ValueError):
            limit = 20
        search_text = str(request.query.get("search", "") or "").strip()
        sort_by = str(request.query.get("sort_by", "date") or "date").strip()
        sort_order = str(request.query.get("sort_order", "desc") or "desc").strip()

        return web.json_response(
            {
                "ok": True,
                **runtime.summon_history_page(
                    offset=offset,
                    limit=limit,
                    search_text=search_text,
                    sort_by=sort_by,
                    sort_order=sort_order,
                ),
            }
        )

    async def post(self, request: web.Request) -> web.Response:
        runtime, claims, error = self._web_token_runtime_or_response(request)
        if error is not None or runtime is None or claims is None:
            return error

        ctype = (request.content_type or "").split(";", 1)[0].strip().lower()
        if ctype == "multipart/form-data":
            form = await request.post()
            action = str(form.get("action") or "").strip().lower()
            if action != "schedule_summon":
                return web.json_response(
                    {
                        "ok": False,
                        "message_text": "Unsupported multipart request for this endpoint.",
                    },
                    status=400,
                )
            when = str(form.get("when") or "").strip()
            message = str(form.get("message") or "")
            priority = str(form.get("priority") or "").strip()
            attachment_path: str | None = None
            voice_note_path: str | None = None
            try:
                attachment_path = await _async_store_optional_attachment(
                    runtime, form.get("attachment")
                )
                voice_note_path = await _async_store_optional_voice_note(
                    runtime, form.get("voice_note")
                )
            except ValueError as err:
                return web.json_response(
                    {"ok": False, "message_text": _random_error_message(str(err))},
                    status=400,
                )
            result = await runtime.async_add_manual_summon_schedule(
                when,
                message,
                priority,
                attachment_path=attachment_path,
                voice_note_path=voice_note_path,
            )
            if not result.get("ok"):
                runtime.discard_upload_paths(attachment_path, voice_note_path)
                reason = str(result.get("reason") or "")
                return web.json_response(
                    {
                        "ok": False,
                        "reason": reason,
                        "message_text": str(
                            result.get("message_text") or "Could not schedule that summon."
                        ),
                    },
                    status=400,
                )
            return web.json_response(
                {
                    "ok": True,
                    "slot_id": result.get("slot_id"),
                    "message_text": str(result.get("message_text") or "Summon scheduled."),
                }
            )

        data = await _parse_request_body(request)
        action = str(data.get("action", "")).strip().lower()
        if action == "schedule_summon":
            when = str(data.get("when") or "").strip()
            message = str(data.get("message") or "")
            priority = str(data.get("priority") or "").strip()
            result = await runtime.async_add_manual_summon_schedule(when, message, priority)
            if not result.get("ok"):
                reason = str(result.get("reason") or "")
                return web.json_response(
                    {
                        "ok": False,
                        "reason": reason,
                        "message_text": str(
                            result.get("message_text") or "Could not schedule that summon."
                        ),
                    },
                    status=400,
                )
            return web.json_response(
                {
                    "ok": True,
                    "slot_id": result.get("slot_id"),
                    "message_text": str(result.get("message_text") or "Summon scheduled."),
                }
            )
        if action == "unschedule_summon":
            slot_id = str(data.get("slot_id") or "").strip()
            result = await runtime.async_remove_manual_summon_schedule(slot_id)
            if not result.get("ok"):
                reason = str(result.get("reason") or "")
                status = 404 if reason == "not_found" else 400
                return web.json_response(
                    {
                        "ok": False,
                        "reason": reason,
                        "message_text": str(
                            result.get("message_text") or "Could not remove that schedule entry."
                        ),
                    },
                    status=status,
                )
            return web.json_response(
                {
                    "ok": True,
                    "message_text": str(
                        result.get("message_text") or "Scheduled summon removed."
                    ),
                }
            )

        event_id = str(data.get("event_id", "")).strip()
        if not event_id:
            return web.json_response(
                {"ok": False, "message_text": "Missing summon id."},
                status=400,
            )

        if action == "delete":
            result = await runtime.async_delete_summon(event_id)
            if result.get("ok"):
                return web.json_response(
                    {
                        "ok": True,
                        "event_id": event_id,
                        "message_text": "Summon deleted.",
                    }
                )
            reason = str(result.get("reason") or "")
            return web.json_response(
                {
                    "ok": False,
                    "message_text": (
                        "Active summons cannot be deleted."
                        if reason == "active_summon"
                        else "Summon not found."
                    ),
                    "reason": reason,
                },
                status=409 if reason == "active_summon" else 404,
            )

        if action == "resend":
            try:
                result = await runtime.async_resend_summon(
                    event_id,
                    voice_note_base_url=_request_base_url(request),
                )
            except HomeAssistantError as err:
                return web.json_response(
                    {"ok": False, "message_text": _random_error_message(str(err))},
                    status=502,
                )
            if not result.accepted and result.disposition == "not_found":
                return web.json_response(
                    {
                        **_trigger_result_payload(result),
                        "message_text": "Summon not found.",
                    },
                    status=404,
                )
            return web.json_response(
                {
                    **_trigger_result_payload(result),
                    "message_text": (
                        _page_success_message() if result.accepted else _page_result_message(result)
                    ),
                },
                status=200 if result.accepted else _trigger_result_status(result),
            )

        return web.json_response(
            {"ok": False, "message_text": "Unknown summon action."},
            status=400,
        )


class LorisSummonPageView(LorisSummonView):
    url = WEB_PATH
    name = "loris_summon:page"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        runtime, error = self._web_page_runtime_or_response(request)
        if error is not None or runtime is None:
            return error
        return _html_page_response(
            await _async_render_web_page(
                self.hass,
                selected_priority=DEFAULT_SUMMON_PRIORITY,
                token_refresh_window_seconds=runtime.web_page_token_refresh_window_seconds(),
            )
        )

    async def post(self, request: web.Request) -> web.Response:
        runtime, claims, error = self._web_token_runtime_or_response(request)
        if error is not None or runtime is None or claims is None:
            return error

        form = await request.post()

        message = str(form.get("message", "")).strip()
        priority = str(form.get("priority", DEFAULT_SUMMON_PRIORITY)
                       ).strip() or DEFAULT_SUMMON_PRIORITY
        result = runtime.preview_trigger(
            message, source="web_page", priority=priority)
        if not result.accepted:
            if _page_prefers_json(request):
                return web.json_response(
                    {
                        **_trigger_result_payload(result),
                        "message_text": _page_result_message(result),
                    },
                    status=_trigger_result_status(result),
                )
            response = _html_page_response(
                await _async_render_web_page(
                    self.hass,
                    message=message,
                    selected_priority=priority,
                    banner_text=_page_result_message(result),
                    banner_kind="error",
                    token_refresh_window_seconds=runtime.web_page_token_refresh_window_seconds(),
                ),
                status=_trigger_result_status(result),
            )
            return response

        attachment_path: str | None = None
        voice_note_path: str | None = None
        try:
            attachment_path = await _async_store_optional_attachment(runtime, form.get("attachment"))
            voice_note_path = await _async_store_optional_voice_note(runtime, form.get("voice_note"))
        except ValueError as err:
            if _page_prefers_json(request):
                return web.json_response(
                    {"ok": False, "message_text": _random_error_message(str(err))},
                    status=400,
                )
            response = _html_page_response(
                await _async_render_web_page(
                    self.hass,
                    message=message,
                    selected_priority=priority,
                    banner_text=_random_error_message(str(err)),
                    banner_kind="error",
                    token_refresh_window_seconds=runtime.web_page_token_refresh_window_seconds(),
                ),
                status=400,
            )
            return response
        try:
            result = await runtime.async_trigger(
                message,
                source="web_page",
                priority=priority,
                attachment_path=attachment_path,
                voice_note_path=voice_note_path,
                voice_note_base_url=_request_base_url(request),
            )
        except HomeAssistantError as err:
            if _page_prefers_json(request):
                return web.json_response(
                    {"ok": False, "message_text": _random_error_message(str(err))},
                    status=502,
                )
            response = _html_page_response(
                await _async_render_web_page(
                    self.hass,
                    message=message,
                    selected_priority=priority,
                    banner_text=_random_error_message(str(err)),
                    banner_kind="error",
                    token_refresh_window_seconds=runtime.web_page_token_refresh_window_seconds(),
                ),
                status=502,
            )
            return response
        if _page_prefers_json(request):
            return web.json_response(
                {
                    **_trigger_result_payload(result),
                    "message_text": (
                        _page_success_message() if result.accepted else _page_result_message(result)
                    ),
                },
                status=200 if result.accepted else _trigger_result_status(
                    result),
            )
        if result.accepted:
            return _html_page_response(
                await _async_render_web_page(
                    self.hass,
                    selected_priority=priority,
                    banner_text=_page_success_message(),
                    banner_kind="success",
                    token_refresh_window_seconds=runtime.web_page_token_refresh_window_seconds(),
                )
            )
        return _html_page_response(
            await _async_render_web_page(
                self.hass,
                selected_priority=priority,
                token_refresh_window_seconds=runtime.web_page_token_refresh_window_seconds(),
            )
        )


class LorisSummonIconView(LorisSummonView):
    url = ICON_PATH
    name = "loris_summon:icon"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        # Serve the icon directly from disk so replacing icon.png updates the page on refresh
        if not await self.hass.async_add_executor_job(WEB_PAGE_ICON_PATH.exists):
            return web.Response(status=404, text="Icon not found")
        return web.Response(
            body=await self.hass.async_add_executor_job(WEB_PAGE_ICON_PATH.read_bytes),
            content_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
            },
        )


class LorisSummonAttachmentFileView(LorisSummonView):
    url = ATTACHMENT_FILE_PATH
    name = "loris_summon:attachment_file"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        runtime, attachment_path, error = self._attachment_path_or_response(request)
        if error is not None or runtime is None or attachment_path is None:
            return error
        return web.Response(
            body=await self.hass.async_add_executor_job(attachment_path.read_bytes),
            content_type=mimetypes.guess_type(str(attachment_path))[0] or "application/octet-stream",
            headers={
                "Cache-Control": "private, max-age=3600",
                "Content-Disposition": f'inline; filename="{attachment_path.name}"',
            },
        )


class LorisSummonVoiceNotePageView(LorisSummonView):
    url = VOICE_NOTE_PLAY_PATH
    name = "loris_summon:voice_note_page"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        runtime, voice_note_path, error = self._voice_note_path_or_response(request)
        if error is not None or runtime is None or voice_note_path is None:
            return error
        player_markup = await _async_render_voice_note_page(
            self.hass,
            runtime.voice_note_file_url_for_request(
                str(request.query.get("event_id") or ""),
                str(request.query.get("token") or ""),
            ),
            voice_note_path.name,
        )
        return _html_page_response(player_markup)


class LorisSummonVoiceNoteFileView(LorisSummonView):
    url = VOICE_NOTE_FILE_PATH
    name = "loris_summon:voice_note_file"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        runtime, voice_note_path, error = self._voice_note_path_or_response(request)
        if error is not None or runtime is None or voice_note_path is None:
            return error
        return web.Response(
            body=await self.hass.async_add_executor_job(voice_note_path.read_bytes),
            content_type=mimetypes.guess_type(str(voice_note_path))[0] or "application/octet-stream",
            headers={
                "Cache-Control": "private, max-age=3600",
                "Content-Disposition": f'inline; filename="{voice_note_path.name}"',
            },
        )


async def _parse_request_body(request: web.Request) -> dict[str, Any]:
    # Accept common webhook content types so simple external integrations can call the endpoint
    if request.can_read_body:
        content_type = request.content_type or ""
        if content_type == "application/json":
            try:
                return await request.json()
            except json.JSONDecodeError:
                return {}
        if content_type.startswith("text/"):
            return {"message": await request.text()}
        if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
            return dict(await request.post())
    return {}


async def _async_store_optional_attachment(
    runtime: LorisSummonRuntime,
    upload: Any,
) -> str | None:
    if not getattr(upload, "filename", ""):
        return None
    return await runtime.async_store_attachment(
        upload.filename,
        upload.file.read(),
        getattr(upload, "content_type", None),
    )


async def _async_store_optional_voice_note(
    runtime: LorisSummonRuntime,
    upload: Any,
) -> str | None:
    if not getattr(upload, "filename", ""):
        return None
    return await runtime.async_store_voice_note(
        upload.filename,
        upload.file.read(),
        getattr(upload, "content_type", None),
    )


def _extract_message(data: dict[str, Any]) -> str:
    # Support a few obvious field names so callers do not need a rigid payload contract
    for key in ("text", "message", "content"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_source(data: dict[str, Any], default: str) -> str:
    value = data.get("source")
    return value.strip() if isinstance(value, str) and value.strip() else default


def _extract_priority(data: dict[str, Any]) -> Any:
    # Pass through raw priority input so the runtime can normalize labels and numeric values centrally
    return data.get(ATTR_PRIORITY, DEFAULT_SUMMON_PRIORITY)


def _extract_bearer_token(request: web.Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def _extract_web_page_token(
    request: web.Request,
    *,
    allow_query_token: bool = False,
) -> str | None:
    # Accept bearer auth for fetch calls and a query token for EventSource
    token = _extract_bearer_token(request)
    if token:
        return token
    if allow_query_token:
        query_token = str(request.query.get("access_token") or "").strip()
        if query_token:
            return query_token
    return None


def _request_base_url(request: web.Request) -> str | None:
    host = str(request.host or "").strip()
    if not host:
        return None
    return f"{request.scheme}://{host}".rstrip("/")


def _web_page_auth_error_response(*, stream: bool = False) -> web.Response:
    # Return one consistent auth failure shape so the browser can fall back to login cleanly
    if stream:
        return web.Response(status=401, text="Unauthorized")
    return web.json_response(
        {
            "ok": False,
            "login_url": WEB_PATH,
            "session_expired": True,
            "message_text": "Session expired. Sign in again.",
        },
        status=401,
    )


def _html_page_response(markup: str, status: int = 200) -> web.Response:
    # Disable browser caching so page edits show up on refresh during integration development
    return web.Response(
        text=markup,
        status=status,
        content_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


async def _async_render_voice_note_page(
    hass: HomeAssistant,
    audio_url: str,
    filename: str,
) -> str:
    escaped_audio_url = html.escape(audio_url, quote=True)
    escaped_filename = html.escape(filename)
    template = await hass.async_add_executor_job(
        lambda: VOICE_NOTE_PAGE_TEMPLATE_PATH.read_text(encoding="utf-8")
    )
    return (
        template.replace("__VOICE_NOTE_AUDIO_URL__", escaped_audio_url)
        .replace("__VOICE_NOTE_FILENAME__", escaped_filename)
    )


def _page_prefers_json(request: web.Request) -> bool:
    # Let the browser page fetch JSON while keeping plain form posts as a fallback
    accept = request.headers.get("Accept", "")
    return request.headers.get("X-Requested-With") == "fetch" or "application/json" in accept


def _page_result_message(result: TriggerResult) -> str:
    # Keep summon rejection copy aligned across the browser surfaces
    return _random_error_message(_result_error_reason(result))


def _page_success_message() -> str:
    return _random_success_message()


async def _async_render_web_page(
    hass: HomeAssistant,
    message: str = "",
    selected_priority: str = DEFAULT_SUMMON_PRIORITY,
    banner_text: str | None = None,
    banner_kind: str = "success",
    token_refresh_window_seconds: int = 0,
) -> str:
    # Read the page template from disk so frontend edits do not depend on Python module reloads
    escaped_message = html.escape(message)
    priority_options = _render_priority_options(selected_priority)
    placeholder_text = html.escape(_web_page_placeholder_text(), quote=True)
    placeholder_messages = json.dumps(WEB_PLACEHOLDERS)
    success_messages = json.dumps(SUCCESS_MESSAGES)
    error_messages = json.dumps(ERROR_MESSAGES)
    initial_toast = (
        json.dumps({"text": banner_text, "kind": banner_kind})
        if banner_text
        else "null"
    )
    template = await hass.async_add_executor_job(
        lambda: WEB_PAGE_TEMPLATE_PATH.read_text(encoding="utf-8")
    )
    return (
        template.replace("__PLACEHOLDER_TEXT__", placeholder_text)
        .replace("__ESCAPED_MESSAGE__", escaped_message)
        .replace("__PRIORITY_OPTIONS__", priority_options)
        .replace("__PLACEHOLDER_MESSAGES__", placeholder_messages)
        .replace("__SUCCESS_MESSAGES__", success_messages)
        .replace("__ERROR_MESSAGES__", error_messages)
        .replace("__INITIAL_TOAST__", initial_toast)
        .replace("__ICON_PATH__", ICON_PATH)
        .replace("__STATUS_PATH__", STATUS_PATH)
        .replace("__STATUS_STREAM_PATH__", STATUS_STREAM_PATH)
        .replace("__VOICE_NOTES_PATH__", VOICE_NOTES_PATH)
        .replace("__WEB_LOGIN_PATH__", WEB_LOGIN_PATH)
        .replace("__WEB_REFRESH_PATH__", WEB_REFRESH_PATH)
        .replace("__TOKEN_REFRESH_WINDOW_SECONDS__", str(token_refresh_window_seconds))
    )


def _render_priority_options(selected_priority: str) -> str:
    # Keep the priority selector server rendered so non JavaScript form posts stay correct
    normalized_priority = str(selected_priority).strip(
    ).lower() or DEFAULT_SUMMON_PRIORITY
    if normalized_priority not in WEB_PRIORITY_VALUES:
        normalized_priority = DEFAULT_SUMMON_PRIORITY
    return "".join(
        f'<option value="{value}"{" selected" if value == normalized_priority else ""}>{label}</option>'
        for value, label in WEB_PRIORITY_OPTIONS
    )


def _web_page_placeholder_text() -> str:
    # Pick a fresh prompt on each page render so the form feels less static
    return random.choice(WEB_PLACEHOLDERS)


def _random_success_message() -> str:
    # Reuse the same message pool across the browser surfaces so the summon voice stays consistent
    return random.choice(SUCCESS_MESSAGES)


def _random_error_message(reason: str) -> str:
    # Reuse the same summon failure copy across the browser surfaces
    return f"{random.choice(ERROR_MESSAGES)} (Reason: {_human_error_reason(reason)})"


async def _async_write_sse_event(
    response: web.StreamResponse,
    event_name: str,
    payload: dict[str, Any],
) -> None:
    # Send JSON snapshots as SSE frames so the browser can react without polling
    body = (
        f"event: {event_name}\n"
        f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    ).encode("utf-8")
    await response.write(body)


def _human_error_reason(reason: str) -> str:
    # Normalize internal reason codes before surfacing them to people
    normalized = reason.strip().lower().replace("_", " ")
    return {
        "invalid": "empty command",
        "invalid priority": "invalid priority",
        "rate limited": "rate limit",
        "attachment is empty": "attachment was empty",
        "attachment is not a supported image or video": "attachment must be an image or video file",
        "attachment exceeds the 95 mb upload limit": "attachment exceeds the 95 MB upload limit",
        "voice note is empty": "voice note was empty",
        "voice note is not a supported audio file": "voice note must be an audio file",
        "voice note exceeds the 75 mb upload limit": "voice note exceeds the 75 MB upload limit",
        "voice note not found": "voice note was not found",
        "no voice note": "no saved voice note exists for that summon",
        "not found": "summon was not found",
        "active summon": "the summon is still active",
        "delivery failed": "pushover delivery failed",
        "invalid subscription": "browser subscription payload was invalid",
        "invalid keys": "browser subscription keys were invalid",
        "invalid body": "request body was invalid",
    }.get(normalized, normalized or "unknown")


def _result_error_reason(result: TriggerResult) -> str:
    # Convert trigger results into short stable reasons for user facing failure messages
    return _human_error_reason(result.disposition)


def _trigger_result_payload(result: TriggerResult) -> dict[str, Any]:
    # Return a compact machine readable response for external API callers
    payload = {
        "ok": result.accepted,
        "disposition": result.disposition,
        "message": result.message,
        "priority": result.priority,
        "source": result.source,
    }
    if result.event_id is not None:
        payload["event_id"] = result.event_id
    if result.cooldown_until is not None:
        payload["cooldown_until"] = result.cooldown_until
    if result.rate_limited_until is not None:
        payload["rate_limited_until"] = result.rate_limited_until
    return payload


def _trigger_result_status(result: TriggerResult) -> int:
    # Surface invalid payloads separately from throttling so callers can react correctly
    if result.accepted:
        return 200
    if result.disposition in {"invalid", "invalid_priority"}:
        return 400
    if result.disposition in {"cooldown", "rate_limited"}:
        return 429
    return 409
