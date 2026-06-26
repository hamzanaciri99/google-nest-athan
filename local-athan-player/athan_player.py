"""
Athan player - runs continuously on a machine that's on the same local
network as your Google Nest speaker (Cast discovery is local-network only).

Each day it fetches that day's prayer times directly from the Aladhan API
and, at the exact time of each prayer, casts the Athan audio to the
configured speaker, restoring whatever was playing beforehand afterward.

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

DEFAULT_MEDIA_RECEIVER_APP_ID = "CC1AD845"


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


def ping_healthcheck(success: bool = True) -> None:
    url = getattr(config, "HEALTHCHECK_URL", "")
    if not url:
        return
    ping_url = url if success else url.rstrip("/") + "/fail"
    try:
        requests.get(ping_url, timeout=10)
    except requests.RequestException:
        log.warning("Healthcheck ping to %s failed (network issue), continuing anyway", ping_url)


def snapshot_state(cast) -> dict:
    """Best-effort capture of whatever the speaker was doing before the Athan."""
    media_controller = cast.media_controller
    media_controller.update_status()
    time.sleep(1)  # give the status response a moment to arrive
    status = media_controller.status
    return {
        "volume": cast.status.volume_level if cast.status else None,
        "app_id": cast.app_id,
        "content_id": status.content_id,
        "content_type": status.content_type,
        "current_time": status.current_time,
        "player_state": status.player_state,
    }


def wait_until_finished(media_controller, max_wait_seconds: int = 360, poll_interval: int = 3) -> None:
    time.sleep(5)  # let the stream start before we start checking for IDLE
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        media_controller.update_status()
        if media_controller.status.player_state in ("IDLE", "UNKNOWN"):
            return
        time.sleep(poll_interval)
    log.warning("Timed out waiting for Athan playback to finish")


def restore_state(cast, previous: dict) -> None:
    """Best-effort restore. Reliable when the previous app was the Default
    Media Receiver (a plain media URL); for other apps (Spotify, YouTube
    Music, etc.) we can only relaunch the app - resuming its exact track
    and position is up to that app, not something we can control."""
    if previous.get("volume") is not None:
        cast.set_volume(previous["volume"])

    if previous.get("player_state") not in ("PLAYING", "PAUSED"):
        return  # nothing meaningful was happening before, leave it idle

    if previous.get("app_id") == DEFAULT_MEDIA_RECEIVER_APP_ID and previous.get("content_id"):
        try:
            media_controller = cast.media_controller
            media_controller.play_media(
                previous["content_id"],
                previous["content_type"] or "audio/mp3",
                current_time=previous["current_time"],
                autoplay=(previous["player_state"] == "PLAYING"),
            )
            media_controller.block_until_active(timeout=10)
            log.info("Resumed previous media at %.0fs", previous["current_time"] or 0)
            return
        except Exception:
            log.exception("Failed to resume previous media, leaving device as-is")
            return

    if previous.get("app_id"):
        try:
            cast.start_app(previous["app_id"])
            log.info(
                "Relaunched previous app %s (exact resume isn't guaranteed for non-default apps)",
                previous["app_id"],
            )
        except Exception:
            log.exception("Failed to relaunch previous app")


def play_athan(prayer_name: str, restore_previous: bool = True) -> None:
    log.info("Playing Athan for %s", prayer_name)
    casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[config.CAST_DEVICE_NAME])
    if not casts:
        log.error('Cast device "%s" not found on the local network', config.CAST_DEVICE_NAME)
        return
    try:
        cast = casts[0]
        cast.wait(timeout=15)

        previous = snapshot_state(cast) if restore_previous else None

        cast.set_volume(config.VOLUME)
        media_controller = cast.media_controller
        media_controller.play_media(
            config.ADHAN_URL,
            "audio/mp3",
            title=f"{prayer_name} - Athan",
            thumb=getattr(config, "BACKGROUND_IMAGE_URL", "") or None,
        )
        media_controller.block_until_active(timeout=10)

        if restore_previous:
            wait_until_finished(media_controller)
            restore_state(cast, previous)
    except Exception:
        log.exception("Failed to cast Athan to %s", config.CAST_DEVICE_NAME)
    finally:
        browser.stop_discovery()


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
                ping_healthcheck(success=True)
            except Exception:
                log.exception("Failed to fetch prayer times, will retry shortly")
                ping_healthcheck(success=False)
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
        play_athan("Test", restore_previous=False)
        return

    run_forever()


if __name__ == "__main__":
    main()
