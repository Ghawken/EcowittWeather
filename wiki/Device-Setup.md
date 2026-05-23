![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Device Setup

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## The Ecowitt Gateway Hub Device

Each physical Ecowitt gateway is represented in Indigo as a single **Ecowitt Gateway Hub** device. This one device holds every state from every sensor attached to that gateway — outdoor weather, indoor sensors, soil probes, air quality, lightning, batteries, and more.

States are not declared in advance. A brand-new Hub device starts with only `connectionStatus`. Every other state appears automatically the first time data arrives from the gateway.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Creating a Hub Device

1. In Indigo, open **Devices** and click **New Device…**
2. Select **Type: Ecowitt Weather Station**
3. Select **Model: Ecowitt Gateway Hub**
4. Click **Next** / **Define Device Properties…**
5. In the **PASSKEY** field, enter your gateway's PASSKEY (see [Finding Your PASSKEY](Ecowitt-Gateway-Setup#finding-your-passkey)) — or leave blank to accept any gateway
6. Click **Save**

The device will show `connectionStatus: Never` until the first push arrives. After that it changes to **Connected** and all sensor states populate.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## PASSKEY Configuration

### What the PASSKEY does

Every Ecowitt gateway embeds a unique 32-character hexadecimal PASSKEY in every POST it sends. The plugin uses this PASSKEY to route incoming data to the correct Hub device when you have more than one gateway.

### Leave blank — single gateway (simplest setup)

If you have one gateway and one Hub device, leave the PASSKEY field blank. The plugin accepts data from any gateway and routes it to the first Hub device it finds.

### Set the PASSKEY — multiple gateways or strict routing

Set the PASSKEY on each Hub device to its corresponding gateway's PASSKEY. The plugin then routes each push exclusively to the device with the matching PASSKEY.

```
Gateway A (PASSKEY: 1054F475...)  →  Hub device "Weather Station — Backyard"
Gateway B (PASSKEY: AB92C3D4...)  →  Hub device "Weather Station — Roof"
```

### Routing rules (in priority order)

1. If the incoming PASSKEY exactly matches a Hub device's PASSKEY → route to that device
2. If no match and a Hub device has a blank PASSKEY → route to that device
3. If no device matches → log a warning and discard the push

This means you can mix configured and open devices: a device with a PASSKEY handles its specific gateway, a device with a blank PASSKEY acts as a catch-all for anything else.

### Finding your PASSKEY

See [Ecowitt Gateway Setup → Finding Your PASSKEY](Ecowitt-Gateway-Setup#finding-your-passkey) for the full procedure. The short version:

1. Enable **Debug Logging** in the plugin preferences
2. Wait for a push
3. Look in the Indigo log for: `Raw push received — ... PASSKEY='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'`
4. Copy the 32-character value into the Hub device's PASSKEY field

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Multiple Gateways

To receive data from multiple Ecowitt gateways simultaneously:

1. Create one Hub device per gateway
2. Set the PASSKEY on each device to its gateway's PASSKEY
3. All gateways share the same listen port and path — no additional configuration is needed in the plugin

Each Hub device maintains its own state set independently. States for Gateway A never affect Gateway B's device.

**Example setup:**

| Hub device name | PASSKEY | Gateway |
|---|---|---|
| Outdoor Station | `1054F475A49C8247A94571A1F3841D3E` | GW3000 in garden |
| Roof Station | `AB92C3D41E5F6789ABCD1234EFAB5678` | GW2000 on roof |
| Indoor Sensors | *(blank)* | GW1200 indoors |

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Dynamic States — When They Appear

States are created on-demand as sensor data arrives. Here is the lifecycle:

| Stage | What happens |
|---|---|
| Device created | Only `connectionStatus` exists (from Devices.xml) |
| First push received | `connectionStatus`, `lastUpdate`, `gatewayModel`, `stationType` appear |
| First sensor push | All sensor states appear for this push's readings |
| New sensor added to gateway | New states appear on the first push that includes that sensor |
| Plugin restarted | All previously seen states are restored from Indigo's stored device state |

### States that are always present

These are registered on the first push regardless of sensor type:

| State | Value | Notes |
|---|---|---|
| `connectionStatus` | Connected / Stale / Never | Declared in Devices.xml; shown in device list |
| `lastUpdate` | ISO 8601 timestamp | Updated on every push |
| `gatewayModel` | e.g. `GW3000C_V1.2.0` | Auto-populated from gateway |
| `stationType` | e.g. `GW3000C_V1.2.0` | Same as gateway firmware version string |

### What if a sensor is removed?

If you remove a physical sensor from the gateway, its Indigo states are **not deleted**. They remain in the Hub device but stop updating. The values shown are the last readings received.

If this bothers you, delete the Hub device and recreate it — states will be rebuilt fresh from the next push.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Using States in Indigo

Once data is flowing, all Hub device states are available anywhere Indigo lets you reference a device state:

- **Triggers** — fire when `outdoorTemp` drops below a threshold, or when `connectionStatus` changes to Stale
- **Conditions** — check `rainRate > 0` before turning on irrigation
- **Schedules** — log or act on weather readings on a timed basis
- **Control pages** — display live weather readings
- **Scripts / Python** — `indigo.devices["My Station"].states["outdoorTemp"]`

### Stale detection

If no push arrives for more than **5 minutes**, `connectionStatus` changes to `Stale`. This is useful for triggers that alert you when the weather station goes offline. See [Code Architecture — Stale Detection](Code-Architecture#stale-detection) for implementation details.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Device Display in Indigo

The Hub device shows `connectionStatus` as its primary display state in the Indigo device list. This gives at-a-glance status (Connected / Stale / Never) without opening the device detail.

All other states are visible in the device's state inspector and are available for triggers and scripts.
