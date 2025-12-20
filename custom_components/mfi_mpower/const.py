"""Constants for the Ubiquiti mFi mPower integration."""

from __future__ import annotations

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)

DOMAIN = "mfi_mpower"

NAME = "Ubiquiti mFi mPower"

DEFAULT_TIMEOUT = 10

DEFAULTS = {
    CONF_HOST: None,
    CONF_USERNAME: "ubnt",
    CONF_PASSWORD: "ubnt",
    CONF_SCAN_INTERVAL: 30,
}
