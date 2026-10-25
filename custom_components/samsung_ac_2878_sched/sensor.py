"""Schedules sensor for the Samsung AC (port 2878 / DPLUG).

Auto-loaded from climate.py via discovery (no separate `sensor:` platform block
needed). Exposes the on-device on/off schedules as a native entity:

  state      = number of schedules stored on the AC module
  attribute  'schedules' = full list (id, time, action, repeat, days, enabled)

Polled on its own (slow) interval so it stays fresh without any user automation.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity

from . import schedule_ctl

_LOGGER = logging.getLogger(__package__)

# Slow poll on purpose: the old AC14K module dislikes frequent/concurrent
# connections, and schedules rarely change. 5 minutes is plenty.
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Only set up when auto-loaded by the climate platform (discovery_info present).
    if discovery_info is None:
        return
    mac = discovery_info.get("mac")
    duid = mac.replace(":", "").upper() if mac else None
    async_add_entities(
        [
            SamsungAcSchedulesSensor(
                base_name=discovery_info.get("base_name") or "samsungrac",
                host=discovery_info.get("ip_address"),
                token=discovery_info.get("token"),
                cert=discovery_info.get("cert"),
                duid=duid,
            )
        ],
        True,
    )


class SamsungAcSchedulesSensor(SensorEntity):
    """Number of on-device schedules + the full list as an attribute."""

    _attr_icon = "mdi:calendar-clock"
    _attr_should_poll = True

    def __init__(self, base_name, host, token, cert, duid):
        self._attr_name = f"climate_ip_{base_name} schedules"
        self._attr_unique_id = f"{duid}_schedules" if duid else f"{base_name}_schedules"
        self._host = host
        self._token = token
        self._cert = cert
        self._duid = duid
        self._attr_native_value = None
        self._schedules: list = []

    @property
    def extra_state_attributes(self):
        return {"schedules": self._schedules}

    async def async_update(self):
        try:
            ctx = await self.hass.async_add_executor_job(
                schedule_ctl.make_context, self._cert
            )
            self._schedules = await schedule_ctl.get_schedules(
                self._host, self._token, ctx, self._duid, self.hass.config.time_zone
            )
            self._attr_native_value = len(self._schedules)
            self._attr_available = True
        except Exception as e:  # keep last known list; just mark unavailable this cycle
            _LOGGER.warning("schedules sensor update failed: %s", e)
            self._attr_available = False
