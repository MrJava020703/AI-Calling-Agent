from abc import ABC, abstractmethod
from .config import get_settings
class TelephonyProvider(ABC):
    @abstractmethod
    def make_call(self, to: str, webhook_url: str) -> str: ...
    @abstractmethod
    def answer_call(self) -> str: ...
class TwilioProvider(TelephonyProvider):
    def make_call(self, to: str, webhook_url: str) -> str:
        settings = get_settings()
        if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_phone_number]): raise RuntimeError("Twilio is not configured")
        from twilio.rest import Client
        return Client(settings.twilio_account_sid, settings.twilio_auth_token).calls.create(to=to, from_=settings.twilio_phone_number, url=webhook_url).sid
    def answer_call(self) -> str: return "<Response><Say>Connecting you to VoxAgent.</Say></Response>"
