# Changelog

All notable changes to this project will be documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.5.0] — 2026-11-07

Aligned with the FGLair 3.4.3 Android app.

### Added
- **Fujitsu FGLair (China)** app/region option (`FGLair-cn` credentials, `ayla.com.cn` servers)
- B-series (`AP-WB*`) swing control via `af_vertical_move_step1`, which is how the app does it on these units
- HVAC modes, fan speeds and swing support now follow the unit's `device_capabilities` bitmask
- `minimum_heat` attribute; while Minimum Heat is active the target shows 10 °C, and choosing Heat leaves it by writing the 24 °C basic setpoint, as the app does

### Changed
- Target temperature step is 0.5 °C on A/F-template units (AP-WA/WC/WD/WF) and stays 1 °C on B-series
- Minimum setpoint is 18 °C in auto/cool/dry/fan and 16 °C in heat, matching the app's per-mode ranges
- `operation_mode = 1` (the transient value right after power-on) now reads as **off** instead of auto, matching the app
- Model names with a `-dev` suffix are recognised

### Fixed
- `display_temperature` decoding for sub-zero values (truncate instead of floor), and out-of-table values now read as unknown
- FGLair units on the US app were labelled °F although the cloud reports °C; they now report °C and HA converts
- B-series units no longer show a room temperature or get a `get_prop` refresh write every poll, since the app shows neither for them

---

## [1.4.1] — 2026-06-16

### Fixed
- Offline error message now shows the device DSN instead of the entity name (avoids `AttributeError` in edge cases where the entity name is not yet resolved)

### Added
- Full unit test suite (68 tests) covering mode/fan mappings, temperature conversion, API retry logic, coordinator offline detection, and climate entity command guards

---

## [1.4.0] — 2026-06-16

### Fixed
- Entity is now marked **Unavailable** in HA when the AC's WiFi module is offline — prevents stale state being shown as if commands were applied
- All commands (set mode, temperature, fan, swing, turn on/off) now raise a visible error notification when the device is offline instead of silently writing to the Ayla cloud cache
- Device connection status is refreshed on every poll cycle via the Ayla device list endpoint

---

## [1.3.0] — 2026-05-30

### Fixed
- Current temperature now refreshes automatically every poll cycle — writes `get_prop = 1` after each read to ask the AC unit to push a fresh `display_temperature` to the Ayla cloud, matching the behaviour of the refresh button in the official FGLair app

---

## [1.2.0] — 2026-05-30

### Fixed
- Turn-on command now sends `operation_mode = 1` (the wake/ON signal the device expects) instead of `2` (AUTO), which the device rejects when powered off — matching the behaviour of the official FGLair app

---

## [1.1.0] — 2026-05-30

### Added
- HTTP timeout (15 s) on all cloud API requests
- Automatic retry (up to 3 attempts, exponential backoff) on transient errors such as connection resets and timeouts
- `temperature_last_updated` state attribute on climate entities — shows the exact timestamp the AC unit last pushed a temperature reading to the Ayla cloud

---

## [1.0.0] — 2026-05-25

### Added
- Initial release
- Cloud polling via the Ayla Networks REST API (same backend as the official FGLair and Hisense apps)
- Support for three device families: Fujitsu FGLair (`AP-W[ACDF]nE`), FGLair B-series (`AP-WBnE`), and Hisense AC
- Climate entity per device with HVAC modes, fan modes, swing, target temperature, and current temperature
- Config flow with username / password and region selector (FGLair EU/US, Hisense EU/US)
- Automatic token refresh on 401 — no manual re-authentication needed
- Correct `display_temperature` decoding (lookup-table formula derived from FGLair 3.4.2 APK)
- Brand icons in `brand/` directory for HA integrations panel
