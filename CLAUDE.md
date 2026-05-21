# CLAUDE.md — Indigo Async Plugin + Dynamic States Reference

This document is a design reference for building Indigo home-automation plugins that:
- Drive an **asyncio event loop in a daemon thread** alongside Indigo's own thread model
- Expose a **variable number of device states** that are created dynamically as data arrives, not pre-declared in Devices.xml
- Handle **dual-unit data sources** (imperial/metric) where the same logical value arrives in two forms

The canonical implementation is `EcowittWeather.indigoPlugin`. Use it as the code outline for any similar plugin — weather APIs, local push receivers, MQTT bridges, polling loops, etc.

---

## 1. File Structure

```
MyPlugin.indigoPlugin/Contents/
├── Info.plist               # Indigo-specific keys (NOT standard Apple bundle keys)
├── requirements.txt         # pip dependencies; Indigo installs these automatically
└── Server Plugin/
    ├── plugin.py            # All logic lives here
    ├── Devices.xml          # Declare device type + ONLY static/guaranteed states
    ├── PluginConfig.xml     # Plugin-level preferences (port, path, units, debug)
    └── Actions.xml          # Leave empty if no actions needed
```

### Info.plist keys (Indigo-specific — not standard Apple bundle)
```xml
<key>PluginVersion</key>      <string>1.0.0</string>
<key>ServerApiVersion</key>   <string>3.4</string>
<key>IwsApiVersion</key>      <string>1.0.0</string>
<key>CFBundleDisplayName</key> ...
<key>CFBundleName</key>        ...
<key>CFBundleIdentifier</key>  <string>com.community.indigoplugin.yourplugin</string>
<key>CFBundleVersion</key>    <string>1.0.0</string>
```
Do **not** use `ServerVersion`, `IOMVersion`, `APIVersion`, `CFBundleShortVersionString` — those are wrong keys from Apple bundle docs.

### Devices.xml — declare the minimum
Only declare states that are **guaranteed on every device** (e.g. `connectionStatus`). All data-driven states are registered dynamically in code. Set `UiDisplayStateId` to the status key so it shows in the device list.

```xml
<Device type="custom" id="myHubDevice">
  <States>
    <State id="connectionStatus">
      <ValueType>String</ValueType>
      ...
    </State>
  </States>
  <UiDisplayStateId>connectionStatus</UiDisplayStateId>
</Device>
```

---

## 2. Logging Pattern

`indigo.PluginBase.__init__` attaches its own log handler. You **must** clear it before adding yours or every message appears twice.

```python
class IndigoLogHandler(logging.Handler):
    def __init__(self, display_name: str, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.displayName = display_name

    def emit(self, record: logging.LogRecord) -> None:
        levelno = int(record.levelno)
        if self.level > levelno:
            return
        if levelno == logging.DEBUG:
            msg = f"({path.basename(record.pathname)}:{record.funcName}:{record.lineno}): {record.getMessage()}"
        else:
            msg = record.getMessage()
        indigo.server.log(message=msg, type=self.displayName,
                          isError=(levelno >= logging.ERROR), level=levelno)


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        # Clear PluginBase's handler to prevent double logging
        self.logger.setLevel(logging.DEBUG)
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)
        self.logger.propagate = False

        self.indigo_log_handler = IndigoLogHandler(pluginDisplayName, logging.INFO)
        self.logger.addHandler(self.indigo_log_handler)

        self.debug = bool(pluginPrefs.get("debugLogging", False))
        if self.debug:
            self.indigo_log_handler.setLevel(logging.DEBUG)
```

---

## 3. Asyncio Daemon Thread

Indigo is not async-aware. Run a separate event loop in a daemon thread. Never block Indigo's thread with `asyncio.run()`.

```python
def startup(self) -> None:
    self.event_loop = asyncio.new_event_loop()
    self.event_loop.set_exception_handler(self._on_asyncio_exception)
    self.loop_thread = threading.Thread(
        target=self.event_loop.run_forever, daemon=True, name="MyPluginLoop"
    )
    self.loop_thread.start()

    fut = asyncio.run_coroutine_threadsafe(
        self._start_server(), self.event_loop
    )
    fut.result(timeout=30)   # blocks Indigo thread only during startup

def shutdown(self) -> None:
    if self.event_loop and self.event_loop.is_running():
        self.event_loop.call_soon_threadsafe(self.event_loop.stop)
    if self.loop_thread:
        self.loop_thread.join(timeout=5)

def _on_asyncio_exception(self, loop, context):
    exc = context.get("exception")
    if exc:
        self.logger.error(f"Asyncio unhandled: {type(exc).__name__}: {exc}")
    else:
        self.logger.error(f"Asyncio error: {context.get('message', context)}")
```

