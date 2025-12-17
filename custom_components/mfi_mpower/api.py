"""Namespace wrapper for the API (mfi_mpower) of the Ubiquiti mFi mPower integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncssh

# pylint: disable=unused-import
from mfi_mpower.device import MPowerDevice
from mfi_mpower.entities import MPowerEntity, MPowerSensor, MPowerSwitch
from mfi_mpower.exceptions import (
    MPowerAPIAuthError,
    MPowerAPIConnError,
    MPowerAPIDataError,
    MPowerAPIReadError,
    MPowerSSHConnError,
)

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DEFAULTS
from .update_coordinator import MPowerDataUpdateCoordinator

# pylint: enable=unused-import


_LOGGER = logging.getLogger(__name__)

# Reduce verbosity level from asyncssh
if _LOGGER.level in (logging.NOTSET, logging.INFO):
    asyncssh.logging.set_log_level(logging.WARNING)


def create_data(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> dict:
    """Construct API data to create MPowerDevice instances from hass and config data."""
    assert all(
        [
            MPowerDevice,
            MPowerEntity,
            MPowerSensor,
            MPowerSwitch,
            MPowerAPIConnError,
            MPowerAPIAuthError,
            MPowerAPIReadError,
            MPowerAPIDataError,
        ]
    )
    session = async_create_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])

    return {
        "host": data.get(CONF_HOST, DEFAULTS[CONF_HOST]),
        "username": data.get(CONF_USERNAME, DEFAULTS[CONF_USERNAME]),
        "password": data.get(CONF_PASSWORD, DEFAULTS[CONF_PASSWORD]),
        "use_ssl": data.get(CONF_SSL, DEFAULTS[CONF_SSL]),
        "verify_ssl": data.get(CONF_VERIFY_SSL, DEFAULTS[CONF_VERIFY_SSL]),
        "cache_time": 0,
        "board_info": True,
        "session": session,
    }


async def create_device(hass: HomeAssistant, data: dict[str, Any]) -> MPowerDevice:
    """Construct a new MPowerDevice instance from hass and config data."""
    return MPowerDevice(**create_data(hass, data))


async def update_device(api_device: MPowerDevice) -> None:
    """Update a MPowerDevice instance."""
    async with UpdateHandler() as handler:
        while True:
            try:
                await api_device.update()
                break
            except Exception as exc:  # pylint: disable=broad-except
                handler.handle(exc)


async def create_coordinator(
    hass: HomeAssistant, data: dict[str, Any]
) -> MPowerDataUpdateCoordinator:
    """Construct coordinator instance from hass and config data."""

    api_device = await create_device(hass, data)
    try:
        await update_device(api_device)
    except Exception:  # pylint: disable=broad-except
        pass  # The coordinator will take over on failure...

    coordinator = MPowerDataUpdateCoordinator(
        hass, api_device, data[CONF_SCAN_INTERVAL]
    )

    if not api_device.updated:
        await coordinator.async_config_entry_first_refresh()

    return coordinator


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
        if isinstance(exc, MPowerSSHConnError):
            if isinstance(exc.__context__, BrokenPipeError):
                if self._loop.get_debug():
                    _LOGGER.warning(
                        "%s %s",
                        "MPowerSSHConnError was raised from BrokenPipeError with enabled event loop debug mode.",
                        "The debug mode of the event loop will temporarily be disabled",
                    )
                    self._loop.set_debug(False)
                    return

        raise exc
