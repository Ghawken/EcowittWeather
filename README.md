# Ecowitt Weather Station — Indigo Plugin

Receives local weather data from Ecowitt gateways (GW1000, GW2000, GW3000, HP2560, etc.) via HTTP push using the **Ecowitt protocol**. All sensor readings are stored as states on a single Indigo device per gateway.

---

## Requirements

- Indigo 2025.2 or later (API 3.4+)
- An Ecowitt gateway configured to push to this Mac over your local network
- [`aioecowitt`](https://github.com/home-assistant-libs/aioecowitt) ≥ 2025.9.2 (installed automatically by Indigo from `requirements.txt`)

### Ecowitt Gateway/Hubs supported
GW1200 Wi-Fi Gateway
GW2000 Ethernet and Wi-Fi Gateway
GW3000 Ethernet and Wi-Fi Gateway with Data Storage

### Sensors 
WH51 Wireless Soil Moisture Sensor
WH40 Wireless Self-emptying Rain Gauge Sensor
WH57 Outdoor Wireless Lightning Detection Sensor
WS90 Wireless 7-in-1 Weather Sensor

---

Creates a EcoWitt Gateway Hub device for each gateway.   This single Indigo device contains all the sensors.
If new sensors are added - (Gateway supports quite a lot) then the new sensors will be created automatically and appear as a state.
If sensors are removed (the states remain in the Indigo device but do not update).  If this triggers OCD tendenceies then delete the indigo device and start afresh.


---
## Installation

1. Download the latest release `.indigoPlugin` file.
2. Double-click it — Indigo will install the plugin automatically.
3. Configure the plugin (see below) and create at least one **Ecowitt Gateway Hub** device.

---

## Plugin Configuration

Open **Plugins → Ecowitt Weather Station → Configure…**

| Setting | Default         | Description |
|---|-----------------|---|
| Listen Port | `45000`         | TCP port the plugin's HTTP server listens on. Must be reachable from the gateway. |
| Listen Path | `/data/report/` | URL path the gateway POSTs to. Must match WSView Plus settings exactly. |
| Units | Imperial        | Preferred unit system. When aioecowitt provides both °F and °C, the preferred variant wins. |
| Debug Logging | Off             | Logs every push and sensor update to the Indigo log. |

> **Firewall:** macOS may block incoming connections on the listen port. Allow it in **System Settings → Network → Firewall** or it will be prompted on first connection.

---

# Gateway Setup (WSView Plus)

In the **WSView Plus** app, configure a **Customised** upload server:
This is in the Web Tab of the Gateway settings, or via the App.

## Option 1: Use the Ecowitt app (on your phone):

In the top-left corner, select the menu icon () and select Devices.
Under My Devices, select your Ecowitt station.
In the top-right corner, select the ellipsis icon ().
From the list, select Others.
Select the DIY Upload Servers button, and from the Supported Servers List, select Customized.
From the Protocol Type Same As list, select Ecowitt.
Enter the Server IP / Host Name, Path, and Port from the integration.
The path has to match! Remove the first forward slash from the path, as the app will prepend one.
Save your settings.

## Option 2: Navigate to the Ecowitt web UI in a browser at the station IP address:

Select Weather Services then scroll down to the Customized section.
Under Customized, select 🔘 Enable and Protocol Type Same As 🔘 Ecowitt.
Enter the Server IP / Host Name, Path, and Port from the integration.
Save your settings.



| Field | Value |
|---|---|
| Protocol | Ecowitt |
| Server IP / Hostname | IP address of your Indigo Mac |
| Path | `/data/report` (must match plugin setting) |
| Port | `45000` (must match plugin setting) |
| Upload Interval | 16 s – 60 s (recommended) |

---

## Device Setup

Create one **Ecowitt Gateway Hub** device per physical gateway:

- **PASSKEY** (optional): paste the PASSKEY value your gateway sends. Leave blank to accept data from any gateway — useful when you have a single gateway.

The gateway model and station type are auto-populated from the first push received. All sensor states are created dynamically — a brand-new device has only `connectionStatus` until the first push arrives.

---

## Supported Sensors

States are created only for sensors your specific gateway and attached sensors actually report. States persist across plugin restarts.

### Gateway metadata
`connectionStatus` · `lastUpdate` · `gatewayModel` · `stationType`

### Outdoor
`outdoorTemp` · `outdoorHumidity` · `dewPoint` · `feelsLike` · `windChill`

### Indoor
`indoorTemp` · `indoorHumidity` · `indoorDewPoint`

### Wind
`windDirection` · `windDirAvg10m` · `windSpeed` · `windSpeedAvg10m` · `windGust` · `maxDailyGust`

### Rain (tipping-bucket gauge)
`rainRate` · `eventRain` · `hourlyRain` · `dailyRain` · `weeklyRain` · `monthlyRain` · `yearlyRain`

### Rain (WS90 piezoelectric gauge)
`rainRatePiezo` · `eventRainPiezo` · `hourlyRainPiezo` · `dailyRainPiezo` · `weeklyRainPiezo` · `monthlyRainPiezo` · `yearlyRainPiezo` · `last24hRainPiezo` · `rainStatePiezo`

### Pressure
`pressureRelative` · `pressureAbsolute`

### Solar / UV
`solarRadiation` · `solarRadiationLux` · `uvIndex`

### Vapour Pressure Deficit
`vpd`

### CO₂ / Air Quality (WH45 / WH46)
`co2` · `co2Avg24h` · `co2Indoor` · `co2IndoorAvg24h` · `pm25Co2` · `pm25Co2Avg24h` · `pm1Co2` · `pm4Co2` · `pm10Co2` (+ 24h averages) · `humiCo2` · `tempCo2`

### Lightning (WH57)
`lightningDist` · `lightningCount` · `lightningLastTime`

### Leak sensors (WH55)
`leak1` – `leak4`

### PM2.5 channels (WH41 / WH43)
`pm25Ch1` – `pm25Ch4` (+ 24h averages)

### Multi-channel temperature/humidity (WH31, WH51, WH57 etc.)
`ch1Temp` – `ch8Temp` · `ch1Humidity` – `ch8Humidity` · `ch1DewPoint` – `ch8DewPoint` · `soilMoisture1` – `soilMoisture8` · `soilTemp1` – `soilTemp8` · `leafWetness1` – `leafWetness8`

### Battery / Power
`battWh65` · `battWh40` · `battWh80` · `battWh57` · `battWh68` · `battWh90` · `battWh25` · `battWh26` · `pm25Batt1`–`pm25Batt4` · `ch1Battery`–`ch8Battery` · `soilBatt1`–`soilBatt8` · `ws90CapVolt`

---

## Stale Detection

If no push is received for more than **5 minutes**, `connectionStatus` is set to `Stale`. It returns to `Connected` on the next push. The check runs every 60 seconds.

---

## Multiple Gateways

Create one **Ecowitt Gateway Hub** device per gateway and set the PASSKEY on each. Data from each gateway is routed to its matching device. All gateways share the same listen port and path.

---

## Troubleshooting

**No data received**
- Confirm the gateway is configured for **Ecowitt protocol** (not Wunderground) in WSView Plus.
- Check the path matches exactly — `/data/report/` with  trailing slash.
- Run `sudo tcpdump -ni any -A port 45000` to confirm packets are arriving at the Mac.

**States not appearing**
- Enable **Debug Logging** in plugin preferences and reload the plugin. The log will show sensor discovery and state registration.

**"No matching Indigo device" warning**
- Create an Ecowitt Gateway Hub device, or if one already exists, check the PASSKEY matches.

---

## Credits

- Uses [`aioecowitt`](https://github.com/home-assistant-libs/aioecowitt) by the Home Assistant team.
- Dynamic state pattern adapted from [GhostXML](https://github.com/IndigoDomotics/GhostXML) by IndigoDomotics.