### Crossing the thread boundary

| Direction | Method |
|---|---|
| Indigo thread → asyncio | `asyncio.run_coroutine_threadsafe(coro, loop)` — returns a `concurrent.futures.Future` |
| asyncio thread → Indigo | `indigo.devices[id].updateStatesOnServer(...)` — Indigo's API is thread-safe |
| asyncio → asyncio (next tick) | `loop.call_soon(fn, *args)` |
| Indigo → asyncio (fire-and-forget) | `loop.call_soon_threadsafe(fn, *args)` |

**Never** call `await` from Indigo's thread. **Never** call `fut.result()` from the asyncio thread (deadlock).

---

## 4. HTTP Push Server (aioecowitt pattern)

For libraries that expose a callback-based HTTP server (like `aioecowitt.EcoWittListener`):

```python
async def _start_server(self, port: int, path: str) -> None:
    # Normalise path — strip trailing slash so /foo/ and /foo both work
    path = path.rstrip("/") or "/"

    self.server = EcoWittListener(port=port, path=path)
    self.server.new_sensor_cb.append(self._on_new_sensor)

    # Wrap process_data for per-push callback + error visibility
    _orig = self.server.process_data
    def _patched(data: dict) -> None:
        raw = dict(data)
        self.logger.debug(f"Push: {len(raw)} fields")
        # inject defaults for required-but-possibly-missing fields
        safe = {"PASSKEY": raw.get("PASSKEY", "UNKNOWN"), ...}
        safe.update(raw)
        try:
            _orig(safe)
        except Exception as exc:
            self.logger.error(f"process_data failed: {exc}")
            return
        self.event_loop.call_soon(self._on_push_received, raw)
    self.server.process_data = _patched

    # Wrap low-level aiohttp handler to log requests to wrong path/method.
    # EcoWittListener uses web.Server(self.handler) — setting an instance
    # attribute shadows the class method before start() is called.
    _orig_handler = self.server.handler
    async def _logging_handler(request):
        response = await _orig_handler(request)
        if response.status == 404:
            self.logger.error(
                f"Unmonitored endpoint: {request.method} {request.path!r} "
                f"from {request.remote} — plugin expects POST to {path!r}"
            )
        elif response.status == 405:
            self.logger.warning(
                f"Unexpected method {request.method!r} at {request.path!r}"
            )
        return response
    self.server.handler = _logging_handler

    await self.server.start()
```

For **polling** sources (REST APIs etc.) instead of push:

```python
async def _poll_loop(self) -> None:
    while True:
        try:
            data = await self._fetch()
            self._process(data)
        except Exception:
            self.logger.exception("Poll failed")
        await asyncio.sleep(self.interval)
```

---

## 5. Dynamic State Registration (GhostXML Pattern)

This is the core pattern. States are **not** pre-declared in Devices.xml. They are registered on-demand as data arrives.

### Data structures (in `__init__`)
```python
# Per-device accumulation: {dev_id: {state_key: value_type}}
# Grows as data arrives; seeded from dev.states on plugin restart.
self._device_seen_states: dict[int, dict[str, str]] = {}
```

### State metadata lookup
Build a dict from your sensor→state mapping so `getDeviceStateList` can look up types and labels by state key:
```python
# {state_key: (value_type, display_label)}
STATE_META: dict[str, tuple[str, str]] = {
    "outdoorTemp":  ("float",  "Outdoor Temperature"),
    "windSpeed":    ("float",  "Wind Speed"),
    "lastUpdate":   ("string", "Last Update"),
    ...
}
```
Value types: `"float"` → `getDeviceStateDictForNumberType`, `"string"` → `getDeviceStateDictForStringType`.

