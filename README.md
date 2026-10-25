# Samsung AC 2878 — schedule fork (Home Assistant)

Fork of **`climate_ip` / samsungrac** for **old Samsung air conditioners** that speak the legacy
**DPLUG / AC14K** protocol over TLS on port **2878** (e.g. ARHSFS generation, Wi‑Fi modules like
SWL‑B70F, ~2013–2018). These units are controlled **locally** (token + client cert) — no cloud, no
IR remote required.

This fork adds what the stock integration is missing: management of the AC's **on‑device on/off
schedules**.

## Features (added on top of climate_ip)
- `samsung_ac_2878_sched.get_schedules` — read schedules into the entity attribute `schedules`
- `samsung_ac_2878_sched.set_schedule` — create or edit (time, action on/off, repeat, days, enabled)
- `samsung_ac_2878_sched.delete_schedule` — delete by `schedule_id`
- Schedules live **on the AC module** and run off its **own clock** — they fire even when Home
  Assistant is offline.

Backend protocol handling uses [`pysamsung-dplug`](https://pypi.org/project/pysamsung-dplug/)
(bundled/vendored inside the integration — no pip/internet needed).

## Installation

### HACS (recommended)
HACS → *Integrations* → ⋮ → **Custom repositories** → add this repo URL, category **Integration** →
install → restart Home Assistant.

### Manual
Copy `custom_components/samsung_ac_2878_sched/` into your HA `config/custom_components/` → restart.

## Getting the device token
Each unit needs a one‑time token. Grab it with the bundled helper (needs `pip install pysamsung-dplug`):

```bash
python3 get_token.py 192.168.1.50
```
Then **power the air conditioner ON within ~40 s** — the unit emits the token right after a power‑on,
and it prints to the console. Put it in your config as `token:`.

(The helper uses the shared, public AC14K client certificate bundled in `pysamsung-dplug`.)

## Configuration (`configuration.yaml`)
```yaml
climate:
  - platform: samsung_ac_2878_sched
    config_file: '/config/custom_components/samsung_ac_2878_sched/samsung_2878.yaml'
    ip_address: '192.168.1.50'
    token: 'YOUR_TOKEN'
    cert: 'ac14k_m.pem'        # bundled; '' to skip cert
    mac: 'AA:BB:CC:DD:EE:FF'   # required for 2878 devices
    poll: True
```

## Using schedules
*Developer Tools → Actions*:
- `samsung_ac_2878_sched.get_schedules` (target your climate entity) → see `schedules` in the entity attributes.
- `samsung_ac_2878_sched.set_schedule` → `time` (local HH:MM), `action` (on/off), `repeat`
  (once/everyday/everyweek), `days` (for once/everyweek), `schedule_id` (empty = new, set = edit), `enabled`.
- `samsung_ac_2878_sched.delete_schedule` → `schedule_id`.

## ⚠️ Schedules not firing? Check the AC clock (NTP)
The schedule runs on the **AC module's own clock**. Old units used to sync time from Samsung's cloud,
which is **now shut down** — so the module clock can be stuck (e.g. at 1970), and schedules then fire at
the wrong time (or never). The unit typically hammers a hardcoded list of NTP servers that no longer
answer.

Fix: give the AC a **reachable NTP server**. On a MikroTik router you can enable the local NTP server and
transparently redirect the AC's NTP to it (works even with no internet / in an isolated IoT VLAN):
```
/system ntp server set enabled=yes
/ip firewall nat add chain=dstnat protocol=udp dst-port=123 dst-address-type=!local action=redirect to-ports=123 comment="NTP-redirect"
/ip firewall filter add chain=input protocol=udp dst-port=123 in-interface-list=LAN action=accept comment="NTP-in"
```
After this the module clock jumps to real time and schedules work.

## Migrating from `climate_ip`
This is a separate domain (`samsung_ac_2878_sched`), so upstream `climate_ip` updates never overwrite it.
When switching: remove the old `climate_ip` platform/config, delete the now‑orphaned climate entity in
*Settings → Devices & Services → Entities* (so the entity id frees up), then add this one.

## Credits
Fork of [SebuZet/atxbyea samsungrac (`climate_ip`)](https://github.com/atxbyea/samsungrac).
Schedule support via `pysamsung-dplug`.
