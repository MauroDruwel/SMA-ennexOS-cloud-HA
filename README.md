<h1 align="center">SMA ennexOS Cloud for Home Assistant</h1>
<p align="center"><b>Your PV production data, directly in Home Assistant.</b></p>

<p align="center">
  <a href="#quick-install">Quick Install</a> |
  <a href="#how-it-works">How it Works</a> |
  <a href="#sensors">Sensors</a> |
  <a href="#issues">Issues</a>
</p>

<p align="center">
  <img alt="PyPI" src="https://img.shields.io/pypi/v/sma_ennexos_cloud"/>
  <img alt="License" src="https://img.shields.io/github/license/MauroDruwel/SMA-ennexOS-cloud-HA"/>
</p>

---

> **Your SMA Sunny Portal / ennexOS PV data, right where it belongs, in Home Assistant.**

---

## Requirements

- **Home Assistant 2024.8+**
- An **SMA ID** account (username + password) for [Sunny Portal](https://ennexos.sunnyportal.com/)
- The [`sma_ennexos_cloud`](https://pypi.org/project/sma_ennexos_cloud/) Python package (installed automatically)

No Docker add-on required. No headless browser. Just pure HTTP + PKCE OAuth2.

---

## Quick Install

### Via HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MauroDruwel&repository=SMA-ennexOS-cloud-HA)

<details>
<summary>Or manually...</summary>

1. Open HACS -> **Integrations** -> **...** -> **Custom repositories**
2. Add: `https://github.com/MauroDruwel/SMA-ennexOS-cloud-HA`
3. Search "SMA ennexOS Cloud" -> **Download**

</details>

### Manual Installation

```sh
cd /config/custom_components
git clone https://github.com/MauroDruwel/SMA-ennexOS-cloud-HA.git sma_ennexos_cloud
```

### Then...

1. Restart Home Assistant
2. **Settings** -> **Devices & Services** -> **Add Integration** -> "SMA ennexOS Cloud"
3. Enter your SMA ID username and password
4. Done!

---

## How it Works

```
+-----------------+     sma_ennexos_cloud lib     +------------------+
|  Home Assistant | <---------(PKCE OAuth2)------> |  Sunny Portal   |
|   Integration   |                                 |     API         |
+-----------------+                                  +------------------+
```

1. The integration authenticates via the same PKCE OAuth2 flow the Sunny Portal web app uses
2. It calls the JSON APIs to fetch live power, daily energy, and plant info
3. All data is transformed into Home Assistant sensors automatically

No browser, no scraping, no Docker add-on. Just the `sma_ennexos_cloud` Python library talking directly to the SMA API.

---

## Sensors

Once configured, you'll get these sensors:

| Sensor | Unit | Description |
|--------|------|-------------|
| Current Power | W | Live PV production (polled every 5s) |
| Daily Energy | Wh | Total energy produced today |
| Plant Name | — | Your installation's name |
| Last Sync | — | Timestamp of last data fetch |

---

## Issues

Something broken? [Open an issue](https://github.com/MauroDruwel/SMA-ennexOS-cloud-HA/issues) and let's fix it.

## Contributing

PRs are welcome! Let's make this thing even better.

---

*Made with love and a lot of trial and error.*
