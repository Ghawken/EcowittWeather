![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Code Architecture

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

This page describes how the plugin works internally. It is aimed at contributors and developers who want to understand, extend, or debug the plugin.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Ecowitt Gateway (GW3000, GW2000, etc.)                     │
│  HTTP POST every 16–60 seconds (Ecowitt protocol)           │
└────────────────────────┬────────────────────────────────────┘
                         │ LAN (port 45000)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Indigo Mac                                                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  EcowittLoop (daemon thread)                         │   │
│  │                                                      │   │
│  │  asyncio event loop                                  │   │
│  │  ├── aiohttp web server                              │   │
│  │  ├── EcoWittListener (aioecowitt)                    │   │
│  │  │   ├── process_data() [patched]                    │   │
│  │  │   ├── new_sensor_cb → _on_new_sensor()            │   │
│  │  │   └── sensor.update_cb → _on_sensor_update()      │   │
│  │  ├── _on_push_received()  (call_soon)                │   │
│  │  └── _flush_pending()     (call_soon, once/tick/dev) │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │ updateStatesOnServer (thread-safe)     │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  Indigo main thread                                  │   │
│  │  ├── Plugin lifecycle (startup/shutdown/deviceStart) │   │
│  │  ├── runConcurrentThread (stale detection)           │   │
│  │  └── Indigo device states                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Threading Model

Indigo plugins run on Indigo's main thread. This plugin adds a second thread — the `EcowittLoop` daemon thread — that owns an asyncio event loop.

| Thread | Owns | Role |
|---|---|---|
| Indigo main thread | Plugin lifecycle, device callbacks, `runConcurrentThread` | Indigo SDK calls |
| `EcowittLoop` (daemon) | asyncio event loop, aiohttp server, aioecowitt | Receives and processes gateway pushes |

**Cross-thread safety:** All Indigo API calls (`dev.updateStatesOnServer`, `dev.stateListOrDisplayStateIdChanged`, `indigo.devices[...]`) are made from the asyncio thread via calls that are safe to call from any thread. The asyncio event loop is started with `run_forever()` and never exits until `event_loop.stop()` is called from the main thread during shutdown.

Communication from the main thread to the asyncio thread uses `asyncio.run_coroutine_threadsafe()`. Communication in the other direction (asyncio → Indigo state writes) is safe because `updateStatesOnServer` is thread-safe in Indigo's API.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## aioecowitt Integration

The plugin uses [`aioecowitt`](https://github.com/home-assistant-libs/aioecowitt) (the same library used by Home Assistant) to parse Ecowitt protocol POSTs.

**Key class:** `EcoWittListener` (previously called `EcoWittServer` — renamed in a library update).

```python
self.ecowitt_server = EcoWittListener(port=port, path=listen_path)
self.ecowitt_server.new_sensor_cb.append(self._on_new_sensor)
await self.ecowitt_server.start()
```

`EcoWittListener` starts an aiohttp web server, accepts POST requests, and parses the Ecowitt field set into typed `EcoWittSensor` objects. Each sensor has a `key` (e.g. `"tempf"`), `value`, `name`, and `station` (the gateway it came from, identified by PASSKEY).

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## process_data Patch

`aioecowitt`'s `update_value()` method skips calling `update_cb` when a sensor value hasn't changed between pushes. This is a problem for `connectionStatus` and `lastUpdate` — they must update on every push regardless.

To solve this, the plugin wraps `process_data` with a patched version:

```python
_orig_process_data = self.ecowitt_server.process_data

def _patched_process_data(data: dict) -> None:
    # add safe defaults for fields extract_station() requires
    safe = {"PASSKEY": ..., "stationtype": ..., "model": ...}
    safe.update(data)
    _orig_process_data(safe)
    # fire our own per-push callback regardless of value changes
    self.event_loop.call_soon(self._on_push_received, data)

self.ecowitt_server.process_data = _patched_process_data
```

The `call_soon()` queues `_on_push_received` to run on the next asyncio event loop tick, which is after all `update_cb` sensor callbacks have fired for this push.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Batched State Updates

Ecowitt pushes can contain 40–60 sensor readings simultaneously. Writing each one to Indigo as a separate `updateStateOnServer` call would be slow and would cause the Indigo device inspector to flicker. Instead, all updates from a single push are coalesced into one `updateStatesOnServer` call per device.

**Mechanism:**

1. `_on_sensor_update(sensor)` is called once per changed sensor value (from `update_cb`)
2. It accumulates values into `self._pending[dev_id][state_key] = value`
3. It schedules `_flush_pending(dev_id)` via `call_soon()` — but only the **first** update per device per event-loop tick schedules the flush (tracked by `_flush_scheduled`)
4. After all sensor callbacks for this push have run, `_flush_pending` fires and writes all accumulated values in a single `updateStatesOnServer` call

```
Push arrives
  → update_cb fires for sensor A → pending["outdoorTemp"] = 72.4  → schedule flush
  → update_cb fires for sensor B → pending["windSpeed"] = 8.3     → flush already scheduled
  → update_cb fires for sensor C → pending["humidity"] = 61.2     → flush already scheduled
  → event loop tick ends
  → _flush_pending fires → updateStatesOnServer([outdoorTemp, windSpeed, humidity])
```

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Unit Priority System

`aioecowitt`'s `calc.py` module computes both imperial and metric variants for most measurements automatically. This means the plugin receives both `tempf` (°F) and `tempc` (°C) from every push, and both map to the same Indigo state key (`outdoorTemp`).

The priority system selects the winner:

```python
IMPERIAL_VARIANT_KEYS = frozenset(["tempf", "windspeedmph", "rainratein", ...])
METRIC_VARIANT_KEYS   = frozenset(["tempc", "windspeedkmh", "rainratemm", ...])

units = self.pluginPrefs.get("units", "imperial")
if units == "metric":
    priority = 1 if sensor.key in IMPERIAL_VARIANT_KEYS else 0
else:
    priority = 1 if sensor.key in METRIC_VARIANT_KEYS else 0
```

Lower priority number wins. When accumulating into `_pending`, a new value only overwrites the existing one if its priority is lower than or equal to the priority already recorded for that state slot (`_pending_priority`).

Unit-neutral keys (e.g. `humidity`, `uv`, `winddir`) have priority 0 for both unit systems and always win their slot unconditionally.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Dynamic State System

States are not declared statically in `Devices.xml`. Only `connectionStatus` is declared there. All other states are registered dynamically as data arrives, using a pattern inspired by [GhostXML](https://github.com/IndigoDomotics/GhostXML).

**Data structures:**

```python
self._device_seen_states: dict[int, dict[str, str]]
# {dev_id: {state_key: value_type}}
# e.g. {1234567: {"outdoorTemp": "float", "windSpeed": "float", ...}}
```

**Registration flow:**

```
New state key arrives in _flush_pending:
  1. state_key not in _device_seen_states[dev_id]
  2. Add to _device_seen_states: {state_key: vtype}
  3. Call dev.stateListOrDisplayStateIdChanged()
     → Indigo calls getDeviceStateList()
     → getDeviceStateList() reads _device_seen_states and builds the full list
     → Indigo registers the new state
  4. updateStatesOnServer() writes the value into the now-registered state
```

**Survival across restarts:**

When `deviceStartComm` is called, the plugin seeds `_device_seen_states` from `dev.states` (the states Indigo persisted from the previous session). This means all previously received states are available immediately on plugin restart without waiting for a new push.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Sensor-to-State Mapping

The `SENSOR_TO_STATE` dict maps every `aioecowitt` sensor key to an `(indigo_state_key, value_type)` pair:

```python
SENSOR_TO_STATE: dict[str, tuple[str, str]] = {
    "tempf":    ("outdoorTemp", "float"),
    "tempc":    ("outdoorTemp", "float"),
    "humidity": ("outdoorHumidity", "float"),
    # ... 200+ entries
}
```

Multi-channel sensors (WH31, WH51, WN34) are generated programmatically at module load time rather than written out 8 or 16 times:

```python
for _i in range(1, 9):
    _S[f"temp{_i}f"] = (f"ch{_i}Temp", "float")
    _S[f"temp{_i}c"] = (f"ch{_i}Temp", "float")
    ...
```

The parallel `STATE_META` dict maps each Indigo state key to its `(value_type, display_label)` for use in `getDeviceStateList`:

```python
STATE_META: dict[str, tuple[str, str]] = {
    "outdoorTemp": ("float", "Outdoor Temperature"),
    ...
}
```

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## PASSKEY Routing

Each incoming push contains a `PASSKEY` field. The plugin maintains two lookup structures:

```python
self._passkey_to_devid: dict[str, int]   # passkey → device id
self._open_devid: int | None              # first device with blank passkey
```

`_find_device_by_passkey(passkey)` implements the routing logic:

1. Exact PASSKEY match → return that device
2. No match → fall back to `_open_devid` (blank-passkey device)
3. No open device → iterate `indigo.devices.iter("self")` as last resort
4. Nothing found → return `None` (push is discarded with a warning)

The maps are rebuilt by `_rebuild_device_map()` on startup and whenever a device is updated.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Stale Detection

`runConcurrentThread` (Indigo's background thread mechanism) wakes every 60 seconds and calls `_check_stale_devices()`:

```python
def _check_stale_devices(self) -> None:
    for dev in indigo.devices.iter("self"):
        last_str = dev.states.get("lastUpdate", "")
        ts = datetime.fromisoformat(last_str)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > 300 and dev.states.get("connectionStatus") != "Stale":
            dev.updateStateOnServer("connectionStatus", value="Stale")
```

If `lastUpdate` is more than 300 seconds (5 minutes) old and the device isn't already marked Stale, `connectionStatus` is set to `Stale`. The device returns to `Connected` on the next push.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Unmonitored Endpoint Logging

The `aiohttp` handler is also wrapped so requests arriving at the wrong path or with an unexpected HTTP method produce informative Indigo log entries rather than silently returning a 404:

```python
async def _logging_handler(request):
    response = await _orig_handler(request)
    if response.status == 404:
        self.logger.error(
            f"Unmonitored endpoint: {request.method} {request.path!r} "
            f"from {request.remote} — plugin expects POST to {listen_path!r}"
        )
    elif response.status == 405:
        self.logger.warning(...)
    return response
```

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## System / Diagnostic Field Filtering

Several fields sent by the gateway carry no weather data:

```python
SYSTEM_SENSOR_KEYS = frozenset(["runtime", "heap", "dateutc", "interval", "freq", "ws90_ver"])
```

These are checked at the top of `_on_sensor_update` and silently skipped — no Indigo state is created and no warning is logged.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## File Structure

```
EcowittWeather.indigoPlugin/
└── Contents/
    ├── Info.plist                  Plugin metadata, bundle ID, version
    ├── requirements.txt            aioecowitt>=2025.9.2, aiohttp>=3.9.0
    └── Server Plugin/
        ├── plugin.py               All plugin code (~1000 lines)
        ├── Devices.xml             Declares ecowittGateway device type + connectionStatus
        ├── PluginConfig.xml        listenPort, listenPath, units, debugLogging
        └── Actions.xml             (empty — no custom actions defined)
```

### plugin.py structure

| Lines | Content |
|---|---|
| 1–55 | Module docstring, imports, `IndigoLogHandler` |
| 57–280 | `IMPERIAL_VARIANT_KEYS`, `METRIC_VARIANT_KEYS`, `SYSTEM_SENSOR_KEYS`, `SENSOR_TO_STATE` |
| 282–440 | `STATE_DEFINITIONS` list and `STATE_META` dict |
| 447–496 | `Plugin.__init__` — instance variable setup |
| 498–556 | `startup()`, `shutdown()` |
| 558–643 | `_start_server()` — asyncio server, process_data patch, handler patch |
| 645–695 | `_on_push_received()` — per-push metadata update |
| 697–806 | `_on_new_sensor()`, `_on_sensor_update()`, `_flush_pending()` |
| 808–842 | Device lookup — `_rebuild_device_map`, `_register_device`, `_find_device_by_passkey` |
| 844–874 | Stale detection — `runConcurrentThread`, `_check_stale_devices` |
| 876–955 | Device lifecycle — `deviceStartComm`, `deviceStopComm`, `deviceUpdated`, `getDeviceStateList` |
| 957–1021 | Preferences — `validatePrefsConfigUi`, `closedPrefsConfigUi` |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `aioecowitt` | ≥ 2025.9.2 | Ecowitt protocol parsing, sensor objects |
| `aiohttp` | ≥ 3.9.0 | Async HTTP server (used by aioecowitt internally) |
| `indigo` | system | Indigo plugin SDK (provided by Indigo) |

Both `aioecowitt` and `aiohttp` are listed in `requirements.txt` and installed automatically by Indigo.
