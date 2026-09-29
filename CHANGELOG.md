# Changelog

All notable changes to the Ecowitt Weather Station Indigo plugin.

---

## [1.1.1] — 2026-09-30

### Added
- WN38 Black Globe Thermometer support (resolves [#1](https://github.com/Ghawken/EcowittWeather/issues/1))
  - `blackGlobeTemp` — Black Globe Temperature (°F / °C)
  - `wetBulbGlobeTemp` — Wet Bulb Globe Temperature / WBGT index (°F / °C)
  - `bgtBatt` — WN38 battery level
- `bgt` / `bgtc` and `wbgt` / `wbgtc` added to imperial/metric variant key sets so unit preference is respected correctly

---

## [1.1.0] — 2026-05-27

### Fixed
- `ServerApiVersion` corrected from `3.4.0` to `3.4` — three-part version string caused silent load failures and misleading "Info.plist not found" errors on plugin restart

---

## [1.0.5] — 2026-05-22

### Fixed
- Various release fixes and stability improvements

---

## [1.0.3] — 2026-05-22

### Fixed
- Info.plist corrections

---

## [1.0.2] — 2026-05-21

### Added
- Initial production test releases

---

## [1.0.1] — 2026-05-21

### Added
- First development version for production testing

---

## [1.0.0] — 2026-05-20

### Added
- Initial release
- Ecowitt local push protocol support via `aioecowitt`
- Single *Ecowitt Gateway Hub* device per gateway holds all sensor states
- Dynamic state system — states appear automatically as sensor data arrives; no XML editing required
- Unit preference system (Imperial / Metric) with per-push priority resolution
- PASSKEY-based routing for multiple simultaneous gateways
- Stale detection — `connectionStatus` set to `Stale` after 5 minutes without a push
- Full sensor coverage: outdoor/indoor conditions, wind, rain (tipping-bucket and WS90 piezo), pressure, solar/UV, VPD, CO₂/air quality (WH45/WH46), lightning (WH57), leak sensors (WH55), PM2.5 channels (WH41/WH43), multi-channel temp/humidity (WH31), soil moisture (WH51), soil temperature (WN34), leaf wetness, LDS liquid sensors, batteries
- Asyncio HTTP server with batched `updateStatesOnServer` calls per push
- Debug logging option for raw push data and sensor discovery