### `getDeviceStateList` — returns only seen states
```python
def getDeviceStateList(self, dev: indigo.Device) -> list:
    state_list = super().getDeviceStateList(dev)          # includes Devices.xml states
    existing_keys = {s.get("Key", "") for s in state_list}

    seen = self._device_seen_states.get(dev.id, {})       # {state_key: vtype}
    for key, vtype in seen.items():
        if key in existing_keys:
            continue
        label = STATE_META.get(key, (vtype, key))[1]
        try:
            if vtype == "string":
                entry = self.getDeviceStateDictForStringType(key, label, label)
            else:
                entry = self.getDeviceStateDictForNumberType(key, label, label)
        except Exception as exc:
            self.logger.error(f"getDeviceStateList: failed for {key!r}: {exc}")
            continue
        state_list.append(entry)
        existing_keys.add(key)
    return state_list
```

### `deviceStartComm` — seed from persisted states on restart
```python
def deviceStartComm(self, dev: indigo.Device) -> None:
    seen = self._device_seen_states.setdefault(dev.id, {})
    if not seen:
        # Restore states from previous sessions so they survive plugin restarts.
        # Brand-new devices have only 'connectionStatus' here → nothing seeded →
        # states appear dynamically as first data arrives (correct behaviour).
        for key in dev.states:
            if key == "connectionStatus":
                continue
            meta = STATE_META.get(key)
            seen[key] = meta[0] if meta else "string"

    dev.stateListOrDisplayStateIdChanged()   # triggers getDeviceStateList()
    dev.updateStateOnServer("connectionStatus", "Never")
```

### `deviceStopComm` — clean up
```python
def deviceStopComm(self, dev: indigo.Device) -> None:
    self._device_seen_states.pop(dev.id, None)
```

### Writing states — register new keys first

The critical sequence whenever you have data to write:

```python
def _flush_pending(self, dev_id: int) -> None:
    updates = self._pending.pop(dev_id, {})    # {state_key: value}
    if not updates:
        return

    dev = indigo.devices[dev_id]

    # 1. Register any state keys seen for the first time this session
    seen = self._device_seen_states.setdefault(dev_id, {})
    new_keys = [k for k in updates if k not in seen]
    if new_keys:
        for k in new_keys:
            seen[k] = STATE_META.get(k, ("string", k))[0]
        dev.stateListOrDisplayStateIdChanged()   # calls getDeviceStateList()

    # 2. Write values — Indigo now knows about all the keys
    dev.updateStatesOnServer([{"key": k, "value": v} for k, v in updates.items()])
```

**Rule:** `stateListOrDisplayStateIdChanged()` → `updateStatesOnServer()`. Never the other way around. `updateStatesOnServer` silently drops keys that aren't registered.

### Batching with `call_soon`
When many sensor callbacks fire in one event-loop tick, coalesce them into one write:

```python
def _on_sensor_update(self, sensor) -> None:
    self._pending.setdefault(dev.id, {})[state_key] = value
    if dev.id not in self._flush_scheduled:
        self._flush_scheduled.add(dev.id)
        self.event_loop.call_soon(self._flush_pending, dev.id)  # runs next tick

def _flush_pending(self, dev_id: int) -> None:
    self._flush_scheduled.discard(dev_id)
    # ... (see above)
```

---

## 6. Dual-Unit Priority System

When a library computes both `tempf` (°F) and `tempc` (°C) for the same state slot, only one should win based on the user's unit preference.

```python
IMPERIAL_VARIANT_KEYS: frozenset[str] = frozenset(["tempf", "windspeedmph", ...])
METRIC_VARIANT_KEYS:   frozenset[str] = frozenset(["tempc", "windspeedkmh", ...])

# Per-device, per-state: winning priority number (lower = higher priority)
self._pending_priority: dict[int, dict[str, int]] = {}

def _on_sensor_update(self, sensor) -> None:
    state_key, _ = SENSOR_TO_STATE[sensor.key]
    units = self.pluginPrefs.get("units", "imperial")
    if units == "metric":
        priority = 1 if sensor.key in IMPERIAL_VARIANT_KEYS else 0
    else:
        priority = 1 if sensor.key in METRIC_VARIANT_KEYS else 0

    dev_priority = self._pending_priority.setdefault(dev.id, {})
    if priority > dev_priority.get(state_key, 999):
        return   # better value already queued for this slot
    dev_priority[state_key] = priority
    self._pending.setdefault(dev.id, {})[state_key] = sensor.value
```

**Note:** aioecowitt computes both unit variants in the same synchronous `process_data` call, so both arrive before `_flush_pending` runs. The priority check correctly lets the preferred unit win.

