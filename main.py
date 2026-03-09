"""
Alert Call Service - Main Entry Point.
Monitors Pikud HaOref alerts and makes phone calls when rockets are detected.
Uses real-time API (every 2s) + history API fallback (every 30s).
"""
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

import config
from oref_monitor import OrefAlertMonitor
from phone_caller import PhoneCaller
from web_app import app as web_app

# =============================================================================
# Logging Setup
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("alert_call.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("alert_call")


class AlertCallService:
    """
    Main service that connects the Oref alert monitor with the phone caller.
    Runs a polling loop that checks for alerts and triggers calls.
    """

    def __init__(self):
        self.monitor = OrefAlertMonitor()
        self.caller = PhoneCaller()
        self._running = False
        self._last_call_time: datetime | None = None
        self._last_history_check = time.time()
        self._total_calls_made = 0

    def _can_make_call(self) -> bool:
        """Check if enough time has passed since the last call (cooldown)."""
        if self._last_call_time is None:
            return True
        elapsed = datetime.now() - self._last_call_time
        return elapsed > timedelta(seconds=config.ALERT_COOLDOWN_SECONDS)

    def _handle_alerts(self, areas: list[str], source: str = "realtime"):
        """Handle detected alerts by making a phone call."""
        logger.warning("🚨 ALERT DETECTED via %s! Areas: %s", source, ", ".join(areas))

        # Track active alert areas for end-of-event detection
        self.monitor.mark_alert_active(areas)

        if not self._can_make_call():
            remaining = config.ALERT_COOLDOWN_SECONDS - (datetime.now() - self._last_call_time).seconds
            logger.info("Call cooldown active. Next call available in %d seconds.", remaining)
            return

        self._total_calls_made += 1
        logger.warning("📞 Making call #%d for areas: %s", self._total_calls_made, ", ".join(areas))
        call_sid = self.caller.make_alert_call(areas)
        if call_sid:
            self._last_call_time = datetime.now()
            logger.info("📞 Call made successfully (SID: %s). Total calls: %d",
                        call_sid, self._total_calls_made)
        else:
            logger.error("❌ Failed to make alert call!")

    def _handle_alert_ended(self, areas: list[str]):
        """Handle end of alert by calling end-event numbers."""
        logger.info("✅ Alert ENDED for areas: %s", ", ".join(areas))
        call_sid = self.caller.make_end_event_call(areas)
        if call_sid:
            logger.info("📞 End-event call made successfully (SID: %s)", call_sid)
        else:
            logger.info("No end-event calls made (no numbers configured or all failed).")

    def run(self):
        """Start the main alert monitoring loop."""
        self._running = True
        logger.info("=" * 60)
        logger.info("🛡️  Alert Call Service Started")
        logger.info("   Polling interval: %d seconds", config.POLL_INTERVAL_SECONDS)
        logger.info("   History check interval: 30 seconds")
        logger.info("   Call cooldown: %d seconds", config.ALERT_COOLDOWN_SECONDS)
        if config.MONITORED_AREAS:
            logger.info("   Monitored areas: %s", ", ".join(config.MONITORED_AREAS))
        else:
            logger.info("   Monitoring: ALL areas")
        logger.info("   Web interface: http://%s:%d", config.WEB_HOST, config.WEB_PORT)
        logger.info("=" * 60)

        # Start the web server in a background thread
        web_thread = threading.Thread(
            target=lambda: web_app.run(
                host=config.WEB_HOST,
                port=config.WEB_PORT,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
        )
        web_thread.start()
        logger.info("🌐 Web interface started on http://%s:%d", config.WEB_HOST, config.WEB_PORT)

        # Run startup connectivity check
        api_ok = self.monitor.startup_check()
        if api_ok:
            logger.info("✅ Startup check PASSED - API is accessible")
        else:
            logger.error("⚠️ Startup check FAILED - API may not be accessible!")
            logger.error("Will keep trying in case connectivity is restored...")

        while self._running:
            try:
                # Primary: check real-time alerts
                areas = self.monitor.check_alerts()
                if areas:
                    self._handle_alerts(areas, source="realtime")

                # Check if a previously active alert has ended
                ended_areas = self.monitor.check_alert_ended()
                if ended_areas:
                    self._handle_alert_ended(ended_areas)

                # Fallback: check history API every 30 seconds
                now = time.time()
                if now - self._last_history_check >= 30:
                    self._last_history_check = now
                    history_areas = self.monitor.check_history()
                    if history_areas:
                        self._handle_alerts(history_areas, source="history")

                time.sleep(config.POLL_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt.")
                self.stop()
            except Exception as e:
                logger.error("Unexpected error in main loop: %s", e, exc_info=True)
                time.sleep(config.POLL_INTERVAL_SECONDS)

    def stop(self):
        """Stop the service gracefully."""
        self._running = False
        logger.info("🛑 Alert Call Service Stopped")


def main():
    """Entry point for the service."""
    service = AlertCallService()

    # Handle graceful shutdown on SIGINT and SIGTERM
    def signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down...", sig)
        service.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        service.run()
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
