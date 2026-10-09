# Helpmeet: Color FX for All

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Helpmeet: Color FX for All** brings smooth, coordinated color sequence animations and holiday lighting effects to any Home Assistant light or light group—independent of hardware brand or proprietary vendor ecosystems (Philips Hue, Zigbee, Z-Wave, Matter, LIFX, etc.).

Inspired by the Circadian Lighting paradigm, each Color FX hub provides an intuitive On/Off helper switch, a sequence selector, and automatic state restoration when turned off.

<img src="https://raw.githubusercontent.com/Helpmeeters/color-fx-for-all/main/docs/images/card.png" alt="The Color FX dashboard card showing three Hubs: Den following Media Art from the Bedroom player, Kitchen off on Halloween, and Living Room on Sunset, each with its palette swatches" width="530">

---

## ✨ Features

- 🌈 **Multi-Sequence Library:** Built-in curated palettes including **Sunset**, **Halloween**, **Christmas**, **Ocean Waves**, **Cyberpunk**, **Campfire**, **Pastel Dream**, **Rainbow**, and **Patriotic**.
- 🎵 **Media Art:** A live sequence that cycles through the colors of the artwork on whichever media player most recently started playing something new: album art from a speaker, a show or movie poster from an Apple TV, and so on. Each hub can follow the media players you pick, or every player if you leave the list empty. It needs no automations and updates with each new album or title.
- 🎛️ **Helper Switch Per Hub:** Simple `switch.color_fx_<hub>` entity—turn it on to start the effect, turn it off to stop.
- 🔁 **Sequence Selector:** `select.color_fx_<hub>_sequence` lets you switch themes on the fly.
- 💾 **State Restoration:** Gracefully snapshots each bulb's brightness, color temperature, and on/off status before starting, and restores them when turned off.
- ⏱️ **Optional Rotation:** Cycle through a sequence with adjustable step interval (hold time) and transition speed, or turn rotation off to hold a single dominant color.
- 💡 **Light Group Native:** Expands light groups automatically and filters only color-capable bulbs so plain switches/dimmers aren't sent invalid color payloads.
- 🌓 **Circadian Lighting Friendly:** Easily added to Circadian Lighting's `disable_entity` list to prevent color fights while active.

---

## 📋 Requirements

- Home Assistant **2026.9** or newer.
- At least one light that supports color. Lights that only dim or change white temperature are left alone.

---

## 📦 Install

1. In HACS, add this repository as a custom repository (type: Integration) and install **Helpmeet: Color FX for All**.
2. Restart Home Assistant.
3. Go to **Settings** → **Devices & Services** → **Add Integration** → **Helpmeet: Color FX for All**.

To add more hubs later, open the integration's page and choose **Add Hub**.

---

## 🚀 Quick Setup

1. Choose a **Hub Name** (e.g. `Living Room`).
2. Optionally choose the **Media Art Players** this hub follows (music speakers, TVs, or anything else that shows artwork). Leave it empty to follow every media player.
3. Select one or more **Target Lights / Light Groups**.
4. Pick your default sequence, and whether to **Restore lighting on stop** (on by default).
5. Choose whether to **Rotate colors**. With rotation on, the **Color Rotation** section sets the step interval and transition speed. With it off, the lights hold the sequence's most dominant color (for Media Art, the artwork's most prominent color) and change only when the sequence or artwork does.

You can change any of these later under the hub's **Configure** options, including its name.

### Entities Created
Each hub appears as a device named after it, with:
- `switch.color_fx_<hub>` — Master toggle.
- `select.color_fx_<hub>_sequence` — Dropdown to change the active sequence.

The switch's `palette` attribute lists the current sequence's colors as hex codes. When Media Art is selected it follows the artwork live, even while the hub is off, and `palette_source` names the media player the colors came from.

Media Art only changes when the artwork does, so with video it shows one palette per title rather than following the picture scene by scene. Which apps publish artwork is up to each app; on Apple TV, Apple's own apps usually do, while some third-party apps send none.

### Dashboard Card
The integration loads a **Color FX** card on every dashboard; no resource setup is needed. Add it from the dashboard's card picker and choose a hub. It shows the hub with an on/off toggle, a sequence picker, and swatches of its live palette:
```yaml
type: custom:color-fx-card
entity: switch.color_fx_living_room
name: Living Room   # optional
```
Leave out `entity` to show every Color FX hub in one card.

---

## 🎮 Services

| Service | Description | Parameters |
|---|---|---|
| `color_fx.start` | Starts the animation loop | `entity_id`, optional `sequence` |
| `color_fx.stop` | Stops the loop and restores previous lighting | `entity_id` |
| `color_fx.next_sequence` | Cycles to the next sequence in the list | `entity_id` |
| `color_fx.set_sequence` | Sets the active sequence | `entity_id`, `sequence` |

`entity_id` can be a hub's switch, or a light the hub targets. Leave it out to act on every hub.

---

## 🛠️ Automations Example

Double-press a physical switch (like Inovelli or Zigbee button) to toggle the effect:
```yaml
automation:
  - alias: "Living Room · Switch · Toggle Color FX"
    trigger:
      - platform: device
        domain: zha
        type: remote_button_double_press
        subtype: Config
    action:
      - action: switch.toggle
        target:
          entity_id: switch.color_fx_living_room
```

Cycle to the next theme on triple-press:
```yaml
automation:
  - alias: "Living Room · Switch · Next Color FX Theme"
    trigger:
      - platform: device
        domain: zha
        type: remote_button_triple_press
        subtype: Config
    action:
      - action: color_fx.next_sequence
        target:
          entity_id: switch.color_fx_living_room
```

---

## 🐞 Debug Logging

Turn on **Enable debug logging** on the integration's page (it lasts until you turn it off or restart), or add this to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.color_fx: debug
```

The log then shows each hub starting and stopping, sequence changes, and every palette Media Art extracts along with the player it came from.

---

## 🗑️ Uninstall

Delete the hubs from **Devices & Services** (a running hub stops and restores its lights first), then uninstall the integration in HACS. Restart Home Assistant to stop the dashboard card from loading, and remove any Color FX cards from your dashboards.

---

## 🤝 Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and what to include in a bug report, and [SECURITY.md](SECURITY.md) for reporting vulnerabilities privately.

---

## 🤖 Written with AI Assistance

Much of this integration's code, tests, and documentation was written with the help of AI coding assistants, then reviewed, tested, and directed by a human maintainer. Its behavior is covered by tests that run against both Home Assistant stable and beta. If something looks wrong, please [open an issue](https://github.com/Helpmeeters/color-fx-for-all/issues).

---

## 📄 License

[MIT](LICENSE). Color FX for All is part of Helpmeet, a family of Home Assistant integrations.