---

## 7. System / Diagnostic Fields

Libraries often expose metadata fields (timestamps, firmware versions, heap size) alongside real data. Silently ignore them:

```python
SYSTEM_SENSOR_KEYS: frozenset[str] = frozenset([
    "runtime", "heap", "dateutc", "interval", "freq", "ws90_ver",
])

def _on_new_sensor(self, sensor) -> None:
    if sensor.key not in SYSTEM_SENSOR_KEYS:
        self.logger.info(f"New sensor: {sensor.key!r} ({sensor.name})")
    sensor.update_cb.append(lambda: self._on_sensor_update(sensor))

def _on_sensor_update(self, sensor) -> None:
    try:
        if sensor.key in SYSTEM_SENSOR_KEYS:
            return    # check BEFORE any logging
        ...
```

---

## 8. Stale Detection

For push-based sources: if no data arrives for N minutes, mark the device stale.

```python
def runConcurrentThread(self) -> None:
    try:
        while True:
            self.sleep(60)
            self._check_stale_devices()
    except self.StopThread:
        pass

def _check_stale_devices(self) -> None:
    for dev in indigo.devices.iter("self"):
        if not dev.enabled:
            continue
        last_str = dev.states.get("lastUpdate", "")
        if not last_str or last_str == "Never":
            continue
        try:
            ts = datetime.fromisoformat(last_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > 300 and dev.states.get("connectionStatus") != "Stale":
                dev.updateStateOnServer("connectionStatus", "Stale")
                self.logger.warning(f"[{dev.name}] Stale — no data for {int(age//60)}m")
        except Exception:
            pass
```

---

## 9. Adapting to Other Weather Sources

| Source type | asyncio entry point | Key difference vs Ecowitt |
|---|---|---|
| Local HTTP push (aioecowitt) | `EcoWittListener` in `_start_server` | Wrap `process_data`; handler logging via instance attr shadow |
| REST API polling | `asyncio.sleep` loop in `_start_server` | No callbacks; pull data, then call `_process(data)` |
| MQTT (asyncio-mqtt, aiomqtt) | `client.messages` async iterator | Sensor callbacks replaced by topic subscriptions |
| WebSocket stream | `websockets.connect` | Similar to MQTT; messages drive `_on_sensor_update` |
| aiohttp client | `aiohttp.ClientSession.get` in poll loop | Handle auth headers, rate limiting, pagination |

In all cases the **thread model, logging, dynamic state, and stale detection** patterns are identical. Only `_start_server` and the data → state_key mapping change.

### Sensor→State mapping pattern
```python
# Source field name → (indigo_state_key, value_type)
SENSOR_TO_STATE: dict[str, tuple[str, str]] = {
    "temperature":    ("outdoorTemp",   "float"),
    "humidity":       ("outdoorHumidity", "float"),
    "feels_like":     ("feelsLike",     "float"),
    ...
}

# State key → (value_type, display_label)  — derived from above + extras
STATE_META: dict[str, tuple[str, str]] = { ... }
```

Keep `SENSOR_TO_STATE` and `STATE_META` as module-level constants. They're the only part that changes substantially between weather sources.

---

## 10. Key Gotchas

| Gotcha | Fix |
|---|---|
| Double logging on startup | Clear `self.logger.handlers` and set `propagate = False` before adding `IndigoLogHandler` |
| `updateStatesOnServer` silently drops keys | Always call `stateListOrDisplayStateIdChanged()` first when new keys appear |
| States lost on plugin restart | Seed `_device_seen_states` from `dev.states` in `deviceStartComm` |
| asyncio exception swallowed silently | Set `loop.set_exception_handler(self._on_asyncio_exception)` |
| Wrong path (trailing slash) | Normalise: `path = path.rstrip("/") or "/"` before passing to server |
| HTTP 404s invisible | Wrap the server's handler and log non-200 responses |
| `fut.result()` deadlock | Never call from asyncio thread; only call from Indigo's thread during startup |
| Metric value overwrites imperial | Priority system: track `_pending_priority`; lower number wins the state slot |
| `getDeviceStateList` key dict uses `"Key"` (capital K) | `s.get("Key", "")` when iterating the base state list |
| `tf_ch{i}` vs `tf_ch{i}f` | aioecowitt uses no `f` suffix for Fahrenheit on soil/CO2 temp keys |
