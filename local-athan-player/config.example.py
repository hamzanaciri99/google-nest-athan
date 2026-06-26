# Copy this file to config.py (in the same folder) and fill in your own
# values. config.py is gitignored so your personal settings stay local.
#
# Keep CITY / COUNTRY / METHOD / TIMEZONE identical to the CONFIG block in
# apps-script/Code.gs, so the Google Calendar (visibility) and this player
# (actual playback) always agree on prayer times.

CITY = "Dublin"
COUNTRY = "Ireland"
METHOD = 3                     # Aladhan calculation method ID - see https://aladhan.com/calculation-methods
TIMEZONE = "Europe/Dublin"     # IANA timezone - must also match this machine's system timezone

PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

CAST_DEVICE_NAME = "Living Room display"   # exact name as shown in the Google Home app
VOLUME = 0.6                                # 0.0 - 1.0
ADHAN_URL = "https://cdn.aladhan.com/audio/adhans/a9.mp3"

# Optional: shown as the background/thumbnail image on screened devices
# (e.g. Nest Hub) while the Athan plays. Leave as "" to use the device's
# default. Must be a public, directly-loadable image URL (jpg/png).
BACKGROUND_IMAGE_URL = "https://cdn.britannica.com/66/269466-138-10EDD7D6/adhan-muslim-call-to-prayer.jpg"
