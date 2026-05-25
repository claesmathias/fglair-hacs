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
    "hisense-eu": "Hisense (EU)",
    "hisense-us": "Hisense (US)",
}

# Device type detection patterns
FGL_MODEL_RE = r"AP-W[ACDF]\dE"
FGLB_MODEL_RE = r"AP-WB\dE"

# FGL / FGLb temperature: API stores tenths of degrees (210 = 21.0 °C)
FGL_TEMP_SCALE = 10.0

# FglOperationMode int → HA HVACMode string
FGL_MODE_TO_HA = {
    0: "off",
    1: "auto",   # "ON" power state — treat as auto
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
