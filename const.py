"""Constants for the Lori's Summon integration."""

DOMAIN = "loris_summon"
PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_ALERT_TITLE = "alert_title"
CONF_ALIVE_CHECKS_PER_DAY = "alive_checks_per_day"
CONF_API_TOKEN = "api_token"
CONF_COOLDOWN_SECONDS = "cooldown_seconds"
CONF_DEBUG_LOGGING = "debug_logging"
CONF_ENABLE_WEB = "enable_web"
CONF_HISTORY_SIZE = "history_size"
CONF_LIGHT_FLASH_BRIGHTNESS = "light_flash_brightness"
CONF_LIGHT_FLASH_COLOR = "light_flash_color"
CONF_LIGHT_FLASH_COUNT = "light_flash_count"
CONF_LIGHT_FLASH_DURATION = "light_flash_duration"
CONF_LIGHT_TARGET = "light_target"
CONF_MAX_TRIGGERS_PER_WINDOW = "max_triggers_per_window"
CONF_MESSAGE_TEMPLATE = "message_template"
CONF_PUSHOVER_APP_TOKEN = "pushover_app_token"
CONF_PUSHOVER_DEVICE = "pushover_device"
CONF_PUSHOVER_SOUND_DEFAULT = "pushover_sound_default"
CONF_PUSHOVER_SOUND_EMERGENCY = "pushover_sound_emergency"
CONF_PUSHOVER_SOUND_LOW = "pushover_sound_low"
CONF_PUSHOVER_SOUND_LOWEST = "pushover_sound_lowest"
CONF_PUSHOVER_SOUND_NORMAL = "pushover_sound_normal"
CONF_PUSHOVER_USER_KEY = "pushover_user_key"
CONF_RATE_LIMIT_WINDOW_SECONDS = "rate_limit_window_seconds"
CONF_TRIGGER_LIGHTS = "trigger_lights"
CONF_WEB_PASSWORD = "web_password"
CONF_WEB_USERNAME = "web_username"

DEFAULT_ALERT_TITLE = "Lori's Summon"
DEFAULT_ALIVE_CHECKS_PER_DAY = 2
DEFAULT_COOLDOWN_SECONDS = 30
DEFAULT_DEBUG_LOGGING = False
DEFAULT_ENABLE_WEB = False
DEFAULT_HISTORY_SIZE = 25
DEFAULT_LIGHT_FLASH_BRIGHTNESS = 255
DEFAULT_LIGHT_FLASH_COLOR = [255, 0, 0]
DEFAULT_LIGHT_FLASH_COUNT = 3
DEFAULT_LIGHT_FLASH_DURATION = 1.0
DEFAULT_MAX_TRIGGERS_PER_WINDOW = 5
DEFAULT_MESSAGE_TEMPLATE = "{{ message }}"
DEFAULT_PUSHOVER_APP_TOKEN = ""
DEFAULT_PUSHOVER_DEVICE = ""
DEFAULT_PUSHOVER_SOUND_DEFAULT = ""
DEFAULT_PUSHOVER_SOUND_EMERGENCY = ""
DEFAULT_PUSHOVER_SOUND_LOW = ""
DEFAULT_PUSHOVER_SOUND_LOWEST = ""
DEFAULT_PUSHOVER_SOUND_NORMAL = ""
DEFAULT_PUSHOVER_USER_KEY = ""
DEFAULT_PUSHOVER_EMERGENCY_EXPIRE = 300
DEFAULT_PUSHOVER_EMERGENCY_RETRY = 30
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 300
DEFAULT_SUMMON_MESSAGE = "You are summoned. Report immediately."
DEFAULT_SUMMON_PRIORITY = "emergency"
DEFAULT_TRIGGER_LIGHTS = True
DEFAULT_WEB_PASSWORD = ""
DEFAULT_WEB_USERNAME = ""

ATTR_ACKNOWLEDGED_AT = "acknowledged_at"
ATTR_ACKNOWLEDGED_BY = "acknowledged_by"
ATTR_ACTIVE = "active"
ATTR_ATTACHMENT_PATH = "attachment_path"
ATTR_COOLDOWN_UNTIL = "cooldown_until"
ATTR_DISPOSITION = "disposition"
ATTR_EMERGENCY_ACKNOWLEDGED_AFTER_SECONDS = "emergency_acknowledged_after_seconds"
ATTR_EVENT_ID = "event_id"
ATTR_EVENT_KIND = "event_kind"
ATTR_HISTORY = "history"
ATTR_PUSHOVER_TITLE = "pushover_title"
ATTR_LAST_TRIGGERED_AT = "last_triggered_at"
ATTR_MESSAGE = "message"
ATTR_NEXT_REMINDER_AT = "next_reminder_at"
ATTR_PENDING_ACK = "pending_ack"
ATTR_PRIORITY = "priority"
ATTR_PUSHOVER_ACKNOWLEDGED = "pushover_acknowledged"
ATTR_PUSHOVER_ACKNOWLEDGED_AT = "pushover_acknowledged_at"
ATTR_PUSHOVER_ACKNOWLEDGED_BY = "pushover_acknowledged_by"
ATTR_PUSHOVER_ACKNOWLEDGED_BY_DEVICE = "pushover_acknowledged_by_device"
ATTR_PUSHOVER_EXPIRED = "pushover_expired"
ATTR_PUSHOVER_EXPIRES_AT = "pushover_expires_at"
ATTR_PUSHOVER_LAST_DELIVERED_AT = "pushover_last_delivered_at"
ATTR_PUSHOVER_RECEIPT = "pushover_receipt"
ATTR_RATE_LIMITED_UNTIL = "rate_limited_until"
ATTR_REMINDER_COUNT = "reminder_count"
ATTR_SOURCE = "source"
ATTR_TRIGGERED_AT = "triggered_at"
ATTR_VOICE_NOTE_PATH = "voice_note_path"
ATTR_VOICE_NOTE_BASE_URL = "voice_note_base_url"

