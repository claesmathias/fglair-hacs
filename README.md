# FGLair — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/claesmathias/fglair-hacs)](https://github.com/claesmathias/fglair-hacs/releases)
[![License](https://img.shields.io/github/license/claesmathias/fglair-hacs)](LICENSE)

A HACS custom integration for **Fujitsu FGLair** and **Hisense** air conditioners. Controls your AC units via the Ayla Networks cloud API — the same backend used by the official FGLair and Hisense apps.

---

## Supported hardware

| Model pattern | Series | Notes |
|---|---|---|
| `AP-W[ACDF]nE` (e.g. AP-WD1E, AP-WF2E) | Fujitsu FGLair | Full support incl. swing |
| `AP-WBnE` | Fujitsu FGLair B-series | Full support |
| AEH-W4B1 / AEH-W4E1 based units | Hisense AC | Full support incl. swing |

Any unit that can be controlled via the official **FGLair** or **Hisense Home** mobile app should work.

---

## Prerequisites

- An active account in the **FGLair** or **Hisense Home** app
- Your AC unit(s) already connected and visible in the app
- Home Assistant 2024.1 or newer

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/claesmathias/fglair-hacs` with category **Integration**
3. Search for **FGLair** and click **Download**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/fujitsu_airstage` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **FGLair**
3. Enter your credentials and select the correct app / region:

| App | Region | Use if… |
|---|---|---|
| **Fujitsu FGLair (EU)** | Europe | You use the FGLair app in Europe |
| **Fujitsu FGLair (US)** | United States | You use the FGLair app in the US |
| **Hisense (EU)** | Europe | You use the Hisense Home app in Europe |
| **Hisense (US)** | United States | You use the Hisense Home app in the US |

---

## Features

Each AC unit is exposed as a **Climate** entity with the following controls:

| Feature | FGLair / FGLair-B | Hisense AC |
|---|---|---|
| HVAC modes | off / auto / cool / heat / dry / fan only | off / auto / cool / heat / dry / fan only |
| Fan modes | auto / quiet / low / medium / high | auto / lower / low / medium / high / higher |
| Swing (vertical) | ✅ on / off | ✅ on / off |
| Target temperature | 16–30 °C (1 °C steps) | 16–30 °C (1 °C steps) |
| Current temperature | ✅ (indoor sensor) | ✅ (indoor sensor) |
| Polling interval | 30 seconds | 30 seconds |

---

## Troubleshooting

### Integration not found after install
Make sure you restarted Home Assistant after copying the files or installing via HACS.

### Authentication fails
- Double-check your email and password — use the same credentials as the mobile app.
- EU and US accounts are on separate servers; make sure you selected the correct region.

### Temperature shows as 0 °C or very wrong value
Open an issue with your device's `oem_model` value (visible in the device info page in HA).

### Cannot connect / timeout
The integration uses the Ayla Networks cloud API. If the cloud is unreachable (e.g. maintenance), polling will fail until connectivity is restored. Check the HA logs for details.

### Logs
Enable debug logging by adding this to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.fujitsu_airstage: debug
```

---

## Credits

Protocol and authentication details derived from the excellent [deiger/AirCon](https://github.com/deiger/AirCon) project. Temperature encoding formulas verified against the FGLair 3.4.2 APK.

---

## License

MIT — see [LICENSE](LICENSE).
