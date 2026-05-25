# Changelog

All notable changes to this project will be documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
