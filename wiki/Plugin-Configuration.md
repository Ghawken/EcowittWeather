![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Plugin Configuration

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

Open **Plugins → Ecowitt Weather Station → Configure…** to access the plugin preferences.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Settings Reference

### Listen Port

**Default:** `45000`

The TCP port the plugin's built-in HTTP server listens on. Your Ecowitt gateway will POST to this port.

- Must be between 1024 and 65535
- Must not be in use by another application
- Gateways cannot use ports 80 or 443 for custom servers, so avoid those
- The same port is shared by all gateways — you do not need separate ports for multiple gateways

**Firewall:** macOS may prompt you to allow incoming connections when the plugin first starts. If it doesn't, check **System Settings → Network → Firewall** and confirm Indigo is allowed. You can test with:
```bash
sudo lsof -nP -iTCP:45000 -sTCP:LISTEN
```
If nothing appears, the server is not running. Check the Indigo log for startup errors.

---

### Listen Path

**Default:** `/data/report`

The HTTP URL path the gateway should POST to. This must match what is configured in your gateway's Customized upload settings exactly (the plugin normalises trailing slashes, so `/data/report/` and `/data/report` both work).

- Must start with `/`
- The default `/data/report` matches the default path used by most Ecowitt gateways out-of-the-box
- If you change this, update the **Path** field in your gateway settings to match

---

### Display Units

**Default:** Imperial (°F, mph, inHg, in)

| Option | Temperature | Speed | Pressure | Rain / distance |
|---|---|---|---|---|
| **Imperial** | °F | mph | inHg | inches / miles |
| **Metric** | °C | km/h | hPa | mm / km |

The `aioecowitt` library automatically computes both imperial and metric variants for most measurements (e.g. temperature arrives as both `tempf` and `tempc`). This setting controls which value wins when both are present.

**How unit priority works:**
- Each incoming sensor key is classified as Imperial, Metric, or unit-neutral
- The preferred unit variant gets priority 0; the alternate variant gets priority 1
- Within a single push, if the preferred variant arrives, it wins its Indigo state slot
- If only one variant arrives (some derived values), it takes the slot unconditionally

Changing this setting takes effect on the next push — no restart required.

---

### Enable Debug Logging

**Default:** Off

When enabled, the plugin logs every incoming push and every individual sensor value update to the Indigo log. This produces a large volume of output during normal operation and is intended for initial setup and troubleshooting only.

Debug entries include:
- Full raw push data (all fields and values)
- Each sensor key being mapped to an Indigo state
- State writes with key, value, and device name
- Dynamic state registration events

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Changing Port or Path After Initial Setup

If you change the **Listen Port** or **Listen Path**, the plugin automatically stops the HTTP server and restarts it on the new address. No plugin reload is required. You will see a log entry:

```
Listen address changed → restarting server on port 45001 at /data/report
Ecowitt server restarted on port 45001 at /data/report
```

Remember to update the gateway's Customized upload settings to match the new port or path, otherwise the gateway will keep sending to the old address and data will stop flowing.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Changing Units

Changing the units setting takes effect immediately on the next push. Existing state values are not retroactively converted — they will update to the new unit on the next data push.

If you switch from Imperial to Metric, you may notice that state values change scale (e.g. `windSpeed` jumps from mph to km/h). Any Indigo triggers comparing values to numeric thresholds will need to be updated to use metric values.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Validation

The plugin validates both the port and path when you click OK:

| Field | Validation rule |
|---|---|
| Listen Port | Must be an integer between 1024 and 65535 |
| Listen Path | Must start with `/` |

Errors are shown inline in the preferences dialog.
