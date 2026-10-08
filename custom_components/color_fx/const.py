"""Constants for the Color FX for All integration."""

DOMAIN = "color_fx"
DEFAULT_NAME = "Color FX"

CONF_ZONES = "zones"
CONF_TARGET_LIGHT = "target_light"
CONF_SEQUENCE = "sequence"
CONF_TRANSITION = "transition"
CONF_INTERVAL = "interval"
CONF_BRIGHTNESS = "brightness"
CONF_RESTORE_STATE = "restore_state"
CONF_CUSTOM_SEQUENCES = "custom_sequences"

DEFAULT_SEQUENCE = "Sunset"
DEFAULT_TRANSITION = 2.0
DEFAULT_INTERVAL = 4.0
DEFAULT_RESTORE_STATE = True

SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_NEXT_SEQUENCE = "next_sequence"
SERVICE_SET_SEQUENCE = "set_sequence"

ATTR_CURRENT_SEQUENCE = "current_sequence"
ATTR_TARGET_LIGHT = "target_light"
ATTR_AVAILABLE_SEQUENCES = "available_sequences"
ATTR_ACTIVE_BULBS = "active_bulbs"

BUILTIN_SEQUENCES: dict[str, list[list[int]]] = {
    "Sunset": [
        [255, 75, 45],   # Deep Coral
        [255, 160, 20],  # Golden Amber
        [180, 50, 180],  # Twilight Violet
        [70, 50, 160],   # Dusk Indigo
    ],
    "Halloween": [
        [255, 90, 0],    # Pumpkin Orange
        [138, 43, 226],  # Witch Purple
        [0, 255, 50],    # Slime Green
        [220, 20, 60],   # Blood Crimson
    ],
    "Christmas": [
        [255, 15, 15],   # Holly Red
        [10, 180, 40],   # Pine Green
        [255, 200, 50],  # Warm Gold
        [255, 245, 245], # Snow White
    ],
    "Ocean Waves": [
        [0, 60, 190],    # Deep Ocean Blue
        [0, 190, 210],   # Turquoise
        [40, 230, 180],  # Bright Aqua
        [140, 250, 215], # Seafoam
    ],
    "Cyberpunk": [
        [255, 20, 147],  # Neon Pink
        [0, 245, 255],   # Electric Cyan
        [140, 20, 255],  # Ultra Violet
        [255, 230, 0],   # Cyber Yellow
    ],
    "Campfire": [
        [255, 80, 0],    # Fire Orange
        [255, 140, 15],  # Warm Flame
        [200, 30, 0],    # Deep Ember
        [255, 180, 40],  # Candle Glow
    ],
    "Pastel Dream": [
        [127, 172, 255], # Soft Sky Blue
        [215, 150, 255], # Lavender
        [255, 158, 243], # Cotton Candy Pink
        [255, 185, 140], # Soft Peach
    ],
    "Rainbow": [
        [255, 0, 0],     # Red
        [255, 127, 0],   # Orange
        [255, 255, 0],   # Yellow
        [0, 255, 0],     # Green
        [0, 255, 255],   # Cyan
        [0, 0, 255],     # Blue
        [148, 0, 211],   # Violet
    ],
    "Patriotic": [
        [255, 0, 0],     # Red
        [255, 255, 255], # White
        [0, 30, 255],    # Blue
    ],
}
