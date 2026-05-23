![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

<p align="center">
  <img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/icon.png" width="180" alt="Plugin Icon"/>
</p>

<p align="center">
  <strong>Ecowitt Weather Station</strong> is an <a href="https://www.indigodomo.com">Indigo Domotics</a> plugin that receives live weather data directly from your Ecowitt gateway over your local network — no cloud, no third-party account required.
</p>

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## What it does

The plugin runs a lightweight HTTP server inside Indigo. Your Ecowitt gateway is configured to POST its sensor readings to that server every 16–60 seconds using the **Ecowitt local push protocol**. Every reading becomes an Indigo device state, available immediately for use in triggers, schedules, control pages, and scripts.

- **No cloud dependency** — data flows directly from gateway to Mac over your LAN
- **All sensors in one device** — a single *Ecowitt Gateway Hub* device holds every state from every sensor attached to that gateway
- **Dynamic states** — new sensors appear automatically the first time their data is received; you never need to edit XML
- **Units your way** — choose Imperial or Metric; the plugin picks the right value when aioecowitt provides both
- **Multiple gateways** — add one Hub device per gateway; each is routed by its unique PASSKEY

---

## Supported Hardware

### Gateways / Hubs
| Model | Notes |
|---|---|
| GW1200 | Wi-Fi gateway |
| GW2000 | Ethernet + Wi-Fi gateway |
| GW3000 | Ethernet + Wi-Fi with on-board data storage |
| HP2560 / HP2564 | Console display hubs |

Any Ecowitt gateway that supports the **Customized / Ecowitt protocol** upload will work.

### Sensors (examples)
WS90 · WH65 · WH40 · WH57 · WH51 · WH31 · WH55 · WH41 · WH43 · WH45 · WH46 · WN34 · WH80 · WH68 · WH85 · WH25 · WH26

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Wiki Pages

| Page | Description |
|---|---|
| [Installation](Installation) | Download, install, and first launch |
| [Plugin Configuration](Plugin-Configuration) | Port, path, units, debug logging |
| [Ecowitt Gateway Setup](Ecowitt-Gateway-Setup) | Configure your gateway to push data — app and web UI methods, per-model notes |
| [Device Setup](Device-Setup) | Creating Hub devices, PASSKEY routing, multiple gateways |
| [Sensor States Reference](Sensor-States-Reference) | Complete list of all states by sensor category |
| [Code Architecture](Code-Architecture) | How the plugin works — asyncio, dynamic states, unit priority |
| [Troubleshooting](Troubleshooting) | Common problems and diagnostic steps |

---

## Quick Start

```
1. Install the plugin  →  Installation
2. Configure plugin    →  Plugin Configuration (set port, units)
3. Configure gateway   →  Ecowitt Gateway Setup (WSView Plus / web UI)
4. Create Hub device   →  Device Setup
5. Wait for first push — states appear automatically
```

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Requirements

- **Indigo** 2025.2 or later (API 3.4+)
- **macOS** with Indigo running on the same LAN as the gateway
- An Ecowitt gateway with firmware supporting Customized upload (all current models do)
- [`aioecowitt`](https://github.com/home-assistant-libs/aioecowitt) ≥ 2025.9.2 — installed automatically by Indigo from `requirements.txt`

---

*Plugin by [Glenn Hawken](https://github.com/Ghawken) · Uses [aioecowitt](https://github.com/home-assistant-libs/aioecowitt) by the Home Assistant team · Dynamic state pattern from [GhostXML](https://github.com/IndigoDomotics/GhostXML)*
