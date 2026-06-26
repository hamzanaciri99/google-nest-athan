# Prayer Times on Google Nest

Automatically plays the Athan (call to prayer) on a Google Nest speaker at
each prayer time, using a Google Calendar as the "glue" between prayer-time
data and Home Assistant.

## How it works

```mermaid
flowchart LR
    A[Aladhan API] -->|daily fetch| B[Google Apps Script]
    B -->|creates 5 events/day| C[Google Calendar: "Prayer Times"]
    C -->|read via Google Calendar integration| D[Home Assistant]
    D -->|automation: on event start| E[Google Nest speaker]
    E -->|media_player.play_media| F[Athan mp3]
```

1. A **Google Apps Script** runs once a day (just after midnight) and pulls
   that day's prayer times from the [Aladhan API](https://aladhan.com/prayer-times-api),
   writing them as 5 events (Fajr, Dhuhr, Asr, Maghrib, Isha) on a dedicated
   **Google Calendar**.
2. **Home Assistant**'s built-in Google Calendar integration reads that
   calendar.
3. An **automation** triggers whenever an event starts on that calendar and
   tells your Google Nest speaker (via the Cast integration) to play the
   Athan audio file.

## Repo contents

```
apps-script/
  Code.gs                    - the script you paste into script.google.com
  appsscript.json             - reference project manifest (timezone setting)
home-assistant/
  automations.yaml            - the automation that plays the Athan
  configuration_snippet.yaml  - an input_boolean helper to mute the Athan
docs/img/                     - screenshot slots referenced below (empty for now)
```

## Prerequisites

- A Google account.
- A working Home Assistant instance where your Google Nest speaker already
  shows up as a `media_player` (normally automatic via the Google Cast
  integration once the speaker is set up in the Google Home app).
- About 20-30 minutes, most of it one-time Google Cloud / OAuth setup.

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
defaults to `3` (Muslim World League) - you'll set this in Step 3.

---

## Step 3 - Create the Apps Script project

