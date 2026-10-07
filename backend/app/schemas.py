from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class ORMModel(BaseModel): model_config = ConfigDict(from_attributes=True)
class LoginRequest(BaseModel): email: EmailStr; password: str = Field(min_length=8)
class TokenResponse(BaseModel): access_token: str; token_type: str = "bearer"
class UserOut(ORMModel): id: int; name: str; email: EmailStr; role: str
class ContactIn(BaseModel): name: str; phone: str; email: EmailStr | None = None; company: str | None = None; notes: str | None = None
class ContactOut(ORMModel): id: int; name: str; phone: str; email: str | None; company: str | None; notes: str | None; created_at: datetime
class AppointmentIn(BaseModel): customer_name: str; phone: str; date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$"); time: str = Field(pattern=r"^\d{2}:\d{2}$"); notes: str | None = None
class AppointmentOut(ORMModel): id: int; customer_name: str; phone: str; date: str; time: str; status: str; notes: str | None; created_at: datetime
class CallOut(ORMModel): id: int; call_sid: str; direction: str; phone_number: str; status: str; duration: int | None; summary: str | None; sentiment: str | None; intent: str | None; created_at: datetime
class OutboundCallIn(BaseModel): phone_number: str = Field(min_length=7, max_length=32)
class AgentIn(BaseModel): name: str; greeting: str; system_prompt: str; voice: str = "alloy"; language: str = "en"; enabled: bool = True
class KnowledgeIn(BaseModel): title: str; content: str; category: str = "general"
