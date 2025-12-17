"""Constants for the Ubiquiti mFi mPower integration."""

from __future__ import annotations

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)

DOMAIN = "mfi_mpower"

NAME = "Ubiquiti mFi mPower"

DEFAULT_TIMEOUT = 15

DEFAULTS = {
    CONF_HOST: None,
    CONF_USERNAME: "ubnt",
    CONF_PASSWORD: "ubnt",
    CONF_SSL: False,
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: 30,
}
