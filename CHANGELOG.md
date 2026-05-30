# Changelog

All notable changes to this project will be documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
