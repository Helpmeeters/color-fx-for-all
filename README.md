# Helpmeet: Color FX for All

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Helpmeet: Color FX for All** brings smooth, coordinated color sequence animations and holiday lighting effects to any Home Assistant light or light group—independent of hardware brand or proprietary vendor ecosystems (Philips Hue, Zigbee, Z-Wave, Matter, LIFX, etc.).

Inspired by the Circadian Lighting paradigm, each Color FX zone provides an intuitive On/Off helper switch, a sequence selector, and automatic state restoration when turned off.

---

## ✨ Features

- 🌈 **Multi-Sequence Library:** Built-in curated palettes including **Sunset**, **Halloween**, **Christmas**, **Ocean Waves**, **Cyberpunk**, **Campfire**, **Pastel Dream**, **Rainbow**, and **Patriotic**.
- 🎛️ **Helper Switch Per Zone:** Simple `switch.color_fx_<zone>` entity—turn it on to start the effect, turn it off to stop.
- 🔁 **Sequence Selector:** `select.color_fx_<zone>_sequence` lets you switch themes on the fly.
- 💾 **State Restoration:** Gracefully snapshots each bulb's brightness, color temperature, and on/off status before starting, and restores them when turned off.
- ⏱️ **Configurable Timing:** Adjustable step interval (hold time) and transition speed.
- 💡 **Light Group Native:** Expands light groups automatically and filters only color-capable bulbs so plain switches/dimmers aren't sent invalid color payloads.
- 🌓 **Circadian Lighting Friendly:** Easily added to Circadian Lighting's `disable_entity` list to prevent color fights while active.

---

## 🚀 Quick Setup

### Via UI (Config Flow)
1. In Home Assistant, go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Color FX**.
3. Choose a **Zone Name** (e.g. `Living Room`) and select your **Target Light / Light Group**.
4. Pick your default sequence and timing.

### Entities Created
For each zone configured:
- `switch.color_fx_<zone>` — Master toggle.
- `select.color_fx_<zone>_sequence` — Dropdown to change the active sequence.

---

## 🎮 Services

| Service | Description | Parameters |
|---|---|---|
| `color_fx.start` | Starts the animation loop | `entity_id`, optional `sequence` |
| `color_fx.stop` | Stops the loop and restores previous lighting | `entity_id` |
| `color_fx.next_sequence` | Cycles to the next sequence in the palette | `entity_id` |
| `color_fx.set_sequence` | Sets the active sequence | `entity_id`, `sequence` |

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

## 📄 License
MIT © 2026 Helpmeeters
