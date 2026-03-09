"""
Phone Numbers Store.
Manages persistent storage of phone numbers in JSON files.
Supports two separate lists: alert numbers and end-of-event numbers.
"""
import json
import logging
import os
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

PHONE_NUMBERS_FILE = os.path.join(os.path.dirname(__file__), "phone_numbers.json")
END_EVENT_NUMBERS_FILE = os.path.join(os.path.dirname(__file__), "end_event_numbers.json")


class PhoneStore:
    """Thread-safe persistent store for phone numbers."""

    def __init__(self, filepath: str, seed_from_config: bool = False):
        self._filepath = filepath
        self._lock = threading.Lock()
        self._ensure_file_exists(seed_from_config)

    def _ensure_file_exists(self, seed_from_config: bool):
        """Create the JSON file if it doesn't exist."""
        if not os.path.exists(self._filepath):
            initial_numbers = []
            if seed_from_config:
                import config
                if config.MY_PHONE_NUMBER:
                    initial_numbers.append({
                        "number": config.MY_PHONE_NUMBER,
                        "name": "מספר ראשי",
                        "added_at": datetime.now().isoformat(),
                        "active": True,
                    })
            self._save(initial_numbers)
            logger.info("Created %s with %d initial number(s).",
                        os.path.basename(self._filepath), len(initial_numbers))

    def _load(self) -> list[dict]:
        """Load phone numbers from file."""
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, numbers: list[dict]):
        """Save phone numbers to file."""
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(numbers, f, ensure_ascii=False, indent=2)

    def get_all(self) -> list[dict]:
        """Get all phone numbers."""
        with self._lock:
            return self._load()

    def get_active_numbers(self) -> list[str]:
        """Get only active phone numbers (just the number strings)."""
        with self._lock:
            numbers = self._load()
            return [n["number"] for n in numbers if n.get("active", True)]

    def add(self, number: str, name: str = "") -> dict:
        """Add a new phone number. Returns the added entry."""
        with self._lock:
            numbers = self._load()
            # Check for duplicates
            for n in numbers:
                if n["number"] == number:
                    raise ValueError(f"המספר {number} כבר קיים ברשימה")
            entry = {
                "number": number,
                "name": name or "",
                "added_at": datetime.now().isoformat(),
                "active": True,
            }
            numbers.append(entry)
            self._save(numbers)
            logger.info("Added phone number: %s (%s)", number, name)
            return entry

    def remove(self, number: str) -> bool:
        """Remove a phone number. Returns True if found and removed."""
        with self._lock:
            numbers = self._load()
            original_len = len(numbers)
            numbers = [n for n in numbers if n["number"] != number]
            if len(numbers) == original_len:
                return False
            self._save(numbers)
            logger.info("Removed phone number: %s", number)
            return True

    def toggle(self, number: str) -> bool:
        """Toggle active state of a phone number. Returns new state."""
        with self._lock:
            numbers = self._load()
            for n in numbers:
                if n["number"] == number:
                    n["active"] = not n.get("active", True)
                    self._save(numbers)
                    logger.info("Toggled phone number %s -> active=%s", number, n["active"])
                    return n["active"]
            raise ValueError(f"המספר {number} לא נמצא ברשימה")


# Singleton instances
phone_store = PhoneStore(PHONE_NUMBERS_FILE, seed_from_config=True)
end_event_store = PhoneStore(END_EVENT_NUMBERS_FILE, seed_from_config=False)
