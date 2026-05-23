![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Ecowitt Gateway Setup

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## How the Local Push Protocol Works

Ecowitt gateways support two upload methods:

| Method | How it works |
|---|---|
| **Ecowitt Cloud** | Gateway sends data to Ecowitt's servers; you view it in the app |
| **Customized Server (local push)** | Gateway POSTs data directly to any HTTP server on your network |

This plugin uses the **Customized Server** method with **Ecowitt protocol**. Your gateway sends an HTTP POST to your Indigo Mac's IP address every 16–60 seconds. No internet connection is required once the gateway is configured.

> **Protocol choice matters.** There are two protocol options in the Customized Server settings — **Ecowitt** and **Wunderground**. You must select **Ecowitt**. The Wunderground format sends a different field set and will not be parsed correctly.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Before You Start — Find Your Mac's IP Address

The gateway needs to reach your Indigo Mac by IP address. Find it in:

**System Settings → Network → [your connection] → IP Address**

Or in Terminal:
```
ipconfig getifaddr en0   # Wi-Fi
ipconfig getifaddr en1   # Ethernet
```

Use a static IP (reserved DHCP lease on your router) so the gateway doesn't lose track of the Mac if addresses change.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Connection Settings

These values must match exactly between the gateway and the plugin:

| Field | Default | Notes |
|---|---|---|
| Protocol | Ecowitt | Must be Ecowitt, not Wunderground |
| Server IP / Hostname | *(your Mac's LAN IP)* | e.g. `192.168.1.50` |
| Path | `/data/report` | Must match the plugin's **Listen Path** setting |
| Port | `45000` | Must match the plugin's **Listen Port** setting |
| Upload Interval | 16 s – 60 s | 16 s recommended for responsive Indigo triggers |

> **Path note:** The plugin normalises trailing slashes, so `/data/report` and `/data/report/` both work. However, enter the path without a trailing slash in the gateway settings for clarity.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Method 1: Ecowitt App (iOS / Android)

The **Ecowitt** app (not WSView Plus) is the recommended method for newer gateways. It provides a cleaner interface and works with all current models.

1. Open the **Ecowitt** app
2. Tap the **menu icon** (top-left) → **Devices**
3. Under **My Devices**, tap your station
4. Tap the **⋯ ellipsis icon** (top-right)
5. Tap **Others**
6. Tap **DIY Upload Servers**
7. In the **Supported Servers** list, tap **Customized**
8. Set **Protocol Type** → **Ecowitt**
9. Enter:
   - **Server IP / Hostname**: your Mac's LAN IP
   - **Path**: `data/report` *(the app prepends `/` automatically — do not include the leading slash here)*
   - **Port**: `45000`
10. Tap **Save**

The gateway will begin pushing data within one upload interval.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Method 2: WSView Plus App (iOS / Android)

**WSView Plus** is the older companion app. The menu path is slightly different:

1. Open **WSView Plus**
2. Tap your station in the device list
3. Tap **Weather Services** (or **Upload Settings**)
4. Scroll to **Customized** and enable it
5. Set **Protocol Type Same As** → **Ecowitt**
6. Enter the Server IP, Path (`/data/report`), and Port (`45000`)
7. Save

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Method 3: Gateway Web UI (browser)

Every Ecowitt gateway hosts its own web UI. This is the most reliable method and doesn't require a phone.

### Step 1 — Find the gateway's IP address

Check your router's DHCP client list. Ecowitt gateways typically appear as **GW3000**, **GW2000**, or similar. Alternatively, the Ecowitt or WSView Plus app shows the IP in the device detail screen.

### Step 2 — Open the web UI

Navigate to `http://<gateway-ip>` in a browser on the same network. You should see the gateway's dashboard.

### Step 3 — Go to Weather Services

The navigation path varies slightly by model:

| Model | Menu path |
|---|---|
| GW3000 | **Weather Services** tab |
| GW2000 | **Weather Services** tab |
| GW1200 | **Weather Services** tab |
| HP2560/64 console | **Settings → Upload** |

### Step 4 — Configure Customized upload

1. Scroll to the **Customized** section
2. Set the radio button to **🔘 Enable**
3. Set **Protocol Type Same As** → **🔘 Ecowitt**
4. Enter:
   - **Server IP / Hostname**: your Mac's LAN IP
   - **Path**: `/data/report`
   - **Port**: `45000`
   - **Upload Interval**: `16` (seconds)
5. Click **Save**

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Per-Gateway Model Notes

### GW3000

- Has on-board data storage — data is not lost if the Mac is offline
- Both Ethernet and Wi-Fi supported; Ethernet is recommended for reliability
- The web UI is accessible on both the Ethernet IP and the Wi-Fi IP if both are connected
- Supports the highest number of simultaneous sensor attachments

### GW2000

- Ethernet + Wi-Fi, no on-board storage
- Web UI path: **Weather Services → Customized**
- Supports WH45/WH46 CO₂ sensors, WN34 soil temperature probes, LDS liquid sensors

### GW1200

- Wi-Fi only
- Lighter sensor support; does not support WN34 or LDS sensors
- Fewer multi-channel slots than GW2000/GW3000

### HP2560 / HP2564 Console

- These are display consoles that also act as gateways
- Upload settings are under **Settings → Upload** in the web UI
- The PASSKEY is visible in the upload settings screen

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Per-Sensor Type Notes

Different sensor combinations affect which states appear in the Indigo Hub device. Here is what each common sensor or sensor pack produces:

### WS90 (7-in-1 weather sensor, piezoelectric)

The WS90 combines anemometer, rain gauge (piezoelectric), temperature, humidity, solar, and UV in a single unit. It **does not have a traditional tipping-bucket gauge** — all rain readings come from the `*_piezo` keys.

States produced: `windSpeed`, `windGust`, `windDirection`, `rainRatePiezo`, `dailyRainPiezo`, `solarRadiation`, `uvIndex`, `outdoorTemp`, `outdoorHumidity`, `ws90CapVolt` (supercapacitor voltage).

> The WS90 is powered entirely by its supercapacitor. The `ws90CapVolt` state shows the charge level. Readings may be absent or inaccurate when the cap voltage is very low (overnight, overcast conditions).

### WH65 (traditional 7-in-1 outdoor sensor)

Uses a tipping-bucket rain gauge. States produced: `windSpeed`, `windGust`, `windDirection`, `rainRate`, `dailyRain`, `solarRadiation`, `uvIndex`, `outdoorTemp`, `outdoorHumidity`, `battWh65`.

### WH40 (self-emptying rain gauge)

Supplements or replaces the tipping-bucket gauge. Produces `rainRate`, `dailyRain`, etc. States are shared with WH65 rain fields — whichever sensor is primary wins. Battery: `battWh40`.

### WH51 (soil moisture, up to 16 channels)

Each channel produces `soilMoisture1`–`soilMoisture16`, `soilAd1`–`soilAd16` (raw ADC), `soilBatt1`–`soilBatt16`.

### WN34 (soil/water temperature probe, up to 8 channels)

Produces `soilTemp1`–`soilTemp8`, `soilTempBatt1`–`soilTempBatt8`.

### WH31 (multi-channel temp/humidity, up to 8 channels)

Each channel produces `ch1Temp`–`ch8Temp`, `ch1Humidity`–`ch8Humidity`, `ch1DewPoint`–`ch8DewPoint`, `ch1Battery`–`ch8Battery`.

### WH57 (lightning detector)

Produces `lightningDist`, `lightningCount`, `lightningLastTime`, `battWh57`.

### WH45 (CO₂ + PM2.5 + PM10 indoor air quality)

Produces `co2`, `co2Avg24h`, `pm25Co2`, `pm25Co2Avg24h`, `pm10Co2`, `pm10Co2Avg24h`, `tempCo2`, `humiCo2`, `battCo2`.

### WH46 (precision particulate matter: PM1, PM2.5, PM4, PM10)

Produces all WH45 states plus `pm1Co2`, `pm4Co2` and their 24h averages.

### WH55 (leak detector, up to 4 channels)

Produces `leak1`–`leak4` (0 = dry, 1 = wet), `leakBatt1`–`leakBatt4`.

### WH41 / WH43 (outdoor PM2.5, up to 4 channels)

Produces `pm25Ch1`–`pm25Ch4`, `pm25Ch1Avg24h`–`pm25Ch4Avg24h`, `pm25Batt1`–`pm25Batt4`.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Finding Your PASSKEY

The PASSKEY is a 32-character hex string that uniquely identifies each gateway. It is embedded in every POST the gateway sends.

**To find your PASSKEY:**

1. Enable **Debug Logging** in **Plugins → Ecowitt Weather Station → Configure…**
2. Restart the plugin
3. Wait for the next push (up to one upload interval)
4. In the Indigo log, look for a line like:
   ```
   Raw push received — 47 fields: PASSKEY='1054F475A49C8247A94571A1F3841D3E', ...
   ```
5. Copy the 32-character value

Alternatively, open the gateway's web UI → **Weather Services** → **Customized** — the PASSKEY is sometimes shown there, or you can find it in the **About** section.

See [Device Setup](Device-Setup) for how to use the PASSKEY in an Indigo Hub device.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Verifying the Connection

After saving the gateway settings, verify data is flowing:

1. In the Indigo log, look for:
   ```
   [My Gateway] Push #1 from PASSKEY='...' (47 sensor fields)
   ```
2. Open the Hub device — states should appear within a few seconds of the first push
3. `connectionStatus` should show **Connected**

If nothing appears, see [Troubleshooting](Troubleshooting).
