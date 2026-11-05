# Zehnder Multicontroller

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

**Home Assistant integration for Zehnder Multicontroller using the Rainmaker API**

**This component will set up the following platforms.**

| Platform        | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `binary_sensor` | Read-only boolean sensors from your Zehnder devices.        |
| `climate`       | Climate control for temperature and HVAC mode management.   |
| `number`        | Number controls for writable numeric parameters.            |
| `sensor`        | Sensor entities for temperature, humidity and other values. |
| `switch`        | Switch controls for writable boolean parameters.            |

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "Zehnder Multicontroller" in HACS
3. Install the integration
4. Restart Home Assistant
5. Go to "Configuration" -> "Integrations" -> "+" and search for "Zehnder Multicontroller"

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `zehnder_multicontroller`.
4. Download _all_ the files from the `custom_components/zehnder_multicontroller/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Zehnder Multicontroller"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/zehnder_multicontroller/translations/en.json
custom_components/zehnder_multicontroller/__init__.py
custom_components/zehnder_multicontroller/api.py
custom_components/zehnder_multicontroller/binary_sensor.py
custom_components/zehnder_multicontroller/climate.py
custom_components/zehnder_multicontroller/config_flow.py
custom_components/zehnder_multicontroller/const.py
custom_components/zehnder_multicontroller/coordinator.py
custom_components/zehnder_multicontroller/manifest.json
custom_components/zehnder_multicontroller/number.py
custom_components/zehnder_multicontroller/sensor.py
custom_components/zehnder_multicontroller/switch.py
```

## Configuration

Configuration is done through the UI:

1. Go to "Configuration" -> "Integrations"
2. Click the "+" button
3. Search for "Zehnder Multicontroller"
4. Enter your Rainmaker API credentials:
   - **Host**: The Rainmaker API endpoint (default: https://api.rainmaker.espressif.com/v1/)
   - **Username**: Your Rainmaker username
   - **Password**: Your Rainmaker password

### Options

Click **Configure** on the integration to choose how climate devices are exposed:

- **Use climate entity** (default): setpoint, season (heat/cool), heating/cooling enable and
  fan speed are controlled through one `climate` entity. They are not also created as separate
  number/switch entities. The read-only temperature sensor is kept, because it records the
  temperature's long-term statistics.
- **Disabled**: no `climate` entity is created. Each of those values gets its own number or
  switch entity instead.

Changing the option reloads the integration and removes the entities the selected mode does
not use.

### Long-term statistics

Home Assistant keeps long-term statistics (hourly mean/min/max, stored indefinitely) only for
sensor entities with a state class. Controls such as `climate`, `number` and `switch` entities
never get them. To make heating programs analysable over a whole season, this integration
provides:

- A state class on all read-only numeric sensors (temperature, humidity, ...).
- A diagnostic **"... statistics"** sensor for every writable numeric value (e.g. setpoint,
  fan speed) and for every on/off value. On/off values are recorded as 0 or 100 %, so the
  hourly mean is the share of time the value was on (e.g. how much of each hour heating was
  enabled). `season` is left out because the average of a mode number isn't meaningful.

These sensors are created regardless of the climate option.

Detailed (non-statistics) history is deleted after 10 days by default. To keep it longer
while tuning your heating programs, raise the retention in `configuration.yaml`:

```yaml
recorder:
  purge_keep_days: 365
```

## Requirements

This integration uses the `rainmaker-http` Python package to communicate with the Rainmaker API.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/morphiumdeus
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/morphiumdeus/zehnder-multicontroller.svg?style=for-the-badge
[commits]: https://github.com/morphiumdeus/zehnder-multicontroller/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/morphiumdeus/zehnder-multicontroller.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40morphiumdeus-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/morphiumdeus/zehnder-multicontroller.svg?style=for-the-badge
[releases]: https://github.com/morphiumdeus/zehnder-multicontroller/releases
[user_profile]: https://github.com/morphiumdeus
