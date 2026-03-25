"""
Twilio Phone Call Module.
Handles making phone calls via the Twilio API when alerts are triggered.
Supports calling multiple phone numbers managed via the web interface.
"""
import logging
import time
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

import config
from phone_store import phone_store, end_event_store

logger = logging.getLogger(__name__)

# Per-number cooldown: no more than 1 call per number within this many seconds
PER_NUMBER_COOLDOWN_SECONDS = 180  # 3 minutes


class PhoneCaller:
    """Manages phone calls via Twilio API."""

    def __init__(self):
        if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_PHONE_NUMBER]):
            raise ValueError(
                "Missing Twilio credentials! Please set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in your .env file."
            )

        self.client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        self.from_number = config.TWILIO_PHONE_NUMBER
        # Track last call time per phone number to enforce cooldown
        self._last_call_per_number: dict[str, float] = {}
        logger.info("PhoneCaller initialized. Calls will be made from %s", self.from_number)

    def _build_twiml(self, areas: list[str]) -> str:
        """Build TwiML XML for the phone call voice message."""
        response = VoiceResponse()

        areas_text = ", ".join(areas) if areas else "אזור לא ידוע"
        message = config.CALL_MESSAGE_TEMPLATE.format(areas=areas_text)

        # Repeat the message 3 times so the recipient hears it clearly
        for _ in range(3):
            response.say(message, language=config.CALL_LANGUAGE, voice=config.CALL_VOICE)
            response.pause(length=1)

        return str(response)

    def _is_number_on_cooldown(self, number: str) -> bool:
        """Check if a phone number was called recently (within cooldown period)."""
        last_call = self._last_call_per_number.get(number)
        if last_call is None:
            return False
        elapsed = time.time() - last_call
        return elapsed < PER_NUMBER_COOLDOWN_SECONDS

    def _record_call(self, number: str):
        """Record that a call was made to this number right now."""
        self._last_call_per_number[number] = time.time()

    def make_alert_call(self, areas: list[str]) -> str | None:
        """
        Make phone calls to all active numbers to alert about incoming rockets.

        Returns:
            First Call SID if successful, None if all failed.
        """
        active_numbers = phone_store.get_active_numbers()
        if not active_numbers:
            logger.warning("No active phone numbers to call! Add numbers via the web interface.")
            return None

        twiml = self._build_twiml(areas)
        logger.info("Making alert calls to %d number(s) for areas: %s",
                    len(active_numbers), ", ".join(areas))

        first_sid = None
        for to_number in active_numbers:
            if self._is_number_on_cooldown(to_number):
                remaining = int(PER_NUMBER_COOLDOWN_SECONDS - (time.time() - self._last_call_per_number[to_number]))
                logger.info("Skipping %s — called recently, cooldown %ds remaining", to_number, remaining)
                continue
            try:
                call = self.client.calls.create(
                    twiml=twiml,
                    to=to_number,
                    from_=self.from_number,
                )
                self._record_call(to_number)
                logger.info("Call initiated to %s! SID: %s", to_number, call.sid)
                if first_sid is None:
                    first_sid = call.sid
            except Exception as e:
                logger.error("Failed to call %s: %s", to_number, e)

        return first_sid

    def _build_end_event_twiml(self, areas: list[str]) -> str:
        """Build TwiML XML for the end-of-event voice message."""
        response = VoiceResponse()

        areas_text = ", ".join(areas) if areas else "אזור לא ידוע"
        message = config.END_EVENT_MESSAGE_TEMPLATE.format(areas=areas_text)

        for _ in range(2):
            response.say(message, language=config.CALL_LANGUAGE, voice=config.CALL_VOICE)
            response.pause(length=1)

        return str(response)

    def make_end_event_call(self, areas: list[str]) -> str | None:
        """
        Call all active end-event numbers to notify that the alert is over.

        Returns:
            First Call SID if successful, None if all failed.
        """
        active_numbers = end_event_store.get_active_numbers()
        if not active_numbers:
            logger.info("No end-event phone numbers configured.")
            return None

        twiml = self._build_end_event_twiml(areas)
        logger.info("Making end-event calls to %d number(s) for areas: %s",
                    len(active_numbers), ", ".join(areas))

        first_sid = None
        for to_number in active_numbers:
            if self._is_number_on_cooldown(to_number):
                remaining = int(PER_NUMBER_COOLDOWN_SECONDS - (time.time() - self._last_call_per_number[to_number]))
                logger.info("Skipping end-event call to %s — called recently, cooldown %ds remaining", to_number, remaining)
                continue
            try:
                call = self.client.calls.create(
                    twiml=twiml,
                    to=to_number,
                    from_=self.from_number,
                )
                self._record_call(to_number)
                logger.info("End-event call initiated to %s! SID: %s", to_number, call.sid)
                if first_sid is None:
                    first_sid = call.sid
            except Exception as e:
                logger.error("Failed to call %s for end-event: %s", to_number, e)

        return first_sid
