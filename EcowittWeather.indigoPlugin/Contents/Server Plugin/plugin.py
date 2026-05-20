"""Ecowitt Weather Station — Indigo Home Automation Plugin.

Receives weather data from Ecowitt gateways via local HTTP push using the
aioecowitt library.  All sensor readings are exposed as Indigo device states
on a single "Ecowitt Gateway Hub" device per physical gateway.

Architecture: asyncio event loop in a daemon thread alongside Indigo's own
threads.  Sensor callbacks fire in the asyncio thread; state writes use
Indigo's thread-safe updateStatesOnServer API.  Pending updates for a single
push are coalesced via call_soon() into one batched updateStatesOnServer call.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from os import path
from typing import Any

import indigo  # type: ignore[import]
from aioecowitt import EcoWittListener, EcoWittSensor  # type: ignore[import]


# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

class IndigoLogHandler(logging.Handler):
    """Routes Python log records to indigo.server.log."""

    def __init__(self, display_name: str, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.displayName = display_name

    def emit(self, record: logging.LogRecord) -> None:
        levelno = int(record.levelno)
        if self.level > levelno:
            return
        if levelno == logging.DEBUG:
            msg = (
                f"({path.basename(record.pathname)}"
                f":{record.funcName}:{record.lineno}): "
                f"{record.getMessage()}"
            )
        else:
            msg = record.getMessage()
        is_error = levelno >= logging.ERROR
        indigo.server.log(
            message=msg,
            type=self.displayName,
            isError=is_error,
            level=levelno,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Sensor → Indigo state mapping
# ──────────────────────────────────────────────────────────────────────────────

# Keys carrying imperial values (°F, mph, inHg, in, mi).
# When the user prefers metric these are treated as lower-priority duplicates.
IMPERIAL_VARIANT_KEYS: frozenset[str] = frozenset(
    [
        "tempf", "tempinf", "dewpointf", "dewpointinf",
        "windchillf", "tempfeelsf", "tf_co2f",
        "windspeedmph", "windspdmph_avg10m", "windgustmph", "maxdailygust",
        "rainratein", "eventrainin", "hourlyrainin", "dailyrainin",
        "weeklyrainin", "monthlyrainin", "yearlyrainin", "totalrainin",
        "last24hrainin",
        # WS90 piezoelectric rain gauge — imperial (inches)
        "rrain_piezo", "erain_piezo", "hrain_piezo", "drain_piezo",
        "wrain_piezo", "mrain_piezo", "yrain_piezo", "last24hrain_piezo",
        "baromrelin", "baromabsin",
        "lightning_mi",
    ]
    + [f"temp{i}f"      for i in range(1, 9)]
    + [f"tf_ch{i}f"     for i in range(1, 9)]
    + [f"dewpoint{i}f"  for i in range(1, 9)]
)

# Keys carrying metric values (°C, km/h, hPa, mm, km).
# When the user prefers imperial these are treated as lower-priority duplicates.
METRIC_VARIANT_KEYS: frozenset[str] = frozenset(
    [
        "tempc", "tempinc", "dewpointc", "dewpointinc",
        "windchillc", "tempfeelsc", "tf_co2c",
        "windspeedkmh", "windspdkmh_avg10m", "windgustkmh", "maxdailygustkmh",
        "rainratemm", "eventrainmm", "hourlyrainmm", "dailyrainmm",
        "weeklyrainmm", "monthlyrainmm", "yearlyrainmm", "totalrainmm",
        "last24hrainmm",
        # WS90 piezoelectric rain gauge — metric (mm)
        "rrain_piezomm", "erain_piezomm", "hrain_piezomm", "drain_piezomm",
        "wrain_piezomm", "mrain_piezomm", "yrain_piezomm", "last24hrain_piezomm",
        "baromrelhpa", "baromabshpa",
        "lightning",
    ]
    + [f"temp{i}c"      for i in range(1, 9)]
    + [f"tf_ch{i}c"     for i in range(1, 9)]
    + [f"dewpoint{i}c"  for i in range(1, 9)]
)

# Sensor keys that are system/diagnostic fields — received from the gateway but
# carry no weather data.  Silently ignored (no Indigo state, no warning logged).
SYSTEM_SENSOR_KEYS: frozenset[str] = frozenset([
    "runtime", "heap", "dateutc", "interval", "freq", "ws90_ver",
])

# aioecowitt sensor key → (indigo state key, value type)
# value type: "float" | "string" | "int"
_S: dict[str, tuple[str, str]] = {
    # ── Outdoor temperature / humidity ───────────────────────────────────────
    "tempf":                ("outdoorTemp",          "float"),
    "tempc":                ("outdoorTemp",          "float"),
    "humidity":             ("outdoorHumidity",      "float"),
    # ── Indoor temperature / humidity ─────────────────────────────────────────
    "tempinf":              ("indoorTemp",           "float"),
    "tempinc":              ("indoorTemp",           "float"),
    "humidityin":           ("indoorHumidity",       "float"),
    # ── Derived temperatures ──────────────────────────────────────────────────
    "dewpointf":            ("dewPoint",             "float"),
    "dewpointc":            ("dewPoint",             "float"),
    "dewpointinf":          ("indoorDewPoint",       "float"),
    "dewpointinc":          ("indoorDewPoint",       "float"),
    "windchillf":           ("windChill",            "float"),
    "windchillc":           ("windChill",            "float"),
    "tempfeelsf":           ("feelsLike",            "float"),
    "tempfeelsc":           ("feelsLike",            "float"),
    # ── Wind ─────────────────────────────────────────────────────────────────
    "winddir":              ("windDirection",        "float"),
    "winddir_avg10m":       ("windDirAvg10m",        "float"),
    "windspeedmph":         ("windSpeed",            "float"),
    "windspeedkmh":         ("windSpeed",            "float"),
    "windspdmph_avg10m":    ("windSpeedAvg10m",      "float"),
    "windspdkmh_avg10m":    ("windSpeedAvg10m",      "float"),
    "windgustmph":          ("windGust",             "float"),
    "windgustkmh":          ("windGust",             "float"),
    "maxdailygust":         ("maxDailyGust",         "float"),
    "maxdailygustkmh":      ("maxDailyGust",         "float"),
    # ── Rain (traditional tipping-bucket gauge) ──────────────────────────────
    "rainratein":           ("rainRate",             "float"),
    "rainratemm":           ("rainRate",             "float"),
    "eventrainin":          ("eventRain",            "float"),
    "eventrainmm":          ("eventRain",            "float"),
    "hourlyrainin":         ("hourlyRain",           "float"),
    "hourlyrainmm":         ("hourlyRain",           "float"),
    "dailyrainin":          ("dailyRain",            "float"),
    "dailyrainmm":          ("dailyRain",            "float"),
    "weeklyrainin":         ("weeklyRain",           "float"),
    "weeklyrainmm":         ("weeklyRain",           "float"),
    "monthlyrainin":        ("monthlyRain",          "float"),
    "monthlyrainmm":        ("monthlyRain",          "float"),
    "yearlyrainin":         ("yearlyRain",           "float"),
    "yearlyrainmm":         ("yearlyRain",           "float"),
    # ── Rain (WS90 piezoelectric gauge) ──────────────────────────────────────
    "rrain_piezo":          ("rainRatePiezo",        "float"),
    "rrain_piezomm":        ("rainRatePiezo",        "float"),
    "erain_piezo":          ("eventRainPiezo",       "float"),
    "erain_piezomm":        ("eventRainPiezo",       "float"),
    "hrain_piezo":          ("hourlyRainPiezo",      "float"),
    "hrain_piezomm":        ("hourlyRainPiezo",      "float"),
    "drain_piezo":          ("dailyRainPiezo",       "float"),
    "drain_piezomm":        ("dailyRainPiezo",       "float"),
    "wrain_piezo":          ("weeklyRainPiezo",      "float"),
    "wrain_piezomm":        ("weeklyRainPiezo",      "float"),
    "mrain_piezo":          ("monthlyRainPiezo",     "float"),
    "mrain_piezomm":        ("monthlyRainPiezo",     "float"),
    "yrain_piezo":          ("yearlyRainPiezo",      "float"),
    "yrain_piezomm":        ("yearlyRainPiezo",      "float"),
    "last24hrain_piezo":    ("last24hRainPiezo",     "float"),
    "last24hrain_piezomm":  ("last24hRainPiezo",     "float"),
    "srain_piezo":          ("rainStatePiezo",       "int"),
    # ── Pressure ─────────────────────────────────────────────────────────────
    "baromrelin":           ("pressureRelative",     "float"),
    "baromrelhpa":          ("pressureRelative",     "float"),
    "baromabsin":           ("pressureAbsolute",     "float"),
    "baromabshpa":          ("pressureAbsolute",     "float"),
    # ── VPD ──────────────────────────────────────────────────────────────────
    "vpd":                  ("vpd",                  "float"),
    # ── Solar / UV ───────────────────────────────────────────────────────────
    "solarradiation":       ("solarRadiation",       "float"),
    "solarradiation_lux":   ("solarRadiationLux",    "float"),
    "uv":                   ("uvIndex",              "float"),
    # ── CO2 sensor (WH45 / WH46 / console) ───────────────────────────────────
    "co2":                  ("co2",                  "float"),
    "co2_24h":              ("co2Avg24h",            "float"),
    "co2in":                ("co2Indoor",            "float"),
    "co2in_24h":            ("co2IndoorAvg24h",      "float"),
    "humi_co2":             ("humiCo2",              "float"),
    "tf_co2f":              ("tempCo2",              "float"),
    "tf_co2c":              ("tempCo2",              "float"),
    "pm25_co2":             ("pm25Co2",              "float"),
    "pm25_24h_co2":         ("pm25Co2Avg24h",        "float"),
    "pm1_co2":              ("pm1Co2",               "float"),
    "pm1_24h_co2":          ("pm1Co2Avg24h",         "float"),
    "pm4_co2":              ("pm4Co2",               "float"),
    "pm4_24h_co2":          ("pm4Co2Avg24h",         "float"),
    "pm10_co2":             ("pm10Co2",              "float"),
    "pm10_24h_co2":         ("pm10Co2Avg24h",        "float"),
    # ── Lightning ────────────────────────────────────────────────────────────
    "lightning":            ("lightningDist",        "float"),
    "lightning_mi":         ("lightningDist",        "float"),
    "lightning_num":        ("lightningCount",       "float"),
    "lightning_time":       ("lightningLastTime",    "string"),
    # ── Leak sensors ─────────────────────────────────────────────────────────
    "leak_ch1":             ("leak1",                "int"),
    "leak_ch2":             ("leak2",                "int"),
    "leak_ch3":             ("leak3",                "int"),
    "leak_ch4":             ("leak4",                "int"),
    # ── Standalone battery / power sensors ───────────────────────────────────
    "wh65batt":             ("battWh65",             "float"),
    "wh40batt":             ("battWh40",             "float"),
    "wh80batt":             ("battWh80",             "float"),
    "wh57batt":             ("battWh57",             "float"),
    "wh68batt":             ("battWh68",             "float"),
    "wh90batt":             ("battWh90",             "float"),
    "wh25batt":             ("battWh25",             "float"),
    "wh26batt":             ("battWh26",             "float"),
    "pm25batt1":            ("pm25Batt1",            "float"),
    "pm25batt2":            ("pm25Batt2",            "float"),
    "pm25batt3":            ("pm25Batt3",            "float"),
    "pm25batt4":            ("pm25Batt4",            "float"),
    # WS90 supercapacitor voltage (charges from solar, drives the sensor)
    "ws90cap_volt":         ("ws90CapVolt",          "float"),
}

# Channel-based sensors: channels 1–8
for _i in range(1, 9):
    _S[f"temp{_i}f"]           = (f"ch{_i}Temp",       "float")
    _S[f"temp{_i}c"]           = (f"ch{_i}Temp",       "float")
    _S[f"humidity{_i}"]        = (f"ch{_i}Humidity",   "float")
    _S[f"dewpoint{_i}f"]       = (f"ch{_i}DewPoint",   "float")
    _S[f"dewpoint{_i}c"]       = (f"ch{_i}DewPoint",   "float")
    _S[f"soilmoisture{_i}"]    = (f"soilMoisture{_i}", "float")
    _S[f"tf_ch{_i}f"]          = (f"soilTemp{_i}",     "float")
    _S[f"tf_ch{_i}c"]          = (f"soilTemp{_i}",     "float")
    _S[f"leafwetness_ch{_i}"]  = (f"leafWetness{_i}",  "float")
    _S[f"batt{_i}"]            = (f"ch{_i}Battery",    "float")
    _S[f"soilbatt{_i}"]        = (f"soilBatt{_i}",     "float")

# PM2.5 channels 1–4
for _i in range(1, 5):
    _S[f"pm25_ch{_i}"]          = (f"pm25Ch{_i}",       "float")
    _S[f"pm25_avg_24h_ch{_i}"]  = (f"pm25Ch{_i}Avg24h", "float")

SENSOR_TO_STATE: dict[str, tuple[str, str]] = _S
del _S, _i  # type: ignore[name-defined]


# ──────────────────────────────────────────────────────────────────────────────
# Indigo state definitions  (state_key, value_type, display_label)
# ──────────────────────────────────────────────────────────────────────────────

_D: list[tuple[str, str, str]] = [
    # ── Gateway metadata ──────────────────────────────────────────────────────
    ("lastUpdate",          "string", "Last Update"),
    ("gatewayModel",        "string", "Gateway Model"),
    ("stationType",         "string", "Station Type"),
    # ── Outdoor ───────────────────────────────────────────────────────────────
    ("outdoorTemp",         "float",  "Outdoor Temperature"),
    ("outdoorHumidity",     "float",  "Outdoor Humidity"),
    ("dewPoint",            "float",  "Dew Point"),
    ("feelsLike",           "float",  "Feels Like"),
    ("windChill",           "float",  "Wind Chill"),
    # ── Indoor ────────────────────────────────────────────────────────────────
    ("indoorTemp",          "float",  "Indoor Temperature"),
    ("indoorHumidity",      "float",  "Indoor Humidity"),
    ("indoorDewPoint",      "float",  "Indoor Dew Point"),
    # ── Wind ──────────────────────────────────────────────────────────────────
    ("windDirection",       "float",  "Wind Direction"),
    ("windDirAvg10m",       "float",  "Wind Direction 10m Average"),
    ("windSpeed",           "float",  "Wind Speed"),
    ("windSpeedAvg10m",     "float",  "Wind Speed 10m Average"),
    ("windGust",            "float",  "Wind Gust"),
    ("maxDailyGust",        "float",  "Max Daily Gust"),
    # ── Rain ──────────────────────────────────────────────────────────────────
    ("rainRate",            "float",  "Rain Rate"),
    ("eventRain",           "float",  "Event Rain"),
    ("hourlyRain",          "float",  "Hourly Rain"),
    ("dailyRain",           "float",  "Daily Rain"),
    ("weeklyRain",          "float",  "Weekly Rain"),
    ("monthlyRain",         "float",  "Monthly Rain"),
    ("yearlyRain",          "float",  "Yearly Rain"),
    # ── Rain (WS90 piezoelectric gauge) ──────────────────────────────────────
    ("rainRatePiezo",       "float",  "Rain Rate (Piezo)"),
    ("eventRainPiezo",      "float",  "Event Rain (Piezo)"),
    ("hourlyRainPiezo",     "float",  "Hourly Rain (Piezo)"),
    ("dailyRainPiezo",      "float",  "Daily Rain (Piezo)"),
    ("weeklyRainPiezo",     "float",  "Weekly Rain (Piezo)"),
    ("monthlyRainPiezo",    "float",  "Monthly Rain (Piezo)"),
    ("yearlyRainPiezo",     "float",  "Yearly Rain (Piezo)"),
    ("last24hRainPiezo",    "float",  "Last 24h Rain (Piezo)"),
    ("rainStatePiezo",      "int",    "Rain State (Piezo)"),
    # ── Pressure / VPD ────────────────────────────────────────────────────────
    ("pressureRelative",    "float",  "Pressure Relative"),
    ("pressureAbsolute",    "float",  "Pressure Absolute"),
    ("vpd",                 "float",  "Vapour Pressure Deficit"),
    # ── Solar / UV ────────────────────────────────────────────────────────────
    ("solarRadiation",      "float",  "Solar Radiation (W/m²)"),
    ("solarRadiationLux",   "float",  "Solar Radiation (lux)"),
    ("uvIndex",             "float",  "UV Index"),
    # ── CO2 / air quality ─────────────────────────────────────────────────────
    ("co2",                 "float",  "CO2 (ppm)"),
    ("co2Avg24h",           "float",  "CO2 24h Average"),
    ("co2Indoor",           "float",  "Indoor CO2"),
    ("co2IndoorAvg24h",     "float",  "Indoor CO2 24h Average"),
    ("humiCo2",             "float",  "Humidity (WH45 CO2)"),
    ("tempCo2",             "float",  "Temperature (WH45 CO2)"),
    ("pm25Co2",             "float",  "PM2.5 (WH45)"),
    ("pm25Co2Avg24h",       "float",  "PM2.5 24h Average (WH45)"),
    ("pm1Co2",              "float",  "PM1 (WH46)"),
    ("pm1Co2Avg24h",        "float",  "PM1 24h Average (WH46)"),
    ("pm4Co2",              "float",  "PM4 (WH46)"),
    ("pm4Co2Avg24h",        "float",  "PM4 24h Average (WH46)"),
    ("pm10Co2",             "float",  "PM10 (WH45)"),
    ("pm10Co2Avg24h",       "float",  "PM10 24h Average (WH45)"),
    # ── Lightning ─────────────────────────────────────────────────────────────
    ("lightningDist",       "float",  "Lightning Distance"),
    ("lightningCount",      "float",  "Lightning Count"),
    ("lightningLastTime",   "string", "Lightning Last Time"),
    # ── Leak sensors ──────────────────────────────────────────────────────────
    ("leak1",               "int",    "Leak Detection 1"),
    ("leak2",               "int",    "Leak Detection 2"),
    ("leak3",               "int",    "Leak Detection 3"),
    ("leak4",               "int",    "Leak Detection 4"),
    # ── PM2.5 channels ────────────────────────────────────────────────────────
    ("pm25Ch1",             "float",  "PM2.5 Channel 1"),
    ("pm25Ch1Avg24h",       "float",  "PM2.5 Channel 1 24h Average"),
    ("pm25Ch2",             "float",  "PM2.5 Channel 2"),
    ("pm25Ch2Avg24h",       "float",  "PM2.5 Channel 2 24h Average"),
    ("pm25Ch3",             "float",  "PM2.5 Channel 3"),
    ("pm25Ch3Avg24h",       "float",  "PM2.5 Channel 3 24h Average"),
    ("pm25Ch4",             "float",  "PM2.5 Channel 4"),
    ("pm25Ch4Avg24h",       "float",  "PM2.5 Channel 4 24h Average"),
    # ── Standalone batteries / power ─────────────────────────────────────────
    ("battWh65",            "float",  "WH65 Battery"),
    ("battWh40",            "float",  "WH40 Battery"),
    ("battWh80",            "float",  "WH80 Battery"),
    ("battWh57",            "float",  "WH57 Battery"),
    ("battWh68",            "float",  "WH68 Battery"),
    ("battWh90",            "float",  "WH90 Battery"),
    ("battWh25",            "float",  "WH25 Battery"),
    ("battWh26",            "float",  "WH26 Battery"),
    ("pm25Batt1",           "float",  "PM2.5 Sensor 1 Battery"),
    ("pm25Batt2",           "float",  "PM2.5 Sensor 2 Battery"),
    ("pm25Batt3",           "float",  "PM2.5 Sensor 3 Battery"),
    ("pm25Batt4",           "float",  "PM2.5 Sensor 4 Battery"),
    ("ws90CapVolt",         "float",  "WS90 Capacitor Voltage"),
]

# Channel-based state definitions (1–8)
for _i in range(1, 9):
    _D += [
        (f"ch{_i}Temp",       "float", f"Channel {_i} Temperature"),
        (f"ch{_i}Humidity",   "float", f"Channel {_i} Humidity"),
        (f"ch{_i}DewPoint",   "float", f"Channel {_i} Dew Point"),
        (f"ch{_i}Battery",    "float", f"Channel {_i} Battery"),
        (f"soilMoisture{_i}", "float", f"Soil Moisture {_i}"),
        (f"soilTemp{_i}",     "float", f"Soil Temperature {_i}"),
        (f"soilBatt{_i}",     "float", f"Soil Battery {_i}"),
        (f"leafWetness{_i}",  "float", f"Leaf Wetness {_i}"),
    ]

STATE_DEFINITIONS: list[tuple[str, str, str]] = _D
del _D, _i  # type: ignore[name-defined]

# Fast lookup: state_key → (value_type, display_label)
STATE_META: dict[str, tuple[str, str]] = {
    key: (vtype, label) for key, vtype, label in STATE_DEFINITIONS
}

# ──────────────────────────────────────────────────────────────────────────────
# Plugin
# ──────────────────────────────────────────────────────────────────────────────

class Plugin(indigo.PluginBase):

    def __init__(
        self,
        pluginId: str,
        pluginDisplayName: str,
        pluginVersion: str,
        pluginPrefs: indigo.Dict,
    ) -> None:
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        # Logging — remove any handlers indigo.PluginBase already attached so
        # messages don't route to indigo.server.log twice (double logging).
        self.logger.setLevel(logging.DEBUG)
        for _h in self.logger.handlers[:]:
            self.logger.removeHandler(_h)
        self.logger.propagate = False
        self.indigo_log_handler = IndigoLogHandler(pluginDisplayName, logging.INFO)
        self.logger.addHandler(self.indigo_log_handler)
        self.debug: bool = bool(pluginPrefs.get("debugLogging", False))
        if self.debug:
            self.indigo_log_handler.setLevel(logging.DEBUG)

        # Asyncio
        self.event_loop: asyncio.AbstractEventLoop | None = None
        self.loop_thread: threading.Thread | None = None
        self.ecowitt_server: EcoWittListener | None = None

        # Device lookup tables (passkey → device id)
        self._passkey_to_devid: dict[str, int] = {}
        # First device with a blank passkey (accepts any gateway)
        self._open_devid: int | None = None

        # Per-push batched sensor-value updates (gateway metadata is handled
        # separately via _on_push_received so it updates every push regardless
        # of whether individual sensor values changed)
        self._pending: dict[int, dict[str, Any]] = {}
        # Unit priority per pending slot: 0 = preferred unit, 1 = alternate
        self._pending_priority: dict[int, dict[str, int]] = {}
        # Device ids whose _flush_pending is already queued this tick
        self._flush_scheduled: set[int] = set()

        # Sensor keys we've already warned about (unmapped)
        self._warned_sensors: set[str] = set()
        # Running push counter per station passkey for log clarity
        self._push_count: dict[str, int] = {}
        # Per-device accumulation of registered state keys → value type.
        # Grows as data arrives; seeds from dev.states on plugin restart so
        # previously received states are preserved across reloads.
        self._device_seen_states: dict[int, dict[str, str]] = {}

    # ── Startup / Shutdown ────────────────────────────────────────────────────

    def startup(self) -> None:
        self.logger.info("Ecowitt Weather Station plugin starting")
        if self.debug:
            self.logger.info("Debug logging is enabled")

        self._rebuild_device_map()
        if self._open_devid is not None:
            self.logger.info(
                f"Open device (accepts any gateway): id={self._open_devid}"
            )
        for pk, did in self._passkey_to_devid.items():
            self.logger.info(f"Passkey device: PASSKEY={pk!r} → id={did}")
        if not self._passkey_to_devid and self._open_devid is None:
            self.logger.warning(
                "No Ecowitt Gateway Hub devices found — "
                "create one in Indigo before data can be stored"
            )

        self.event_loop = asyncio.new_event_loop()
        self.event_loop.set_exception_handler(self._on_asyncio_exception)
        self.loop_thread = threading.Thread(
            target=self.event_loop.run_forever,
            daemon=True,
            name="EcowittLoop",
        )
        self.loop_thread.start()

        port        = int(self.pluginPrefs.get("listenPort", 45000))
        listen_path = str(self.pluginPrefs.get("listenPath", "/data/report"))

        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._start_server(port, listen_path),
                self.event_loop,
            )
            fut.result(timeout=30)
            self.logger.info(
                f"Ecowitt HTTP server listening on port {port} at path {listen_path}"
            )
        except Exception:
            self.logger.exception("Failed to start Ecowitt HTTP server")

    def shutdown(self) -> None:
        self.logger.info("Ecowitt Weather Station plugin shutting down")
        if self.ecowitt_server and self.event_loop and self.event_loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(
                    self.ecowitt_server.stop(), self.event_loop
                )
                fut.result(timeout=10)
            except Exception:
                self.logger.exception("Error stopping Ecowitt HTTP server")

        if self.event_loop and self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        if self.loop_thread:
            self.loop_thread.join(timeout=5)

    # ── Asyncio exception handler ─────────────────────────────────────────────

    def _on_asyncio_exception(
        self, loop: asyncio.AbstractEventLoop, context: dict
    ) -> None:
        """Routes uncaught asyncio exceptions to Indigo's log."""
        exc = context.get("exception")
        if exc is not None:
            self.logger.error(
                f"Asyncio unhandled exception: {type(exc).__name__}: {exc}"
            )
        else:
            self.logger.error(f"Asyncio error: {context.get('message', context)}")

    # ── Asyncio server ────────────────────────────────────────────────────────

    async def _start_server(self, port: int, listen_path: str) -> None:
        self.ecowitt_server = EcoWittListener(port=port, path=listen_path)
        self.ecowitt_server.new_sensor_cb.append(self._on_new_sensor)

        # Wrap process_data so we get a reliable per-push callback that fires
        # even when individual sensor values are unchanged between pushes.
        # aioecowitt's update_value() skips update_cb when value == old value,
        # so connectionStatus / lastUpdate would stall without this wrapper.
        # The wrapper also catches and logs any processing errors so they appear
        # in Indigo's log rather than only as an aiohttp 500 with no context.
        _orig_process_data = self.ecowitt_server.process_data

        def _patched_process_data(data: dict) -> None:
            # Build a plain dict with defaults for the three fields that
            # extract_station() pops with no fallback (KeyError if absent).
            # Real Ecowitt gateways always send all three; this only helps
            # when testing with curl or very old firmware.
            raw = dict(data)

            # Log every incoming push at DEBUG so the user can see raw data.
            self.logger.debug(
                f"Raw push received — {len(raw)} fields: "
                + ", ".join(f"{k}={v!r}" for k, v in sorted(raw.items()))
            )

            safe = {
                "PASSKEY":     raw.get("PASSKEY", "UNKNOWN"),
                "stationtype": raw.get("stationtype", "Unknown"),
                "model":       raw.get("model", raw.get("stationtype", "Unknown").split("_")[0]),
            }
            safe.update(raw)   # actual data takes precedence over our defaults
            try:
                _orig_process_data(safe)
            except Exception as exc:
                self.logger.error(
                    f"process_data failed — {type(exc).__name__}: {exc}. "
                    f"Fields received: {sorted(raw.keys())}"
                )
                return
            if self.event_loop is not None:
                self.event_loop.call_soon(self._on_push_received, raw)

        self.ecowitt_server.process_data = _patched_process_data
        await self.ecowitt_server.start()

    # ── Per-push handler (runs in asyncio thread via call_soon) ───────────────

    def _on_push_received(self, raw: dict) -> None:
        """Called once per push. Updates connection states unconditionally."""
        passkey = str(raw.get("PASSKEY", ""))
        dev = self._find_device_by_passkey(passkey)
        if dev is None:
            self.logger.warning(
                f"Push received from PASSKEY={passkey!r} — "
                f"no matching Indigo device (create an Ecowitt Gateway Hub device)"
            )
            return

        count = self._push_count.get(passkey, 0) + 1
        self._push_count[passkey] = count

        meta_updates: dict[str, str] = {
            "connectionStatus": "Connected",
            "lastUpdate":       datetime.now(timezone.utc).isoformat(),
        }
        station_type = raw.get("stationtype", "")
        model        = raw.get("model", "")
        if station_type:
            meta_updates["stationType"] = station_type
        if model:
            meta_updates["gatewayModel"] = model

        # Register any metadata states not yet seen (connectionStatus is always
        # in Devices.xml so only the string keys need dynamic registration).
        seen = self._device_seen_states.setdefault(dev.id, {})
        new_keys = [k for k in meta_updates if k != "connectionStatus" and k not in seen]
        if new_keys:
            for k in new_keys:
                seen[k] = STATE_META.get(k, ("string", k))[0]
            dev.stateListOrDisplayStateIdChanged()

        try:
            dev.updateStatesOnServer([{"key": k, "value": v} for k, v in meta_updates.items()])
        except Exception:
            self.logger.exception(f"[{dev.name}] Failed to update connection states")
            return

        sensor_count = sum(
            1 for k in raw
            if k not in ("PASSKEY", "stationtype", "model", "dateutc",
                         "freq", "runtime", "interval", "heap")
        )
        self.logger.debug(
            f"[{dev.name}] Push #{count} from PASSKEY={passkey!r} "
            f"({sensor_count} sensor fields)"
        )

    # ── Per-sensor callbacks (run in asyncio thread) ──────────────────────────

    def _on_new_sensor(self, sensor: EcoWittSensor) -> None:
        """Called by aioecowitt the first time a sensor key is seen."""
        self.logger.info(
            f"New sensor: {sensor.key!r} ({sensor.name}) "
            f"from station {sensor.station.key!r}"
        )
        sensor.update_cb.append(lambda: self._on_sensor_update(sensor))

    def _on_sensor_update(self, sensor: EcoWittSensor) -> None:
        """Called when a sensor value changes. Batches update for _flush_pending."""
        # Log immediately so we know this callback fired even if something fails below.
        self.logger.debug(
            f"_on_sensor_update: {sensor.key!r} = {sensor.value!r}"
        )
        try:
            if sensor.key in SYSTEM_SENSOR_KEYS:
                return  # diagnostic field — not a weather measurement
            if sensor.key not in SENSOR_TO_STATE:
                if sensor.key not in self._warned_sensors:
                    self._warned_sensors.add(sensor.key)
                    self.logger.warning(
                        f"Unmapped sensor key {sensor.key!r} "
                        f"(value={sensor.value!r}) — no Indigo state defined"
                    )
                return

            dev = self._find_device_for_sensor(sensor)
            if dev is None:
                self.logger.debug(
                    f"No device found for sensor {sensor.key!r} "
                    f"(station={sensor.station.key!r})"
                )
                return

            value = sensor.value
            if value is None:
                return

            if isinstance(value, datetime):
                value = value.isoformat()

            state_key, _vtype = SENSOR_TO_STATE[sensor.key]

            # Prefer the unit variant matching pluginPrefs; lower priority number wins.
            units = self.pluginPrefs.get("units", "imperial")
            if units == "metric":
                priority = 1 if sensor.key in IMPERIAL_VARIANT_KEYS else 0
            else:
                priority = 1 if sensor.key in METRIC_VARIANT_KEYS else 0

            dev_pending  = self._pending.setdefault(dev.id, {})
            dev_priority = self._pending_priority.setdefault(dev.id, {})

            if priority > dev_priority.get(state_key, 999):
                return  # higher-priority key already claimed this slot

            dev_priority[state_key] = priority
            dev_pending[state_key]  = value

            self.logger.debug(
                f"[{dev.name}] queued {sensor.key!r} → {state_key} = {value!r}"
            )

            if dev.id not in self._flush_scheduled:
                self._flush_scheduled.add(dev.id)
                if self.event_loop is None:
                    self.logger.error("event_loop is None inside _on_sensor_update")
                    return
                self.event_loop.call_soon(self._flush_pending, dev.id)

        except Exception:
            self.logger.exception(
                f"Error in _on_sensor_update for key {sensor.key!r}"
            )

    def _flush_pending(self, dev_id: int) -> None:
        """Commit all queued sensor-value updates for one device."""
        self._flush_scheduled.discard(dev_id)
        updates  = self._pending.pop(dev_id, {})
        self._pending_priority.pop(dev_id, None)

        if not updates:
            return

        try:
            dev = indigo.devices[dev_id]
        except KeyError:
            self.logger.warning(f"_flush_pending: device {dev_id} no longer exists")
            return

        # Register any state keys seen for the first time this session.
        seen = self._device_seen_states.setdefault(dev_id, {})
        new_keys = [k for k in updates if k not in seen]
        if new_keys:
            for k in new_keys:
                seen[k] = STATE_META.get(k, ("string", k))[0]
            dev.stateListOrDisplayStateIdChanged()

        state_list = [{"key": k, "value": v} for k, v in updates.items()]
        try:
            dev.updateStatesOnServer(state_list)
            self.logger.debug(f"[{dev.name}] wrote {len(state_list)} state(s)")
        except Exception:
            self.logger.exception(
                f"[{dev.name}] updateStatesOnServer failed — "
                f"keys: {[s['key'] for s in state_list]}"
            )

    # ── Device lookup ─────────────────────────────────────────────────────────

    def _rebuild_device_map(self) -> None:
        self._passkey_to_devid.clear()
        self._open_devid = None
        for dev in indigo.devices.iter("self"):
            self._register_device(dev)

    def _register_device(self, dev: indigo.Device) -> None:
        passkey = str(dev.pluginProps.get("passkey", "")).strip()
        if passkey:
            self._passkey_to_devid[passkey] = dev.id
        elif self._open_devid is None:
            self._open_devid = dev.id

    def _find_device_by_passkey(self, passkey: str) -> indigo.Device | None:
        """Look up a device by raw PASSKEY string from the gateway POST."""
        if passkey and passkey in self._passkey_to_devid:
            try:
                return indigo.devices[self._passkey_to_devid[passkey]]
            except KeyError:
                pass
        if self._open_devid is not None:
            try:
                return indigo.devices[self._open_devid]
            except KeyError:
                self._open_devid = None
        for dev in indigo.devices.iter("self"):
            return dev
        return None

    def _find_device_for_sensor(
        self, sensor: EcoWittSensor
    ) -> indigo.Device | None:
        """Look up a device by the station passkey on an EcoWittSensor."""
        return self._find_device_by_passkey(sensor.station.key or "")

    # ── Stale detection ───────────────────────────────────────────────────────

    def runConcurrentThread(self) -> None:
        """Mark devices Stale when no push arrives for > 5 minutes."""
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
                    dev.updateStateOnServer("connectionStatus", value="Stale")
                    self.logger.warning(
                        f"[{dev.name}] marked Stale — "
                        f"no push for {int(age // 60)}m {int(age % 60)}s"
                    )
            except Exception:
                pass

    # ── Device lifecycle ──────────────────────────────────────────────────────

    def deviceStartComm(self, dev: indigo.Device) -> None:
        self.logger.info(f"Starting device: {dev.name}")
        self._register_device(dev)

        # Seed _device_seen_states from any states persisted by previous sessions
        # so they are preserved across plugin restarts. For a brand-new device,
        # dev.states only contains 'connectionStatus' (from Devices.xml), so nothing
        # is pre-seeded and states appear dynamically as the first push arrives.
        seen = self._device_seen_states.setdefault(dev.id, {})
        if not seen:
            for key in dev.states:
                if key == "connectionStatus":
                    continue
                meta = STATE_META.get(key)
                seen[key] = meta[0] if meta else "string"

        # Rebuild state list from whatever is in seen (may be empty for new devices).
        dev.stateListOrDisplayStateIdChanged()
        dev.updateStateOnServer("connectionStatus", "Never")

    def deviceStopComm(self, dev: indigo.Device) -> None:
        self.logger.info(f"Stopping device: {dev.name}")
        passkey = str(dev.pluginProps.get("passkey", "")).strip()
        if passkey:
            self._passkey_to_devid.pop(passkey, None)
        if self._open_devid == dev.id:
            self._open_devid = None
            for other in indigo.devices.iter("self"):
                if other.id != dev.id:
                    if not str(other.pluginProps.get("passkey", "")).strip():
                        self._open_devid = other.id
                        break
        self._device_seen_states.pop(dev.id, None)

    def deviceUpdated(
        self, origDev: indigo.Device, newDev: indigo.Device
    ) -> None:
        super().deviceUpdated(origDev, newDev)
        self._rebuild_device_map()

    # ── Dynamic state list ────────────────────────────────────────────────────

    def getDeviceStateList(self, dev: indigo.Device) -> list:
        """Return only the states that have actually been received for this device.

        On a brand-new device the list is empty (except connectionStatus from
        Devices.xml).  As pushes arrive, _flush_pending / _on_push_received call
        stateListOrDisplayStateIdChanged() which triggers this method again, causing
        Indigo to register only the states that have been seen.  Previously received
        states persisted in dev.states are re-seeded into _device_seen_states in
        deviceStartComm so they survive plugin restarts.
        """
        state_list = super().getDeviceStateList(dev)
        existing_keys = {s.get("Key", "") for s in state_list}

        seen = self._device_seen_states.get(dev.id, {})
        added = 0
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
            added += 1

        self.logger.debug(
            f"getDeviceStateList({dev.name}): {added} dynamic state(s) "
            f"(total {len(state_list)})"
        )
        return state_list

    # ── Preferences ───────────────────────────────────────────────────────────

    def validatePrefsConfigUi(self, valuesDict: indigo.Dict):
        errors = indigo.Dict()
        try:
            port = int(valuesDict.get("listenPort", "45000"))
            if not (1024 <= port <= 65535):
                errors["listenPort"] = "Port must be between 1024 and 65535"
        except (ValueError, TypeError):
            errors["listenPort"] = "Port must be an integer"

        listen_path = str(valuesDict.get("listenPath", "/data/report")).strip()
        if not listen_path.startswith("/"):
            errors["listenPath"] = "Path must start with /"

        if len(errors) > 0:
            return (False, valuesDict, errors)
        return (True, valuesDict)

    def closedPrefsConfigUi(
        self, valuesDict: indigo.Dict, userCancelled: bool
    ) -> None:
        if userCancelled:
            return

        new_debug = bool(valuesDict.get("debugLogging", False))
        self.debug = new_debug
        self.indigo_log_handler.setLevel(
            logging.DEBUG if new_debug else logging.INFO
        )
        if new_debug:
            self.logger.info("Debug logging enabled")

        new_port  = int(valuesDict.get("listenPort", 45000))
        new_path  = str(valuesDict.get("listenPath", "/data/report"))
        old_port  = int(self.pluginPrefs.get("listenPort", 45000))
        old_path  = str(self.pluginPrefs.get("listenPath", "/data/report"))

        if new_port != old_port or new_path != old_path:
            self.logger.info(
                f"Listen address changed → restarting server "
                f"on port {new_port} at {new_path}"
            )
            if self.ecowitt_server and self.event_loop:
                try:
                    fut = asyncio.run_coroutine_threadsafe(
                        self.ecowitt_server.stop(), self.event_loop
                    )
                    fut.result(timeout=10)
                except Exception:
                    self.logger.exception(
                        "Error stopping server during preference restart"
                    )
            if self.event_loop:
                try:
                    fut = asyncio.run_coroutine_threadsafe(
                        self._start_server(new_port, new_path), self.event_loop
                    )
                    fut.result(timeout=30)
                    self.logger.info(
                        f"Ecowitt server restarted on port {new_port} at {new_path}"
                    )
                except Exception:
                    self.logger.exception("Error restarting server after pref change")
