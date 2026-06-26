# Prayer Times on Google Nest

Plays the Athan (call to prayer) on a Google Nest speaker at each prayer
time, and keeps a Google Calendar showing the day's prayer times for easy
reference on your phone/other devices.

## How it works

```mermaid
flowchart LR
    A[Aladhan API]
    A -->|daily fetch| B[Google Apps Script]
    B -->|creates 5 events/day| C["Google Calendar: 'Prayer Times' (visibility only)"]
    A -->|daily fetch, independent| D[athan_player.py - local script]
    D -->|Cast protocol, local network| E[Google Nest speaker]
    E -->|plays| F[Athan mp3]
```

This is two small, independent pieces sharing the same source of data:

1. A **Google Apps Script** runs once a day and writes that day's prayer
   times (Fajr, Dhuhr, Asr, Maghrib, Isha) as 5 events on a dedicated
   **Google Calendar**, so you can see them on your phone. This part is
   purely for visibility - nothing reads this calendar back.
2. A small **Python script**, running continuously on a machine on your
   home network (e.g. a Raspberry Pi, NAS, or always-on PC), independently
   fetches the same day's prayer times each morning and, at the exact
   moment each one arrives, casts the Athan audio file directly to your
   Google Nest speaker.

### Why two separate pieces, and why not Home Assistant?

Google's own platform has no way to do this end-to-end: Google Home
Routines can't be triggered by a calendar event, and even if they could,
Routine actions can't play an arbitrary external MP3 URL (only tracks from
a linked Spotify/YouTube Music account, or built-in chime sounds). Casting
a specific audio file to a Nest speaker on a precise, daily-shifting
schedule requires something that speaks the Cast protocol directly -
that's what `athan_player.py` does, using the `pychromecast` library,
without needing Home Assistant or any other hub.

Because Cast device discovery is local-network only (mDNS), this script
has to run on a machine on the same network as the speaker - it can't run
in the cloud.

## Repo contents

```
apps-script/
  Code.gs                    - paste into script.google.com; syncs the visibility calendar
  appsscript.json             - reference project manifest (timezone setting)
local-athan-player/
  athan_player.py             - the daemon that casts the Athan at prayer time
  config.example.py           - copy to config.py and fill in your details
  requirements.txt
  athan-player.service        - systemd unit to run it persistently
docs/img/                     - screenshot slots referenced below (empty for now)
```

## Prerequisites

- A Google account, for the calendar.
- A machine that's always on and on the same Wi-Fi/LAN as your Nest
  speaker - a Raspberry Pi is the typical choice, but any always-on Linux
  box (or a PC/NAS) works. Needs Python 3.9+.
- About 20-30 minutes.

---

## Step 1 - Create the dedicated Google Calendar

