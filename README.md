# FGLair Home Assistant Integration

A HACS custom integration for **Fujitsu FGLair** and **Hisense** air conditioners using the Ayla Networks cloud API.

## Supported hardware

| Model pattern | Type |
|---|---|
| `AP-W[ACDF]nE` (e.g. AP-WD1E, AP-WF2E) | Fujitsu FGLair |
| `AP-WBnE` | Fujitsu FGLair B-series |
| Other AEH-W4B1 / AEH-W4E1 based units | Hisense AC |

## Installation via HACS

1. Open HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Search for **FGLair** and install
4. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **FGLair**
3. Enter your FGLair or Hisense app credentials and choose your region

| App | Region |
|---|---|
| Fujitsu FGLair (EU) | `fglair-eu` |
| Fujitsu FGLair (US) | `fglair-us` |
| Hisense (EU) | `hisense-eu` |
| Hisense (US) | `hisense-us` |

## Features

- **HVAC modes**: off / cooling / heating / dry / fan only / auto
- **Fan modes**: auto / quiet / low / medium / high
- **Swing**: vertical swing on/off (FGL devices)
- **Target temperature**: 16–30 °C in 1 °C steps
- **Current temperature**: read from the indoor unit sensor
- **Polling interval**: 30 seconds

## Notes on temperature scaling

FGLair firmware stores temperatures as tenths of degrees (e.g. `210` = 21.0 °C).
This integration divides API values by 10 before displaying them. If your temperatures
look wrong (10× too high or low), please open an issue.

## Credits

Protocol and authentication details derived from the excellent
[deiger/AirCon](https://github.com/deiger/AirCon) project.
