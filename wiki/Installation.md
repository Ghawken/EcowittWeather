![Ecowitt Weather Station — Indigo Plugin](https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/banner.png)

# Installation

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Requirements

| Requirement | Minimum version |
|---|---|
| Indigo Domotics | 2025.2 (API 3.4+) |
| macOS | whatever Indigo 2025.2 requires |
| aioecowitt | ≥ 2025.9.2 (auto-installed) |

Your Indigo Mac and the Ecowitt gateway must be on the same LAN, or the gateway must be able to reach the Mac's IP on the configured listen port.

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Install Steps

### 1. Download the plugin

Go to the [Releases](https://github.com/Ghawken/EcowittWeather/releases) page and download the latest `.indigoPlugin` file.

### 2. Install

Double-click the `.indigoPlugin` file. Indigo will open and prompt you to install it. Click **Install and Enable**.

Indigo automatically installs Python dependencies listed in `requirements.txt` (aioecowitt and aiohttp). This requires an internet connection on first install and may take 30–60 seconds.

### 3. Allow incoming connections

macOS Firewall may block the plugin's HTTP server port on first use.

- **System Settings → Network → Firewall → Options…**
- Add Indigo (or allow it when macOS prompts)
- Alternatively, confirm the port is not blocked with: `sudo pfctl -sr | grep 45000`

### 4. Configure the plugin

Open **Plugins → Ecowitt Weather Station → Configure…** and set the port and units. See [Plugin Configuration](Plugin-Configuration) for details.

### 5. Configure your gateway

Tell your Ecowitt gateway to push data to your Mac's IP address, port, and path. See [Ecowitt Gateway Setup](Ecowitt-Gateway-Setup).

### 6. Create a Hub device

In Indigo, create a new device of type **Ecowitt Gateway Hub**. See [Device Setup](Device-Setup).

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## First Launch Checklist

- [ ] Plugin installed and enabled in Indigo
- [ ] Python dependencies installed (no error in Indigo log on startup)
- [ ] Firewall allows inbound connections on port 45000 (or your chosen port)
- [ ] Plugin configured with correct port and units
- [ ] Gateway configured with correct server IP, path, and port
- [ ] At least one Ecowitt Gateway Hub device created in Indigo
- [ ] First data push received — states appear in the Hub device

<img src="https://raw.githubusercontent.com/Ghawken/EcowittWeather/main/Images/weather_divider_top_animated.gif" width="100%"/>

## Updating the Plugin

Download the new `.indigoPlugin` from the Releases page and double-click it. Indigo will update the plugin in place. All device states and configuration are preserved.

If aioecowitt has been updated (check `requirements.txt`), Indigo will automatically install the new version on next restart.

## Uninstalling

**Plugins → Ecowitt Weather Station → Remove Plugin…**

This removes the plugin and its Python packages. Indigo device configurations and states are removed along with any Hub devices you delete manually.