1. Go to [calendar.google.com](https://calendar.google.com).
2. In the left sidebar, next to "Other calendars", click **+** > **Create new calendar**.
3. Name it exactly `Prayer Times` (this must match `CONFIG.CALENDAR_NAME` in
   `Code.gs` - if you use a different name, update the script later).
4. Click **Create calendar**.

![Create calendar](docs/img/01-create-calendar.png)
*Screenshot: the "Create new calendar" form.*

---

## Step 2 - Pick your calculation method

Prayer times depend on a calculation method that varies by region/authority
(e.g. Muslim World League, Egyptian General Authority, Umm al-Qura, ISNA...).
See the full list at [aladhan.com/calculation-methods](https://aladhan.com/calculation-methods)
and find the method ID matching your local mosque/authority. This repo
defaults to `3` (Muslim World League). **Use the same method ID in both
`apps-script/Code.gs` and `local-athan-player/config.py`** so the calendar
and the actual playback always agree.

---

## Step 3 - Create the Apps Script project (calendar visibility)

1. Go to [script.google.com](https://script.google.com) > **New project**.
2. Rename the project (top-left), e.g. "Prayer Times Sync".
3. Delete the placeholder code and paste in the contents of
   [`apps-script/Code.gs`](apps-script/Code.gs).
4. Click the gear icon (**Project Settings**) and set **Time zone** to match
   `CONFIG.TIMEZONE` in the script exactly (e.g. `Europe/London`).
5. Edit the `CONFIG` block at the top of the script: `CITY`, `COUNTRY`,
   `METHOD`, `TIMEZONE`, `CALENDAR_NAME`, and optionally `ALERT_EMAIL`.
6. Save (Ctrl+S).

![Apps Script editor](docs/img/02-apps-script-editor.png)
*Screenshot: Code.gs pasted into a new Apps Script project.*

### Test it

1. In the function dropdown, select `testRunToday`, click **Run**.
2. Authorize the script when prompted (click through **Advanced > Go to
   "Prayer Times Sync" (unsafe)** - this warning appears because it's your
   own unpublished script - then **Allow** calendar access).

   ![Authorize](docs/img/03-apps-script-authorize.png)

3. Open Google Calendar - you should see new events (Fajr, Dhuhr, Asr,
   Maghrib, Isha) for today and tomorrow.

   ![Calendar events](docs/img/05-calendar-events-result.png)

### Schedule the daily trigger

1. Select `setupDailyTrigger` in the function dropdown, click **Run** once.
2. Open **Triggers** (clock icon, left sidebar) to confirm a daily trigger
   for `dailySync` exists, running shortly after midnight.

   ![Trigger](docs/img/04-apps-script-trigger.png)

The calendar now refreshes itself every night automatically.

---

## Step 4 - Set up the Athan player (actual playback)

1. On your always-on machine, get this repo onto it (e.g. `git clone` or
   copy the `local-athan-player/` folder over), then install dependencies:

   ```bash
   cd local-athan-player
   pip install -r requirements.txt
   ```

2. Copy the config template and edit it:

   ```bash
   cp config.example.py config.py
   ```

   - `CITY`, `COUNTRY`, `METHOD`, `TIMEZONE` - same values as Step 1-3.
   - `CAST_DEVICE_NAME` - the exact name of your speaker as shown in the
     Google Home app (Settings > Device name).
   - `VOLUME` - 0.0 to 1.0.
   - Make sure this machine's **system timezone** also matches `TIMEZONE`
     (e.g. `sudo timedatectl set-timezone Europe/London`), since the script
     uses the system clock to decide when to fire.

3. Test connectivity - this casts the Athan immediately, without waiting
   for an actual prayer time:

   ```bash
   python3 athan_player.py --test
   ```

   Your Nest speaker should immediately play the Athan. If it doesn't, see
   [Troubleshooting](#troubleshooting).

4. Once that works, install it so it starts automatically at boot and keeps
   running (restarting itself if it ever crashes). Pick your OS below.

### Linux (systemd)

```bash
# edit WorkingDirectory / ExecStart / User in athan-player.service first
sudo cp athan-player.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now athan-player
```

Check it's running and watch the logs:

```bash
systemctl status athan-player
journalctl -u athan-player -f
```

![Terminal logs](docs/img/06-athan-player-logs.png)
*Screenshot: `journalctl` showing the daily schedule being loaded.*

### Windows (Scheduled Task)

[`install-windows-task.ps1`](local-athan-player/install-windows-task.ps1)
registers a Scheduled Task that starts the script at boot under the
SYSTEM account (so no one needs to be logged in) and restarts it
automatically if it crashes - the Windows equivalent of the systemd unit
above.

1. Open PowerShell **as Administrator**.
2. Run:

   ```powershell
   cd path\to\local-athan-player
   powershell -ExecutionPolicy Bypass -File .\install-windows-task.ps1
   ```

3. This creates a task named `AthanPlayer` (visible in Task Scheduler) and
   starts it immediately. Logs are appended to
   `local-athan-player\athan_player.log`.

   Watch the logs live:

   ```powershell
   Get-Content .\athan_player.log -Wait -Tail 20
   ```

   ![Terminal logs](docs/img/06-athan-player-logs.png)
   *Screenshot: log output showing the daily schedule being loaded.*

To remove it later: `Unregister-ScheduledTask -TaskName "AthanPlayer"`.

> If `python` isn't found, install it from
> [python.org](https://www.python.org/downloads/) and make sure "Add
> python.exe to PATH" is checked during install - the Microsoft Store
> version sometimes only registers an app-execution alias that scheduled
> tasks running as SYSTEM can't see.

From here, the script independently re-fetches prayer times every day at
midnight rollover and casts the Athan at each one, with no further action
needed - on either OS.

---

## Troubleshooting

**Apps Script side:**
- **"Calendar not found"** - `CONFIG.CALENDAR_NAME` must exactly match the
  calendar's display name (case-sensitive).
- **Times look shifted by a few hours** - `CONFIG.TIMEZONE` doesn't match
  the script's Project Settings time zone; they must match exactly.

**Athan player side:**
- **`Cast device "..." not found on the local network`** - confirm
  `CAST_DEVICE_NAME` matches the Google Home app exactly; confirm this
  machine is on the same Wi-Fi/VLAN as the speaker (mDNS discovery doesn't
  cross subnets/VLANs); check no firewall is blocking mDNS (UDP 5353) - on
  Windows, check Windows Defender Firewall isn't blocking the network
  profile (Private vs Public) this machine is on.
- **Athan plays at the wrong time** - check this machine's system timezone
  matches `config.TIMEZONE` (`timedatectl` on Linux, or Settings > Time &
  language on Windows).
- **Linux: service doesn't survive a reboot** - make sure you ran
  `systemctl enable` (not just `start`) so it's enabled at boot.
- **Windows: task doesn't survive a reboot, or doesn't restart after a
  crash** - open Task Scheduler, find `AthanPlayer`, check its History tab
  for errors, and confirm `athan_player.log` is updating
  (`Get-Content .\athan_player.log -Tail 20`).
- **Windows: `athan_player.log` is empty or missing** - the SYSTEM account
  may not be finding `python` on PATH; confirm `Get-Command python`
  resolves in an Administrator PowerShell window, then re-run
  `install-windows-task.ps1`.
- **Wrong prayer times for your area** - try a different `METHOD` (Step 2).

---

## Possible improvements

1. **Single source of truth.** Right now the calendar and the player each
   call the Aladhan API independently with duplicated config (`CITY`,
   `COUNTRY`, `METHOD`, `TIMEZONE` in two places). The player could instead
   read the Google Calendar's private ICS feed URL (Calendar Settings >
   "Secret address in iCal format") and parse it with the `icalendar`
   Python package - removing the duplicate API call and any chance of the
   two drifting out of sync.
2. **Cache the Athan audio locally** (e.g. serve it via a tiny
   `python -m http.server` on the same machine) instead of streaming from
   `cdn.aladhan.com` every time, so playback doesn't depend on that CDN
   being reachable at the exact prayer time.
3. **Multi-speaker support** - extend `CAST_DEVICE_NAME` to a list and cast
   to all of them (e.g. living room + bedroom).
4. **Different audio for Fajr** - Aladhan's CDN hosts several adhan
   recordings (`a1.mp3`-`a9.mp3`); pick a different one when
   `prayer_name == "Fajr"`.
5. **Health/heartbeat monitoring** - ping a free service like
   healthchecks.io once a day from the script, so you get alerted by email
   if the daemon ever stops running or fails to fetch prayer times.
6. **Auto-restore other playback** - snapshot whatever was casting before
   the Athan and resume it afterward, instead of just setting a fixed
   volume.

Let me know if you'd like help implementing any of these.
