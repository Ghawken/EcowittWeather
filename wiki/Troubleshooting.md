![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Troubleshooting

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Quick Diagnostic Checklist

Before diving into specific issues, work through this checklist:

- [ ] Plugin is installed and enabled (green dot in Plugins menu)
- [ ] No startup errors in the Indigo log (`Ecowitt HTTP server listening on port 45000`)
- [ ] Gateway is configured with correct Server IP, Path, and Port (see [Gateway Setup](Ecowitt-Gateway-Setup))
- [ ] Protocol is set to **Ecowitt** (not Wunderground)
- [ ] At least one Ecowitt Gateway Hub device exists in Indigo
- [ ] macOS Firewall allows inbound connections on port 45000

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## No Data Received

**Symptom:** Hub device shows `connectionStatus: Never`. No log entries from the plugin after startup.

### 1. Confirm the server is running

Check the Indigo log for:
```
Ecowitt HTTP server listening on port 45000 at path /data/report
```

If this line is missing, the server failed to start. Look for an error immediately after the startup message. Common causes: the port is in use by another application.

To check if another process is using the port:
```bash
sudo lsof -nP -iTCP:45000 -sTCP:LISTEN
```

### 2. Confirm packets are reaching the Mac

Run this in Terminal while waiting for a push (adjust port if needed):
```bash
sudo tcpdump -ni any -A port 45000
```

If lines appear when the gateway should be pushing, the network layer is working. If nothing appears, the problem is between the gateway and the Mac (wrong IP, wrong port, or a network/firewall block).

### 3. Check the macOS Firewall

**System Settings → Network → Firewall → Options…**

Confirm Indigo is listed as allowed. If it's blocked, change it to Allow. If Indigo is not in the list, try removing the block for port 45000 in your router as well.

You can also temporarily disable the macOS Firewall to test whether it is the cause.

### 4. Confirm gateway settings

- Open the gateway's web UI or WSView Plus / Ecowitt app
- Confirm Protocol = **Ecowitt** (not Wunderground)
- Confirm the Server IP matches your Mac's current LAN IP
- Confirm Path = `/data/report` (must match the plugin's Listen Path exactly)
- Confirm Port = `45000` (must match the plugin's Listen Port)

### 5. Check that the gateway is on the same network

Confirm the Mac and gateway are on the same LAN segment, or that routing between them is configured. The gateway cannot reach the Mac via the internet unless you have a specific port-forwarding or VPN setup.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## States Not Appearing

**Symptom:** Data is arriving (connectionStatus shows Connected, push count increases in debug log) but sensor states are not populating.

### Enable Debug Logging

Open **Plugins → Ecowitt Weather Station → Configure…** → enable **Debug Logging** → OK.

After the next push, the log should show:
```
Raw push received — 47 fields: PASSKEY='...', tempf='72.4', ...
_on_sensor_update: 'tempf' = 72.4
[My Station] queued 'tempf' → outdoorTemp = 72.4
[My Station] wrote 12 state(s)
```

If `_on_sensor_update` lines appear but no state write follows, there may be a state registration issue — try reloading the plugin.

### Check for unmapped sensor keys

Look for log lines like:
```
Unmapped sensor key 'newkey' (value='...') — no Indigo state defined
```

This means the gateway is sending a field the plugin doesn't recognise. Please [open an issue](https://github.com/Ghawken/EcowittWeather/issues) with the key name and value so it can be added.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## "No matching Indigo device" Warning

**Symptom:** Indigo log shows:
```
Push received from PASSKEY='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' — 
no matching Indigo device (create an Ecowitt Gateway Hub device)
```

**Causes and fixes:**

| Cause | Fix |
|---|---|
| No Hub device created yet | Create an Ecowitt Gateway Hub device in Indigo |
| Hub device has a PASSKEY set that doesn't match the gateway | Clear the PASSKEY field, or set it to match the value in the log |
| Hub device was deleted | Recreate it |

The PASSKEY in the warning message is the exact value your gateway is sending. Copy it and paste it into the Hub device's PASSKEY field, or leave the PASSKEY field blank to accept any gateway.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## "Unmonitored endpoint" Error

**Symptom:** Indigo log shows:
```
Unmonitored endpoint: POST '/wrong/path' from 192.168.1.x — 
plugin expects POST to '/data/report'
```

The gateway is POSTing to a different path than the plugin expects.

**Fix:** In the gateway's Customized upload settings, set the Path to exactly `/data/report` (or whatever you have configured in **Plugin Configuration → Listen Path**).

> If the Ecowitt app strips the leading `/`, ensure you enter `data/report` in the app (it prepends `/` automatically). In the web UI, enter the full `/data/report`.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## connectionStatus Keeps Going Stale

**Symptom:** `connectionStatus` frequently changes to `Stale` even when the gateway appears to be running.

Stale is triggered when no push arrives for more than 5 minutes. Possible causes:

| Cause | Fix |
|---|---|
| Upload interval set too long on the gateway | Set upload interval to 16–60 seconds |
| Gateway going offline (power, Wi-Fi dropouts) | Check gateway power and network |
| Mac IP address changed (DHCP) | Set a static/reserved IP for the Mac on your router |
| macOS sleeping and blocking the network | Disable sleep for the Indigo Mac, or set network access to stay active |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Wrong Units Displayed

**Symptom:** Temperature shows in °C when you expected °F (or vice versa).

Open **Plugins → Ecowitt Weather Station → Configure…** and confirm **Display Units** is set correctly. The change takes effect on the next push — no restart required.

If units look correct in preferences but states still show the wrong unit: check whether the state was populated before you changed the units setting. The value will update to the correct unit on the next push.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Plugin Won't Start / Python Dependency Error

**Symptom:** Indigo log shows an import error for `aioecowitt` or `aiohttp`.

Indigo installs Python packages from `requirements.txt` automatically. If this fails:

1. Confirm the Indigo Mac has an active internet connection
2. Open the Indigo log and look for pip install output near the plugin load time
3. Try disabling and re-enabling the plugin from the Plugins menu to trigger a fresh install attempt
4. Check that `requirements.txt` in the plugin bundle lists the correct package versions

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## WS90 Rain Data Showing Zero

The WS90 uses a piezoelectric gauge. Its rain readings are in the `*Piezo` states (`rainRatePiezo`, `dailyRainPiezo`, etc.) — **not** in `rainRate` or `dailyRain`. If you see zero in `rainRate`, check `rainRatePiezo`.

Also note that the WS90 is supercapacitor-powered. After an extended overcast period or overnight, the capacitor voltage may be low enough that readings are absent or zero until it recharges in sunlight.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Collecting Diagnostic Information

When filing a bug report, include:

1. **Indigo log excerpt** from around the time the problem occurred (with Debug Logging enabled if possible)
2. **Plugin version** (shown in Plugins menu)
3. **Gateway model** (visible in the `gatewayModel` state after first push)
4. **Sensor model(s)** causing the issue
5. **macOS version**
6. **What you expected vs what happened**

File issues at: https://github.com/Ghawken/EcowittWeather/issues
