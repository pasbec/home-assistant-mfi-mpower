"""Helper to test significant Ubiquiti mFi mPower state changes."""

from __future__ import annotations

from typing import Any

from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant, callback

SIGNIFICANT_CHANGE_THRESHOLDS = {
    "power": 1.0,  # Watt
    "current": 0.01,  # Ampere
    "voltage": 1.0,  # Volt
    "power_factor": 0.01,  # %
    "energy": 0.001,  # kWh
}


@callback
def async_check_significant_change(
    hass: HomeAssistant,
    old_state: str,
    old_attrs: dict,
    new_state: str,
    new_attrs: dict,
    **kwargs: Any,
) -> bool | None:
    """Test if state significantly changed."""
    device_class = new_attrs.get(ATTR_DEVICE_CLASS)
    if device_class is None:
        return None

    try:
        old_value = float(old_state)
        new_value = float(new_state)
    except (TypeError, ValueError):
        return None

    threshold = SIGNIFICANT_CHANGE_THRESHOLDS.get(device_class)
    if threshold is None:
        return None

    return abs(new_value - old_value) >= threshold
