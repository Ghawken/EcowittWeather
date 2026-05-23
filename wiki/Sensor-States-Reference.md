![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Sensor States Reference

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

States are created only for sensors your specific gateway and attached sensors actually report. A brand-new Hub device starts with only `connectionStatus` — all other states appear dynamically as data is received.

All units shown are for the **Imperial** setting. With **Metric** selected, temperature is °C, speed is km/h, pressure is hPa, and precipitation is mm.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Gateway Metadata

These states appear on the first push regardless of sensors attached.

| State key | Type | Description |
|---|---|---|
| `connectionStatus` | string | `Connected`, `Stale`, or `Never` |
| `lastUpdate` | string | ISO 8601 UTC timestamp of last push |
| `gatewayModel` | string | Gateway firmware ID, e.g. `GW3000C_V1.2.0` |
| `stationType` | string | Station type string from gateway |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Outdoor Conditions

| State key | Type | Unit (Imperial) | Description |
|---|---|---|---|
| `outdoorTemp` | float | °F | Outdoor temperature |
| `outdoorHumidity` | float | % | Outdoor relative humidity |
| `dewPoint` | float | °F | Dew point (calculated) |
| `feelsLike` | float | °F | Apparent temperature (feels like) |
| `windChill` | float | °F | Wind chill |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Indoor Conditions

Reported by the gateway's built-in indoor sensor or WH25/WH26.

| State key | Type | Unit (Imperial) | Description |
|---|---|---|---|
| `indoorTemp` | float | °F | Indoor temperature |
| `indoorHumidity` | float | % | Indoor relative humidity |
| `indoorDewPoint` | float | °F | Indoor dew point |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Wind

| State key | Type | Unit (Imperial) | Description |
|---|---|---|---|
| `windDirection` | float | ° (0–360) | Instantaneous wind direction |
| `windDirAvg10m` | float | ° | Wind direction 10-minute average |
| `windSpeed` | float | mph | Instantaneous wind speed |
| `windSpeedAvg10m` | float | mph | Wind speed 10-minute average |
| `windGust` | float | mph | Wind gust (max in recent interval) |
| `maxDailyGust` | float | mph | Maximum gust speed today |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Rain — Traditional Tipping-Bucket Gauge

Reported by WH65, WH40, or a built-in tipping-bucket gauge. **Not reported by WS90** — see Piezoelectric Rain below.

| State key | Type | Unit (Imperial) | Description |
|---|---|---|---|
| `rainRate` | float | in/hr | Current rain rate |
| `eventRain` | float | in | Rain total for current event |
| `hourlyRain` | float | in | Rain total this hour |
| `dailyRain` | float | in | Rain total today |
| `weeklyRain` | float | in | Rain total this week |
| `monthlyRain` | float | in | Rain total this month |
| `yearlyRain` | float | in | Rain total this year |
| `totalRain` | float | in | All-time rain total |
| `last24hRain` | float | in | Rain total in the last 24 hours |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Rain — WS90 Piezoelectric Gauge

The WS90 uses a piezoelectric sensor instead of a tipping bucket. Its rain data arrives under separate key names (with `Piezo` suffix in Indigo).

| State key | Type | Unit (Imperial) | Description |
|---|---|---|---|
| `rainRatePiezo` | float | in/hr | Current rain rate |
| `eventRainPiezo` | float | in | Rain for current event |
| `hourlyRainPiezo` | float | in | Rain this hour |
| `dailyRainPiezo` | float | in | Rain today |
| `weeklyRainPiezo` | float | in | Rain this week |
| `monthlyRainPiezo` | float | in | Rain this month |
| `yearlyRainPiezo` | float | in | Rain this year |
| `last24hRainPiezo` | float | in | Rain in last 24 hours |
| `rainStatePiezo` | int | — | Rain state: `0` = dry, `1` = raining |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Pressure

| State key | Type | Unit (Imperial) | Description |
|---|---|---|---|
| `pressureRelative` | float | inHg | Sea-level (relative) pressure |
| `pressureAbsolute` | float | inHg | Station (absolute) pressure |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Solar Radiation & UV

| State key | Type | Unit | Description |
|---|---|---|---|
| `solarRadiation` | float | W/m² | Solar radiation |
| `solarRadiationLux` | float | lux | Solar radiation in lux |
| `uvIndex` | float | — | UV index |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Vapour Pressure Deficit

| State key | Type | Unit | Description |
|---|---|---|---|
| `vpd` | float | hPa | Vapour pressure deficit |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## CO₂ and Air Quality (WH45 / WH46)

| State key | Type | Unit | Description |
|---|---|---|---|
| `co2` | float | ppm | CO₂ (outdoor sensor) |
| `co2Avg24h` | float | ppm | CO₂ 24h average |
| `co2Indoor` | float | ppm | CO₂ (indoor console sensor) |
| `co2IndoorAvg24h` | float | ppm | Indoor CO₂ 24h average |
| `tempCo2` | float | °F | Temperature reading from WH45/WH46 |
| `humiCo2` | float | % | Humidity reading from WH45/WH46 |
| `pm25Co2` | float | µg/m³ | PM2.5 from WH45 |
| `pm25Co2Avg24h` | float | µg/m³ | PM2.5 24h average (WH45) |
| `pm1Co2` | float | µg/m³ | PM1 from WH46 |
| `pm1Co2Avg24h` | float | µg/m³ | PM1 24h average |
| `pm4Co2` | float | µg/m³ | PM4 from WH46 |
| `pm4Co2Avg24h` | float | µg/m³ | PM4 24h average |
| `pm10Co2` | float | µg/m³ | PM10 from WH45/WH46 |
| `pm10Co2Avg24h` | float | µg/m³ | PM10 24h average |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## PM2.5 Channels — WH41 / WH43 (outdoor)

Up to 4 outdoor PM2.5 sensor channels.

| State key | Type | Unit | Description |
|---|---|---|---|
| `pm25Ch1` – `pm25Ch4` | float | µg/m³ | PM2.5 on channels 1–4 |
| `pm25Ch1Avg24h` – `pm25Ch4Avg24h` | float | µg/m³ | 24h average for each channel |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Lightning (WH57)

| State key | Type | Unit | Description |
|---|---|---|---|
| `lightningDist` | float | miles / km | Distance to last detected lightning strike |
| `lightningCount` | float | — | Lightning strike count today |
| `lightningLastTime` | string | ISO 8601 | Timestamp of last detected strike |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Leak Sensors (WH55) — up to 4 channels

| State key | Type | Description |
|---|---|---|
| `leak1` – `leak4` | int | `0` = dry, `1` = leak detected |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Multi-Channel Temperature / Humidity (WH31) — channels 1–8

| State key | Type | Unit | Description |
|---|---|---|---|
| `ch1Temp` – `ch8Temp` | float | °F | Channel temperature |
| `ch1Humidity` – `ch8Humidity` | float | % | Channel humidity |
| `ch1DewPoint` – `ch8DewPoint` | float | °F | Channel dew point |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Soil Moisture (WH51) — channels 1–16

| State key | Type | Unit | Description |
|---|---|---|---|
| `soilMoisture1` – `soilMoisture16` | float | % | Soil moisture by channel |
| `soilAd1` – `soilAd16` | float | — | Raw ADC value (diagnostic) |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Soil Temperature Probes (WN34) — channels 1–8

| State key | Type | Unit | Description |
|---|---|---|---|
| `soilTemp1` – `soilTemp8` | float | °F | Soil/water temperature by channel |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Leaf Wetness — channels 1–8

| State key | Type | Unit | Description |
|---|---|---|---|
| `leafWetness1` – `leafWetness8` | float | — | Leaf wetness index by channel |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## LDS Liquid Detection Sensors — channels 1–4

| State key | Type | Description |
|---|---|---|
| `depth1` – `depth4` | float | Liquid depth |
| `thi1` – `thi4` | float | THI reading |
| `air1` – `air4` | float | Air reading |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Battery and Power States

Battery values are typically `0` (OK) or `1` (low) for discrete sensors, or a voltage/percentage for others. Exact meaning varies by sensor.

| State key | Description |
|---|---|
| `battWh65` | WH65 outdoor sensor battery |
| `battWh40` | WH40 rain gauge battery |
| `battWh80` | WH80 anemometer battery |
| `battWh57` | WH57 lightning sensor battery |
| `battWh68` | WH68 solar-powered anemometer |
| `battWh90` | WH90 battery |
| `battWh25` | WH25 indoor sensor battery |
| `battWh26` | WH26 indoor sensor battery |
| `battWh85` | WH85 battery |
| `battCo2` | WH45/WH46 CO₂ sensor battery |
| `battConsole` | Console battery |
| `ws90CapVolt` | WS90 supercapacitor voltage (V) |
| `ws85CapVolt` | WS85 supercapacitor voltage (V) |
| `pm25Batt1` – `pm25Batt8` | PM2.5 sensor batteries (WH41/WH43) |
| `ch1Battery` – `ch8Battery` | Multi-channel temp/humidity sensor batteries |
| `soilBatt1` – `soilBatt16` | Soil moisture sensor batteries |
| `soilTempBatt1` – `soilTempBatt8` | Soil temperature probe batteries |
| `leakBatt1` – `leakBatt4` | Leak sensor batteries |
| `leafBatt1` – `leafBatt8` | Leaf wetness sensor batteries |
| `ldsBatt1` – `ldsBatt4` | LDS sensor batteries |
