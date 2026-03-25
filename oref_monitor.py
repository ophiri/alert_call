"""
Pikud HaOref (Home Front Command) Alert Monitor.
Polls the Oref API for real-time rocket/missile alerts.
Uses both the real-time API and the history API as a fallback.
"""
import hashlib
import json
import logging
import time
from datetime import datetime

import requests

import config

logger = logging.getLogger(__name__)


class OrefAlertMonitor:
    """Monitors the Home Front Command alert API for new alerts."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.OREF_HEADERS)
        self._seen_alert_hashes: set[str] = set()
        self._seen_history_ids: set[str] = set()
        self._consecutive_errors = 0
        self._total_polls = 0
        self._last_status_log = time.time()
        self._api_working = False
        # Track the last raw response to avoid re-processing identical responses
        self._last_raw_response = ""
        # Track currently active alerts to detect when they end
        self._active_alert_areas: set[str] = set()
        self._alert_active = False
        # Counter for consecutive empty API responses (used for end-of-event detection)
        self._consecutive_empty_count = 0
        # Require N consecutive empty polls before declaring end-of-event
        # At 2s poll interval, 5 polls = 10 seconds of confirmed silence
        self._END_EVENT_EMPTY_THRESHOLD = 5

        logger.info("OrefAlertMonitor initialized.")
        if config.MONITORED_AREAS:
            logger.info("Monitoring specific areas: %s", ", ".join(config.MONITORED_AREAS))
        else:
            logger.info("Monitoring ALL areas.")

    @staticmethod
    def _hash_alert(alert: dict) -> str:
        """Create a stable hash for an alert, regardless of whether it has an id."""
        # Use ALL relevant fields to create a unique fingerprint
        key_parts = [
            str(alert.get("id", "")),
            str(alert.get("cat", "")),
            str(alert.get("title", "")),
            str(alert.get("desc", "")),
        ]
        # Sort the areas for consistent hashing
        areas = alert.get("data", [])
        if isinstance(areas, str):
            areas = [areas]
        key_parts.extend(sorted(str(a) for a in areas))
        key = "|".join(key_parts)
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def startup_check(self) -> bool:
        """Verify API connectivity on startup. Returns True if API is accessible."""
        logger.info("Running startup connectivity check...")

        # Check our external IP
        try:
            ip_resp = self.session.get("https://api.ipify.org?format=json", timeout=10)
            logger.info("Container external IP: %s", ip_resp.json().get("ip", "unknown"))
        except Exception as e:
            logger.warning("Could not determine external IP: %s", e)

        # Check real-time alerts API and pre-seed any active alerts
        try:
            resp = self.session.get(config.OREF_ALERTS_URL, timeout=10)
            logger.info("Alerts API status code: %d, response length: %d",
                        resp.status_code, len(resp.text))
            if resp.status_code == 200:
                logger.info("Alerts API is ACCESSIBLE (200 OK)")
                self._api_working = True
                # Pre-seed: if there are active alerts right now, mark them as seen
                # so we don't trigger calls on startup for already-active alerts
                clean_text = resp.text.strip().lstrip('\ufeff').strip()
                if clean_text:
                    try:
                        data = resp.json()
                        if data:
                            if isinstance(data, dict):
                                data = [data]
                            if isinstance(data, list):
                                for alert in data:
                                    h = self._hash_alert(alert)
                                    self._seen_alert_hashes.add(h)
                                logger.info("Pre-seeded %d active alert hashes (won't trigger calls on existing alerts)",
                                            len(self._seen_alert_hashes))
                    except (ValueError, Exception):
                        pass
                self._last_raw_response = resp.text
            elif resp.status_code == 403:
                logger.error("Alerts API returned 403 FORBIDDEN - IP may not be Israeli!")
                self._api_working = False
            else:
                logger.warning("Alerts API returned unexpected status: %d", resp.status_code)
                logger.warning("Response body: %s", resp.text[:500])
        except Exception as e:
            logger.error("Alerts API connectivity check FAILED: %s", e)

        # Check history API and pre-seed
        try:
            resp = self.session.get(config.OREF_HISTORY_URL, timeout=10)
            logger.info("History API status code: %d, response length: %d",
                        resp.status_code, len(resp.text))
            if resp.status_code == 200:
                logger.info("History API is ACCESSIBLE (200 OK)")
                if not self._api_working:
                    self._api_working = True
                    logger.info("Will use History API as primary source")
                if resp.text.strip():
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            logger.info("History API has %d alerts today", len(data))
                            for alert in data:
                                rid = str(alert.get("rid", ""))
                                alert_date = alert.get("alertDate", "")
                                area = alert.get("data", "")
                                self._seen_history_ids.add(f"{rid}_{alert_date}_{area}")
                            logger.info("Pre-seeded %d history IDs", len(self._seen_history_ids))
                    except ValueError:
                        pass
            elif resp.status_code == 403:
                logger.error("History API returned 403 FORBIDDEN!")
        except Exception as e:
            logger.error("History API connectivity check FAILED: %s", e)

        return self._api_working

    def _area_matches(self, area: str) -> bool:
        """Check if an area matches any of our monitored areas."""
        if not config.MONITORED_AREAS:
            return True

        area_clean = area.strip()
        for monitored in config.MONITORED_AREAS:
            monitored = monitored.strip()
            if monitored in area_clean or area_clean in monitored:
                return True
        return False

    def check_alerts(self) -> list[str] | None:
        """
        Check the Oref real-time API for current alerts.
        Returns list of area names with NEW alerts, or None.
        """
        self._total_polls += 1

        now = time.time()
        if now - self._last_status_log > 300:
            logger.info(
                "Status: %d total polls, %d errors, API ok: %s, seen hashes: %d",
                self._total_polls, self._consecutive_errors, self._api_working,
                len(self._seen_alert_hashes)
            )
            self._last_status_log = now

        try:
            response = self.session.get(config.OREF_ALERTS_URL, timeout=5)

            if response.status_code != 200:
                self._consecutive_errors += 1
                if self._consecutive_errors <= 3 or self._consecutive_errors % 100 == 0:
                    logger.error(
                        "Oref API status %d (error #%d). Body: %s",
                        response.status_code, self._consecutive_errors,
                        response.text[:200]
                    )
                self._api_working = False
                return None

            self._api_working = True

            # Strip BOM and whitespace
            clean_text = response.text.strip().lstrip('\ufeff').strip()
            if not clean_text:
                if self._consecutive_errors > 0:
                    logger.info("API recovered after %d errors", self._consecutive_errors)
                self._consecutive_errors = 0
                self._consecutive_empty_count += 1
                return None

            # Quick check: if the raw response is identical to last time, skip entirely
            if response.text == self._last_raw_response:
                return None
            self._last_raw_response = response.text

            # Try parsing JSON
            try:
                data = json.loads(clean_text)
            except ValueError:
                try:
                    data = response.json()
                except ValueError:
                    logger.warning("Invalid JSON (len=%d): %s",
                                   len(response.text), repr(response.text[:100]))
                    return None

            if not data:
                self._consecutive_errors = 0
                self._consecutive_empty_count += 1
                return None

            self._consecutive_empty_count = 0
            logger.warning("RAW ALERT DATA: %s", str(data)[:500])

            if isinstance(data, dict):
                data = [data]

            new_areas = []
            for alert in data:
                alert_hash = self._hash_alert(alert)
                alert_id = str(alert.get("id", ""))
                alert_cat = alert.get("cat", "")
                alert_title = alert.get("title", "")
                areas = alert.get("data", [])

                if isinstance(areas, str):
                    areas = [areas]

                # Skip if we've already seen this exact alert content
                if alert_hash in self._seen_alert_hashes:
                    continue

                self._seen_alert_hashes.add(alert_hash)
                logger.warning("NEW alert hash=%s id=%s cat=%s title=%s areas=%s",
                               alert_hash[:8], alert_id, alert_cat, alert_title, areas)

                for area in areas:
                    if self._area_matches(area):
                        new_areas.append(area)
                        logger.warning("MATCHED area: %s", area)
                    else:
                        logger.info("Skipping non-matching area: %s", area)

            self._consecutive_errors = 0

            if len(self._seen_alert_hashes) > 2000:
                self._seen_alert_hashes = set(list(self._seen_alert_hashes)[-1000:])

            return new_areas if new_areas else None

        except requests.Timeout:
            self._consecutive_errors += 1
            if self._consecutive_errors <= 3 or self._consecutive_errors % 100 == 0:
                logger.warning("Timeout (error #%d)", self._consecutive_errors)
            return None
        except requests.ConnectionError:
            self._consecutive_errors += 1
            if self._consecutive_errors <= 3 or self._consecutive_errors % 100 == 0:
                logger.warning("Connection error (#%d)", self._consecutive_errors)
            return None
        except Exception as e:
            self._consecutive_errors += 1
            logger.error("Unexpected error (#%d): %s", self._consecutive_errors, e)
            return None

    def check_history(self) -> list[str] | None:
        """
        Check the Oref History API for recent alerts (fallback).
        Returns list of area names with new alerts, or None.
        """
        try:
            response = self.session.get(config.OREF_HISTORY_URL, timeout=10)

            if response.status_code != 200:
                return None

            if not response.text or response.text.strip() == "":
                return None

            try:
                data = response.json()
            except ValueError:
                return None

            if not isinstance(data, list) or not data:
                return None

            new_areas = []
            for alert in data:
                rid = str(alert.get("rid", ""))
                alert_date = alert.get("alertDate", "")
                area = alert.get("data", "")
                cat_desc = alert.get("category_desc", "")

                history_key = f"{rid}_{alert_date}_{area}"

                if history_key in self._seen_history_ids:
                    continue

                self._seen_history_ids.add(history_key)

                # Only process alerts from the last 5 minutes
                try:
                    alert_time = datetime.strptime(alert_date, "%Y-%m-%d %H:%M:%S")
                    age_seconds = (datetime.now() - alert_time).total_seconds()
                    if age_seconds > 300:
                        continue
                except (ValueError, TypeError):
                    continue

                if self._area_matches(area):
                    new_areas.append(area)
                    logger.warning("HISTORY ALERT MATCHED: %s | %s | %s",
                                   alert_date, cat_desc, area)

            if len(self._seen_history_ids) > 5000:
                self._seen_history_ids = set(list(self._seen_history_ids)[-2500:])

            return new_areas if new_areas else None

        except Exception as e:
            logger.debug("History check error: %s", e)
            return None

    def mark_alert_active(self, areas: list[str]):
        """Mark areas as having an active alert."""
        self._active_alert_areas.update(areas)
        self._alert_active = True
        # Reset empty counter so end-event detection starts fresh
        self._consecutive_empty_count = 0
        logger.info("Active alert areas: %s", ", ".join(self._active_alert_areas))

    def check_alert_ended(self) -> list[str] | None:
        """
        Check if a previously active alert has ended.
        Requires multiple consecutive empty API responses to confirm
        the alert has truly ended (avoids false triggers from brief
        API hiccups or race conditions with the history API).
        """
        if not self._alert_active:
            return None

        if self._consecutive_empty_count >= self._END_EVENT_EMPTY_THRESHOLD:
            ended_areas = list(self._active_alert_areas)
            logger.info("\u2705 Alert ENDED for areas: %s (after %d consecutive empty responses)",
                        ", ".join(ended_areas), self._consecutive_empty_count)
            self._active_alert_areas.clear()
            self._alert_active = False
            self._consecutive_empty_count = 0
            return ended_areas if ended_areas else None

        if self._consecutive_empty_count > 0:
            logger.debug("Waiting for end-of-event confirmation: %d/%d empty responses",
                         self._consecutive_empty_count, self._END_EVENT_EMPTY_THRESHOLD)

        return None

    def reset(self):
        """Reset the seen alerts cache."""
        self._seen_alert_hashes.clear()
        self._seen_history_ids.clear()
        logger.info("Alert cache cleared.")