1. Go to [script.google.com](https://script.google.com) > **New project**.
2. Rename the project (top-left), e.g. "Prayer Times Sync".
3. Delete the placeholder code and paste in the contents of
   [`apps-script/Code.gs`](apps-script/Code.gs).
4. Click the gear icon (**Project Settings**) and set **Time zone** to match
   `CONFIG.TIMEZONE` in the script exactly (e.g. `Europe/London`).
5. Edit the `CONFIG` block at the top of the script:
   - `CITY`, `COUNTRY` - your location.
   - `METHOD` - the ID from Step 2.
   - `TIMEZONE` - must match the project's time zone from step 4.
   - `CALENDAR_NAME` - must match the calendar name from Step 1.
   - `ALERT_EMAIL` (optional) - your email, to get notified if a sync fails.
6. Save (Ctrl+S).

![Apps Script editor](docs/img/02-apps-script-editor.png)
*Screenshot: Code.gs pasted into a new Apps Script project.*

---

## Step 4 - Test the script

1. In the function dropdown at the top of the editor, select `testRunToday`,
   then click **Run**.
2. The first run will prompt you to authorize the script. Click through
   **Advanced > Go to "Prayer Times Sync" (unsafe)** - this warning appears
   because it's your own unpublished script - then **Allow** calendar access.

   ![Authorize](docs/img/03-apps-script-authorize.png)
   *Screenshot: the Google permissions popup.*

3. Check **Executions** (left sidebar) for a successful run, then open
   Google Calendar - you should see new events (Fajr, Dhuhr, Asr, Maghrib,
   Isha) for today and tomorrow.

   ![Calendar events](docs/img/05-calendar-events-result.png)
   *Screenshot: the generated prayer-time events in Google Calendar.*

4. If it fails, see [Troubleshooting](#troubleshooting).

---

## Step 5 - Schedule the daily trigger

1. Select `setupDailyTrigger` in the function dropdown and click **Run** once.
2. Open **Triggers** (clock icon, left sidebar) to confirm a daily trigger
   for `dailySync` now exists, running shortly after midnight.

   ![Trigger](docs/img/04-apps-script-trigger.png)
   *Screenshot: the Triggers page showing the daily trigger.*

From now on, the calendar refreshes itself every night automatically - you
don't need to touch the script again.

---

## Step 6 - Connect the calendar to Home Assistant

Home Assistant needs its own OAuth client to read your Google Calendar
(separate from the Apps Script's own authorization above).

1. Go to the [Google Cloud Console](https://console.cloud.google.com) and
   create (or select) a project.
2. **APIs & Services > Library** - enable **Google Calendar API**.
3. **APIs & Services > OAuth consent screen** - configure as **External**,
   add your own Google account as a test user.
4. **APIs & Services > Credentials > Create Credentials > OAuth client ID**
   - Application type: **TVs and Limited Input devices** (this is the type
   Home Assistant's setup flow expects). Copy the **Client ID** and
   **Client Secret**.

   ![OAuth client](docs/img/06-gcloud-oauth-client.png)
   *Screenshot: the OAuth client ID screen in Google Cloud Console.*

5. In Home Assistant: **Settings > Devices & Services > Add Integration >
   Google Calendar**. Paste the Client ID/Secret, follow the device-code
   link it shows you to authorize, then select the **Prayer Times** calendar.

   ![HA integration](docs/img/07-ha-google-calendar-integration.png)
   *Screenshot: adding the Google Calendar integration in Home Assistant.*

6. Home Assistant creates an entity such as `calendar.prayer_times`. Confirm
   it under **Settings > Devices & Services > Entities**.

---

## Step 7 - Find your Nest speaker's entity ID

1. **Settings > Devices & Services > Entities**, search for your speaker.
2. Note its entity ID, e.g. `media_player.living_room_speaker`.

![Nest entity](docs/img/08-ha-entities-nest-speaker.png)
*Screenshot: locating the Nest speaker's entity ID.*

---

## Step 8 - Add the mute helper and the automation

1. Add the contents of
   [`home-assistant/configuration_snippet.yaml`](home-assistant/configuration_snippet.yaml)
   to your `configuration.yaml`, then restart Home Assistant (or reload
   **Input Booleans** from Settings > System if available).

   ![Helper](docs/img/10-ha-input-boolean.png)
   *Screenshot: the `athan_enabled` helper.*

2. **Settings > Automations & Scenes >** top-right **⋮** menu **> Edit in
   YAML**, then paste/merge in the `automation:` block from
   [`home-assistant/automations.yaml`](home-assistant/automations.yaml).

   ![Automation YAML](docs/img/09-ha-automations-yaml.png)
   *Screenshot: the automation pasted into Home Assistant's YAML editor.*

3. Replace the two placeholder entity IDs with your real ones from Steps 6
   and 7:
   - `calendar.prayer_times` -> your calendar entity.
   - `media_player.living_room_speaker` -> your Nest speaker entity.
4. Save.

---

## Step 9 - End-to-end test

1. On the "Prayer Times" calendar, create a one-off test event starting a
   couple of minutes from now (any title works - the automation triggers on
   any event start on this calendar, not just specific titles).
2. Wait for it to start - your Nest speaker should play the Athan.
3. Check **Settings > Automations & Scenes > "Play Athan on Prayer Time" >
   trace** to confirm it ran successfully.

   ![Trace](docs/img/11-ha-automation-trace-success.png)
   *Screenshot: a successful automation trace.*

---

## Troubleshooting

- **"Calendar not found" in Apps Script** - `CONFIG.CALENDAR_NAME` must
  exactly match the calendar's display name (case-sensitive).
- **Prayer times look shifted by a few hours** - `CONFIG.TIMEZONE` doesn't
  match the script's Project Settings time zone; they must match exactly.
- **Nothing plays on the speaker** - confirm the speaker supports
  `media_player.play_media` by testing the same service call manually from
  **Developer Tools > Actions**; check the automation trace for the actual
  error.
- **Wrong prayer times for your area** - try a different `METHOD`; some
  regions need a specific tuned method (see Step 2).

---

## Possible improvements

A few ways this project could be made simpler or more robust, roughly
ordered by impact:

1. **Skip Google Calendar/Apps Script entirely.** Home Assistant has a
   built-in **Islamic Prayer Times** integration (config-flow, no API key,
   calculates locally) that exposes a sensor per prayer. You'd automate
   directly off `sensor.fajr_prayer_time` etc., with no Google Cloud OAuth
   setup at all. Trade-off: you lose the calendar view of prayer times on
   your phone/other devices, which seems to be part of why you wanted the
   calendar in the first place - worth considering only if visibility
   outside Home Assistant isn't important to you.
2. **Sync a month at a time instead of daily.** Aladhan also has a
   `calendarByCity` endpoint returning a whole month in one call. Running
   that monthly (with the existing daily trigger kept only as a lightweight
   fallback re-sync) means a single missed trigger run doesn't leave you
   without prayer times for a day.
3. **Cache the Athan audio locally in Home Assistant** (`/config/www/`)
   instead of streaming from `cdn.aladhan.com` every time, so playback isn't
   dependent on that CDN being reachable at the exact prayer time.
4. **Different audio for Fajr.** Aladhan's CDN hosts several adhan
   recordings (`a1.mp3`-`a9.mp3`); you could pick a different one for Fajr
   based on the calendar event's title in the automation's action.
5. **Auto-restore volume/playback.** Snapshot whatever was playing before
   the Athan (`media_player.media_pause` / a `scene` snapshot) and resume it
   afterward, instead of just setting a fixed volume.
6. **Quiet hours / Do Not Disturb integration.** Extend the
   `athan_enabled` helper into a schedule helper, so it auto-mutes overnight
   or during specific calendar-free periods without manual toggling.
7. **Push notification fallback.** If the speaker is offline or unreachable,
   send a mobile notification instead, so you don't miss a prayer time
   silently.

Let me know if you'd like help implementing any of these.