PUSHOVER_PRIORITY_DEFAULT = "normal"
PUSHOVER_PRIORITY_EMERGENCY = "emergency"
PUSHOVER_PRIORITY_LOW = "low"
PUSHOVER_PRIORITY_LOWEST = "lowest"
PUSHOVER_PRIORITY_NORMAL = "high"

EVENT_ACKNOWLEDGED = "loris_summon_acknowledged"
EVENT_TRIGGERED = "loris_summon_triggered"

SERVICE_ACKNOWLEDGE = "acknowledge"
SERVICE_TRIGGER = "trigger"
SERVICE_TEST_ACTIONS = "test_actions"
SERVICE_REGENERATE_WEB_PUSH_KEYS = "regenerate_web_push_keys"

ACKNOWLEDGE_PATH = "/api/loris_summon/acknowledge"
ATTACHMENT_FILE_PATH = "/api/loris_summon/attachment/file"
ATTACHMENT_UPLOAD_MAX_BYTES = 95 * 1024 * 1024
ICON_PATH = "/api/loris_summon/icon.png"
PUSHOVER_CALLBACK_PATH = "/api/loris_summon/pushover/callback"
STATUS_PATH = "/api/loris_summon/status"
STATUS_STREAM_PATH = "/api/loris_summon/status/stream"
TRIGGER_PATH = "/api/loris_summon/trigger"
VOICE_NOTES_PATH = "/api/loris_summon/voice_notes"
VOICE_NOTE_FILE_PATH = "/api/loris_summon/voice_note/file"
VOICE_NOTE_PLAY_PATH = "/api/loris_summon/voice_note"
WEB_PATH = "/api/loris_summon/web"
WEB_LOGIN_PATH = "/api/loris_summon/web/login"
WEB_REFRESH_PATH = "/api/loris_summon/web/refresh"
ALIVE_PATH = "/api/loris_summon/alive"

DISPATCH_STATE_UPDATED = "loris_summon_state_updated"

EVENT_KIND_ALIVE = "alive_check"
ALIVE_CHECK_TITLE = "Alive Check"
ALIVE_CHECK_MESSAGE = (
    "Please acknowledge that you are still alive."
)
ALIVE_SOURCE_SCHEDULE = "alive_schedule"
ALIVE_SOURCE_MANUAL = "alive_manual"
ALIVE_SOURCE_MANUAL_PLANNED = "alive_manual_planned"
ALIVE_MANUAL_SCHEDULE_MAX_MESSAGE_LEN = 500
ALIVE_MANUAL_SCHEDULE_MAX_PENDING = 20
ALIVE_MANUAL_SCHEDULE_MAX_LEAD_DAYS = 14

STORE_SUMMON_SCHEDULE = "summon_schedule"
SUMMON_SOURCE_SCHEDULED = "summon_scheduled"
SUMMON_SCHEDULE_MAX_MESSAGE_LEN = 2000
SUMMON_SCHEDULE_MAX_PENDING = 20
SUMMON_SCHEDULE_MAX_LEAD_DAYS = 14
ALIVE_SCHEDULE_MIN_PER_DAY = 1
ALIVE_SCHEDULE_MAX_PER_DAY = 24

STORE_ALIVE_HISTORY = "alive_history"
STORE_ALIVE_WATCHED_EVENTS = "alive_watched_events"
STORE_ALIVE_ACTIVE_EVENT_ID = "alive_active_event_id"
STORE_ALIVE_SCHEDULE = "alive_schedule"

# Legacy JSON-store keys (migrated to on-disk PEM / public key files on load).
STORE_WEB_PUSH_VAPID_PRIVATE = "web_push_vapid_private_pem"
STORE_WEB_PUSH_VAPID_PUBLIC = "web_push_vapid_public_b64u"
STORE_WEB_PUSH_SUBSCRIPTIONS = "web_push_subscriptions"

WEB_PUSH_KEYS_DIR_NAME = "webpush"
WEB_PUSH_VAPID_PRIVATE_FILENAME = "vapid_private.pem"
WEB_PUSH_VAPID_PUBLIC_FILENAME = "vapid_public.b64u"

WEB_PUSH_VAPID_SUB = "mailto:loris-summon-webpush@invalid"
WEB_PUSH_MAX_SUBSCRIPTIONS = 10

WEB_PUSH_VAPID_PATH = "/api/loris_summon/webpush/vapid"
WEB_PUSH_SUBSCRIBE_PATH = "/api/loris_summon/webpush/subscribe"
WEB_PUSH_UNSUBSCRIBE_PATH = "/api/loris_summon/webpush/unsubscribe"
WEB_PUSH_SW_PATH = "/api/loris_summon/webpush/sw.js"
WEB_PUSH_SW_SCOPE = "/api/loris_summon/"
