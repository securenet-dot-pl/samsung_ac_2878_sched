"""On-device schedule control for climate_ip (Samsung AC, port 2878 / DPLUG).

The stock climate_ip integration maps power/mode/temp/fan but has NO schedule
operations. The AC's Wi-Fi module stores on/off schedules on its own clock and
runs them even offline. This module adds read/create/edit/delete of those
schedules, reusing the reference protocol implementation from `pysamsung-dplug`
(handles the UTC conversion + day-mask rotation correctly).

Used by climate.py, which registers the HA services:
  climate_ip.get_schedules / set_schedule / delete_schedule
"""
from __future__ import annotations

import logging
import os
import ssl
from datetime import timezone

_LOGGER = logging.getLogger(__package__)

# Python weekday() order: Mon=0 .. Sun=6
_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _resolve_cert(cert):
    """Resolve a cert filename relative to this integration dir (like samsung_2878.py)."""
    if not cert:
        return None
    if cert.find("\\") == -1 and cert.find("/") == -1:
        return os.path.join(os.path.dirname(__file__), cert)
    return cert


def make_context(cert=None):
    """Build an SSL context for the old AC14K TLS socket (TLS1.0 + SECLEVEL 0 + client cert).

    SYNC / does file I/O (load_cert_chain) -> call from executor, not the event loop.
    """
    cp = _resolve_cert(cert)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except Exception:  # pragma: no cover
        pass
    ctx.set_ciphers("ALL:@SECLEVEL=0")
    if cp:
        ctx.load_cert_chain(cp)
    return ctx


def _tz(tzname):
    if not tzname:
        return timezone.utc
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(tzname)
    except Exception:
        return timezone.utc


def _client(host, token, ssl_context, duid):
    from samsung_dplug import SamsungAcClient

    return SamsungAcClient(host=host, token=token, ssl_context=ssl_context, duid=duid)


def _days_to_py(days):
    """Accept list of day names ('mon'..) and/or ints (0..6); return list[int]."""
    out = []
    for d in days or []:
        if isinstance(d, int):
            out.append(d)
        else:
            s = str(d).strip().lower()[:3]
            if s in _DAY_NAMES:
                out.append(_DAY_NAMES.index(s))
    return out


async def get_schedules(host, token, ssl_context, duid, tzname):
    """Return the schedules stored in the AC as a list of plain dicts."""
    from samsung_dplug import mask_to_weekdays

    c = _client(host, token, ssl_context, duid)
    scheds = await c.async_get_schedules(tz=_tz(tzname))
    out = []
    for s in scheds or []:
        day_ints = sorted(mask_to_weekdays(s.days)) if s.days else []
        out.append(
            {
                "schedule_id": s.schedule_id,
                "time": "%02d:%02d" % (s.hour, s.minute),
                "repeat": s.repeat,
                "days": [_DAY_NAMES[i] for i in day_ints],
                "enabled": s.enabled,
                "action": (s.attrs or {}).get("AC_FUN_POWER"),
                "attrs": s.attrs,
            }
        )
    return out


async def set_schedule(
    host, token, ssl_context, duid, tzname,
    time_str, action, repeat="once", days=None, schedule_id="", enabled=True,
):
    """Create (schedule_id empty) or edit (schedule_id set) a power on/off schedule."""
    from samsung_dplug import Schedule, weekdays_to_mask, ONCE, EVERYDAY_TYPE, EVERYWEEK

    rep_map = {"once": ONCE, "everyday": EVERYDAY_TYPE, "everyweek": EVERYWEEK}
    rep = rep_map.get(str(repeat).strip().lower(), ONCE)

    hh, mm = str(time_str).split(":")[:2]
    power = "On" if str(action).strip().lower() in ("on", "power_on", "true", "1") else "Off"
    mask = weekdays_to_mask(_days_to_py(days)) if days else 0

    sched = Schedule(
        schedule_id=schedule_id or "",
        hour=int(hh),
        minute=int(mm),
        repeat=rep,
        days=mask,
        enabled=bool(enabled),
        attrs={"AC_FUN_POWER": power},
    )
    c = _client(host, token, ssl_context, duid)
    await c.async_set_schedule(sched, tz=_tz(tzname))


async def delete_schedule(host, token, ssl_context, duid, schedule_id):
    c = _client(host, token, ssl_context, duid)
    await c.async_delete_schedule(str(schedule_id))
