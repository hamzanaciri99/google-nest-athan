"""
Athan player - runs continuously on a machine that's on the same local
network as your Google Nest speaker (Cast discovery is local-network only).

Each day it fetches that day's prayer times directly from the Aladhan API
and, at the exact time of each prayer, casts the Athan audio to the
configured speaker. Independent of the Google Calendar / Apps Script piece
in apps-script/ - that one is for visibility only, this one does playback.

Usage:
    python3 athan_player.py            # run continuously
    python3 athan_player.py --test     # cast once immediately, then exit

See README.md for setup instructions (systemd service, etc).
"""

import argparse
import logging
import time
from datetime import datetime, date

import requests
import pychromecast

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("athan_player")


def fetch_timings(for_date: date) -> dict:
    date_str = for_date.strftime("%d-%m-%Y")
    url = f"https://api.aladhan.com/v1/timingsByCity/{date_str}"
    params = {
        "city": config.CITY,
        "country": config.COUNTRY,
        "method": config.METHOD,
        "timezonestring": config.TIMEZONE,
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()["data"]["timings"]


def build_schedule(for_date: date) -> list[tuple[str, datetime]]:
    timings = fetch_timings(for_date)
    schedule = []
    for prayer_name in config.PRAYERS:
        raw = timings[prayer_name].split(" ")[0]  # strip a possible "(TZ)" suffix
        hour, minute = (int(part) for part in raw.split(":"))
        schedule.append((prayer_name, datetime(for_date.year, for_date.month, for_date.day, hour, minute)))
    return sorted(schedule, key=lambda item: item[1])


def play_athan(prayer_name: str) -> None:
    log.info("Playing Athan for %s", prayer_name)
    casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[config.CAST_DEVICE_NAME])
    if not casts:
        log.error('Cast device "%s" not found on the local network', config.CAST_DEVICE_NAME)
        return
    try:
        cast = casts[0]
        cast.wait(timeout=15)
        cast.set_volume(config.VOLUME)
        media_controller = cast.media_controller
        media_controller.play_media(config.ADHAN_URL, "audio/mp3")
        media_controller.block_until_active(timeout=10)
    except Exception:
        log.exception("Failed to cast Athan to %s", config.CAST_DEVICE_NAME)
    finally:
        pychromecast.discovery.stop_discovery(browser)


def run_forever() -> None:
    loaded_date = None
    todays_schedule: list[tuple[str, datetime]] = []

    while True:
        now = datetime.now()

        if now.date() != loaded_date:
            try:
                todays_schedule = build_schedule(now.date())
                loaded_date = now.date()
                log.info("Loaded prayer schedule for %s: %s", loaded_date, todays_schedule)
            except Exception:
                log.exception("Failed to fetch prayer times, will retry shortly")
                time.sleep(60)
                continue

        due, todays_schedule = (
            [item for item in todays_schedule if now >= item[1]],
            [item for item in todays_schedule if now < item[1]],
        )
        for prayer_name, _ in due:
            play_athan(prayer_name)

        time.sleep(20)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test", action="store_true", help="Cast the Athan once immediately and exit (for testing connectivity)"
    )
    args = parser.parse_args()

    if args.test:
        play_athan("Test")
        return

    run_forever()


if __name__ == "__main__":
    main()
