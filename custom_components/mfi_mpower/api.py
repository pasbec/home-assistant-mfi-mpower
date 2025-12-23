"""Namespace wrapper for the API (mfi_mpower) of the Ubiquiti mFi mPower integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

# pylint: disable=unused-import
import asyncssh
from mfi_mpower.device import MPowerDevice
from mfi_mpower.entities import MPowerEntity, MPowerSensor, MPowerSwitch
from mfi_mpower.exceptions import MPowerDataError
from mfi_mpower.interface import MPowerLED, MPowerNetwork
from mfi_mpower.session import (
    MPowerAuthenticationError,
    MPowerCommandError,
    MPowerConnectionError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from .const import DEFAULTS, NAME
from .update_coordinator import MPowerDataUpdateCoordinator

# pylint: enable=unused-import

_LOGGER = logging.getLogger(__name__)


def create_title(host: str) -> str:
    """Construct title from host."""
    return f"{NAME} [{host}]"


def create_data(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> dict:
    """Construct API data to create MPowerDevice instances from hass and config data."""
    assert all(
        [
            MPowerLED,
            MPowerNetwork,
            MPowerDevice,
            MPowerEntity,
            MPowerSensor,
            MPowerSwitch,
            MPowerConnectionError,
            MPowerAuthenticationError,
            MPowerCommandError,
            MPowerDataError,
        ]
    )

    return {
        "host": data.get(CONF_HOST, DEFAULTS[CONF_HOST]),
        "username": data.get(CONF_USERNAME, DEFAULTS[CONF_USERNAME]),
        "password": data.get(CONF_PASSWORD, DEFAULTS[CONF_PASSWORD]),
    }


async def create_device(hass: HomeAssistant, data: dict[str, Any]) -> MPowerDevice:
    """Construct a new MPowerDevice instance from hass and config data."""
    return MPowerDevice(**create_data(hass, data))


async def create_device_for_flow(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[MPowerDevice | None, str | None]:
    """Validate the config data ."""

    try:
        api_device = await create_device(hass, data)
    except Exception as exc:  # pylint: disable=broad-except
        _LOGGER.debug("Device creation failed: %s", exc)
        return None, "input_error"

    _LOGGER.debug(
        "Device creation OK: %s, %s, %s",
        api_device.hostname,
        api_device.mac,
        api_device.data,
    )

    try:
        await api_device.interface.connect()
    except MPowerConnectionError as exc:
        _LOGGER.debug("Connection failed: %s", exc)
        return None, "cannot_connect"
    except MPowerAuthenticationError as exc:
        _LOGGER.debug("Authentication failed: %s", exc)
        return None, "invalid_auth"
    except Exception as exc:  # pylint: disable=broad-except
        _LOGGER.exception("Unhandled exception occurred: %s", exc)
        return None, "unknown"

    _LOGGER.debug(
        "Device connection OK: %s, %s, %s",
        api_device.hostname,
        api_device.mac,
        api_device.data,
    )

    return api_device, "debug"


async def update_device(api_device: MPowerDevice) -> None:
    """Update a MPowerDevice instance."""
    async with UpdateHandler() as handler:
        while True:
            try:
                await api_device.refresh()
                break
            except Exception as exc:  # pylint: disable=broad-except
                handler.handle(exc)


async def create_coordinator(
    hass: HomeAssistant, data: dict[str, Any], config_entry: ConfigEntry | None = None
) -> MPowerDataUpdateCoordinator:
    """Construct coordinator instance from hass and config data."""
    # Setup asyncssh logger
    setup_asyncssh_logger()

    # Create and update API device
    api_device = await create_device(hass, data)
    try:
        await update_device(api_device)
    except Exception:  # pylint: disable=broad-except
        pass  # The coordinator will take over on failure...

    # Create coordinator
    coordinator = MPowerDataUpdateCoordinator(
        hass=hass,
        api_device=api_device,
        scan_interval=data.get(CONF_SCAN_INTERVAL, DEFAULTS[CONF_SCAN_INTERVAL]),
        config_entry=config_entry,
    )

    # Let the coordinator take over if the device was not refreshed yet
    if not api_device.has_data:
        await coordinator.async_config_entry_first_refresh()

    return coordinator


def setup_asyncssh_logger():
    """Setup logger for asyncssh."""
    asyncssh_logger = logging.getLogger(asyncssh.__name__)
    asyncssh_logger.setLevel(_LOGGER.level)
    asyncssh_logger.filters = [
        f for f in asyncssh_logger.filters if not isinstance(f, SilenceInfoFilter)
    ]
    asyncssh_logger.addFilter(SilenceInfoFilter())


class SilenceInfoFilter(logging.Filter):
    """Logging filter to silence info messages."""

    def filter(self, record):
        logger = logging.getLogger(record.name)
        # Suppress INFO and lower if logger is NOTSET
        if logger.level == logging.NOTSET:
            if record.levelno <= logging.INFO:
                return False
        # Downgrade INFO to DEBUG
        if record.levelno == logging.INFO:
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return True


class UpdateHandler:
    """
    Update handler.

    This class handles a possible SSH BrokenPipeError bug - which may occur if the
    debug mode of the event loop is enabled - by means of disabling it temporarily.
    """

    lock: asyncio.Lock = asyncio.Lock()
    counter: int = 0

    def __init__(self) -> None:
        """Initialize handler."""
        self._loop = asyncio.get_running_loop()
        self._debug = self._loop.get_debug()

    async def __aenter__(self) -> UpdateHandler:
        """Enter handler context manager scope."""
        type(self).counter += 1

        return self

    async def __aexit__(self, *kwargs) -> None:
        """Leave handler context manager scope."""
        type(self).counter -= 1

        if not type(self).counter:
            if self._loop.get_debug() != self._debug:
                self._loop.set_debug(self._debug)
                _LOGGER.warning("The debug mode of the event loop has been re-enabled")

    def __bool__(self):
        """Check if no handler context manager scope is used."""
        return not type(self).counter

    def handle(self, exc):
        """Handle update exception."""
        if isinstance(exc, MPowerConnectionError):
            if isinstance(exc.__context__, BrokenPipeError):
                if self._loop.get_debug():
                    _LOGGER.warning(
                        "%s %s",
                        "MPowerConnectionError was raised from BrokenPipeError with enabled event loop debug mode.",
                        "The debug mode of the event loop will temporarily be disabled",
                    )
                    self._loop.set_debug(False)
                    return

        raise exc
