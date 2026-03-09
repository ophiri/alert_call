"""
Configuration for the Alert Call service.
Load settings from environment variables or .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Twilio Configuration
# =============================================================================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")  # Your Twilio phone number

# =============================================================================
# Your Phone Number - the number to call when an alert is triggered
# =============================================================================
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER", "")  # e.g., +972501234567

# =============================================================================
# Pikud HaOref (Home Front Command) API
# =============================================================================
OREF_ALERTS_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
OREF_HISTORY_URL = "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json"

# Headers required by the Oref API
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# =============================================================================
# Alert Service Settings
# =============================================================================
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))  # How often to check for new alerts
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # Min time between phone calls (5 min)

# Areas to monitor - leave empty to monitor ALL areas, or specify specific areas
# Example: ["תל אביב - מרכז העיר", "רמת גן", "גבעתיים"]
_monitored_env = os.getenv("MONITORED_AREAS", "")
MONITORED_AREAS = [a.strip() for a in _monitored_env.split(",") if a.strip()] if _monitored_env else []

# =============================================================================
# Web Interface Settings
# =============================================================================
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "")  # Set in .env file
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "")  # Set in .env file

# =============================================================================
# Call Settings
# =============================================================================
CALL_MESSAGE_TEMPLATE = os.getenv(
    "CALL_MESSAGE_TEMPLATE",
    "אזהרה! התקבלה התרעה על ירי רקטות באזור {areas}. יש להיכנס למרחב המוגן מיד!"
)
END_EVENT_MESSAGE_TEMPLATE = os.getenv(
    "END_EVENT_MESSAGE_TEMPLATE",
    "עדכון: האירוע באזור {areas} הסתיים. ניתן לצאת מהמרחב המוגן."
)
CALL_LANGUAGE = "he-IL"
CALL_VOICE = os.getenv("CALL_VOICE", "Google.he-IL-Standard-A")
