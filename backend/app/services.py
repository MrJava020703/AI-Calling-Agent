from datetime import datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Appointment, Call, Contact, Message

def availability(db: Session, date: str) -> dict:
    booked = {a.time for a in db.scalars(select(Appointment).where(Appointment.date == date, Appointment.status == "booked"))}
    return {"date": date, "available_slots": [f"{h:02}:00" for h in range(9, 18) if f"{h:02}:00" not in booked]}
def book_appointment(db: Session, customer_name: str, phone: str, date: str, time: str, notes: str | None = None) -> Appointment:
    if time not in availability(db, date)["available_slots"]: raise ValueError("That appointment slot is unavailable")
    item = Appointment(customer_name=customer_name, phone=phone, date=date, time=time, notes=notes)
    db.add(item); db.commit(); db.refresh(item); return item
def create_call(db: Session, phone: str, direction: str) -> Call:
    call = Call(call_sid=f"demo_{uuid4().hex}", phone_number=phone, direction=direction, status="in-progress", started_at=datetime.utcnow())
    db.add(call); db.commit(); db.refresh(call); return call
def add_message(db: Session, call: Call, role: str, content: str):
    db.add(Message(call_id=call.id, role=role, content=content)); db.commit()
    call.transcript = (call.transcript or "") + f"{role.title()}: {content}\n"; db.commit()
def get_or_create_contact(db: Session, name: str, phone: str) -> Contact:
    contact = db.scalar(select(Contact).where(Contact.phone == phone))
    if contact: return contact
    contact = Contact(name=name, phone=phone); db.add(contact); db.commit(); db.refresh(contact); return contact
class DemoAgent:
    def reply(self, text: str) -> tuple[str, str, str]:
        message = text.lower()
        if any(w in message for w in ["human", "person", "representative"]): return ("I’ll arrange a transfer to a team member now.", "handoff", "neutral")
        if "cancel" in message: return ("I can help cancel an appointment. Please tell me the appointment date.", "cancel_appointment", "neutral")
        if any(w in message for w in ["book", "appointment", "schedule"]): return ("I can help with that. What date and time would you prefer?", "book_appointment", "positive")
        if "hours" in message: return ("Our standard appointment hours are Monday to Friday, 9 AM to 5 PM.", "faq", "neutral")
        return ("Thanks for calling. I can help with appointments, account questions, order status, or a transfer to our team.", "general", "neutral")
