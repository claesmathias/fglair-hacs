DOMAIN = "fujitsu_airstage"
DEFAULT_SCAN_INTERVAL = 30

CONF_APP = "app"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Ayla Networks region servers
AYLA_USER_SERVERS = {
    "us": "user-field.aylanetworks.com",
    "eu": "user-field-eu.aylanetworks.com",
    "cn": "user-field.ayla.com.cn",
}
AYLA_DEVICES_SERVERS = {
    "us": "ads-field.aylanetworks.com",
    "eu": "ads-eu.aylanetworks.com",
    "cn": "ads-field.ayla.com.cn",
}

# Apps: prefix used to build app_id / app_secret, secret bytes from the official apps
APP_CONFIGS = {
    "fglair-eu": {
        "prefix": "FGLair-eu",
        "secret": b"\x82\x91[T\x14h\x88\x9f\x04\xdd\x05\x89\xf9\x04T,\xb2\xf7\x8fu",
        "region": "eu",
        "celsius": True,
    },
    "fglair-us": {
        "prefix": "CJIOSP",
        "secret": b"U\xbf\x0c@\xbf\xe5\x16&\x10\xec2\xa37G\x82\x15|\xe7)\x91",
        "region": "us",
        "celsius": False,
    },
    "fglair-cn": {
        "prefix": "FGLair-cn",
        "secret": b"s\xd61\xc0\x82\xa0\xac|Vw\xf8\x83o\x01\xee\xd6J\xfb!\xdf",
        "region": "cn",
        "celsius": True,
    },
    "hisense-eu": {
        "prefix": "Hisense",
        "secret": b"\xc0\xedK,\xff+X\xfa\xf6p\x87\xaa\xbcV\x88\xfbI\xb4\xcf\xad",
        "region": "eu",
        "celsius": True,
    },
    "hisense-us": {
        "prefix": "APP1",
        "secret": b"x\x04\xdf\xef6\x08\x8e\x06\n\x97\xfc\xed4m\xd8\xc7\xa3=\xce\x9f",
        "region": "us",
        "celsius": False,
    },
}

APP_LABELS = {
    "fglair-eu": "Fujitsu FGLair (EU)",
    "fglair-us": "Fujitsu FGLair (US)",
    "fglair-cn": "Fujitsu FGLair (China)",
    "hisense-eu": "Hisense (EU)",
    "hisense-us": "Hisense (US)",
}

# Device type detection patterns (FGLair app template_types.js):
#   template A: AP-WA1E..WA6E, AP-WC1E..WC4E, AP-WD1E
#   template F: AP-WF1E..WF4E
#   template B: AP-WB1E..WB4E  ("fglb" — different swing properties, 1 °C steps, no room temp)
FGL_MODEL_RE = r"AP-W[ACDF]\dE"
FGLB_MODEL_RE = r"AP-WB\dE"

# FGL / FGLb temperature: API stores tenths of degrees Celsius (210 = 21.0 °C),
# regardless of the app's display unit.
FGL_TEMP_SCALE = 10.0

# Setpoint step (adjust_temperature units): template B = 10 (1 °C), A/F = 5 (0.5 °C)
FGL_TEMP_STEP = 0.5
FGLB_TEMP_STEP = 1.0

# Setpoint range per mode (operation_modes.js): heat 16–30 °C, everything else 18–30 °C
FGL_MIN_TEMP_HEAT = 16.0
FGL_MIN_TEMP = 18.0
FGL_MAX_TEMP = 30.0

# Minimum Heat (min_heat = 1): unit holds a fixed 10 °C, setpoint not adjustable.
# Leaving it for normal heat: the app writes adjust_temperature = 240 (24 °C).
FGL_MIN_HEAT_TEMP = 10.0
FGL_HEAT_BASIC_ADJUST = 240

# display_temperature lookup table range (temperatures.js): 4000 (-10 °C) .. 9500 (45 °C)
FGL_DISPLAY_MIN = 4000
FGL_DISPLAY_MAX = 9500

# device_capabilities bitmask (device_capabilities.js / air_volumes.js)
FGL_CAP_MODES = {
    "cool": 1 << 0,
    "dry": 1 << 1,
    "fan_only": 1 << 2,
    "heat": 1 << 3,
    "auto": 1 << 4,
}
FGL_CAP_FANS = {
    "auto": 1 << 5,
    "high": 1 << 6,
    "medium": 1 << 7,
    "low": 1 << 8,
    "quiet": 1 << 9,
}
FGL_CAP_VERTICAL_SWING = 1 << 10
FGL_CAP_MIN_HEAT = 1 << 13

# FglOperationMode int → HA HVACMode string
FGL_MODE_TO_HA = {
    0: "off",
    1: "off",    # "ON" wake command; the app treats it as off until the unit restores its mode
    2: "auto",
    3: "cool",
    4: "dry",
    5: "fan_only",
    6: "heat",
}
HA_MODE_TO_FGL = {
    "off": 0,
    "auto": 2,
    "cool": 3,
    "dry": 4,
    "fan_only": 5,
    "heat": 6,
}

# FglFanSpeed int → HA fan_mode string
FGL_FAN_TO_HA = {
    0: "quiet",
    1: "low",
    2: "medium",
    3: "high",
    4: "auto",
}
HA_FAN_TO_FGL = {v: k for k, v in FGL_FAN_TO_HA.items()}

# AcWorkMode int → HA HVACMode string
AC_MODE_TO_HA = {
    0: "fan_only",
    1: "heat",
    2: "cool",
    3: "dry",
    4: "auto",
}
HA_MODE_TO_AC = {v: k for k, v in AC_MODE_TO_HA.items()}

# AcFanSpeed int → HA fan_mode string
AC_FAN_TO_HA = {
    0: "auto",
    5: "lower",
    6: "low",
    7: "medium",
    8: "high",
    9: "higher",
}
HA_FAN_TO_AC = {v: k for k, v in AC_FAN_TO_HA.items()}
