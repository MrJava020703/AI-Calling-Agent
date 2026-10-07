import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base, engine, get_db
from .models import Agent, Appointment, Call, Contact, KnowledgeDocument, User
from .realtime import manager
from .schemas import AgentIn, AppointmentIn, AppointmentOut, CallOut, ContactIn, ContactOut, KnowledgeIn, LoginRequest, OutboundCallIn, TokenResponse, UserOut
from .security import create_token, current_user, hash_password, require_admin, verify_password
from .services import DemoAgent, add_message, availability, book_appointment, create_call
from .telephony import TwilioProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("voxagent")
settings = get_settings()

def seed(db: Session):
    if not db.scalar(select(User).where(User.email == "admin@voxagent.local")):
        db.add(User(name="Demo Administrator", email="admin@voxagent.local", password_hash=hash_password("DemoPass123!"), role="admin"))
    if not db.scalar(select(Agent)):
        db.add(Agent(name="Alex", greeting="Hello, thank you for calling VoxAgent. This is Alex. How may I help you today?", voice="alloy", language="en", system_prompt="You are Alex, a concise, privacy-conscious receptionist. Never invent availability. Use tools for business data."))
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db: seed(db)
    yield

app = FastAPI(title="VoxAgent API", version="1.0.0", description="AI voice calling operations API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def unknown_error(_: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return Response(content='{"detail":"An unexpected server error occurred"}', status_code=500, media_type="application/json")

@app.get("/health")
def health(): return {"status": "ok", "demo_mode": settings.demo_mode}

@app.post("/api/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user)}
@app.get("/api/auth/me", response_model=UserOut, tags=["Authentication"])
def me(user: User = Depends(current_user)): return user

@app.get("/api/dashboard", tags=["Dashboard"])
def dashboard(_: User = Depends(current_user), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Call.id))) or 0
    appointments = db.scalar(select(func.count(Appointment.id)).where(Appointment.status == "booked")) or 0
    recent = db.scalars(select(Call).order_by(Call.created_at.desc()).limit(8)).all()
    return {"metrics": {"total_calls": total, "successful_calls": db.scalar(select(func.count(Call.id)).where(Call.status == "completed")) or 0, "missed_calls": db.scalar(select(func.count(Call.id)).where(Call.status == "missed")) or 0, "avg_duration": db.scalar(select(func.avg(Call.duration)).where(Call.duration.is_not(None))) or 0, "resolution_rate": 92 if settings.demo_mode else 0, "appointments_booked": appointments, "leads_generated": db.scalar(select(func.count(Contact.id))) or 0}, "recent_calls": recent}

@app.get("/api/calls", response_model=list[CallOut], tags=["Calls"])
def calls(status: str | None = None, direction: str | None = None, _: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Call).order_by(Call.created_at.desc())
    if status: q = q.where(Call.status == status)
    if direction: q = q.where(Call.direction == direction)
    return db.scalars(q.limit(100)).all()
@app.post("/api/calls/outbound", response_model=CallOut, tags=["Calls"])
async def outbound(body: OutboundCallIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    if not settings.demo_mode:
        TwilioProvider().make_call(body.phone_number, f"{settings.backend_url}/api/webhooks/voice/incoming")
    call = create_call(db, body.phone_number, "outbound")
    await manager.broadcast("call.started", {"id": call.id, "phone_number": call.phone_number, "demo": settings.demo_mode})
    return call
@app.get("/api/calls/{call_id}", tags=["Calls"])
def call_detail(call_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    call = db.get(Call, call_id)
    if not call: raise HTTPException(404, "Call not found")
    return {"call": call, "messages": call.messages}
@app.post("/api/calls/{call_id}/messages", tags=["Calls"])
async def call_message(call_id: int, payload: dict, _: User = Depends(current_user), db: Session = Depends(get_db)):
    call = db.get(Call, call_id)
    if not call: raise HTTPException(404, "Call not found")
    text = str(payload.get("content", "")).strip()
    if not text: raise HTTPException(422, "content is required")
    add_message(db, call, "caller", text)
    reply, intent, sentiment = DemoAgent().reply(text); add_message(db, call, "assistant", reply)
    call.intent, call.sentiment = intent, sentiment; db.commit()
    await manager.broadcast("transcript.message", {"call_id": call_id, "caller": text, "assistant": reply, "intent": intent})
    return {"reply": reply, "intent": intent, "sentiment": sentiment, "demo": settings.demo_mode}
@app.post("/api/calls/{call_id}/complete", tags=["Calls"])
async def complete_call(call_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    call = db.get(Call, call_id)
    if not call: raise HTTPException(404, "Call not found")
    call.status="completed"; call.ended_at=datetime.utcnow(); call.duration=max(1, int((call.ended_at-call.started_at).total_seconds())) if call.started_at else 0
    call.summary = f"{call.intent or 'General'} inquiry handled by the AI receptionist."
    db.commit(); await manager.broadcast("call.completed", {"id": call.id, "duration": call.duration}); return call

@app.get("/api/contacts", response_model=list[ContactOut], tags=["Contacts"])
def contacts(_: User = Depends(current_user), db: Session = Depends(get_db)): return db.scalars(select(Contact).order_by(Contact.created_at.desc())).all()
@app.post("/api/contacts", response_model=ContactOut, tags=["Contacts"])
def add_contact(body: ContactIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.scalar(select(Contact).where(Contact.phone == body.phone)): raise HTTPException(409, "A contact already has this phone number")
    item=Contact(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.get("/api/appointments", response_model=list[AppointmentOut], tags=["Appointments"])
def appointments(_: User = Depends(current_user), db: Session = Depends(get_db)): return db.scalars(select(Appointment).order_by(Appointment.date, Appointment.time)).all()
@app.get("/api/appointments/availability", tags=["Appointments"])
def appointment_availability(date: str, _: User = Depends(current_user), db: Session = Depends(get_db)): return availability(db, date)
@app.post("/api/appointments", response_model=AppointmentOut, tags=["Appointments"])
def add_appointment(body: AppointmentIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    try: return book_appointment(db, **body.model_dump())
    except ValueError as exc: raise HTTPException(409, str(exc))
@app.post("/api/appointments/{appointment_id}/cancel", response_model=AppointmentOut, tags=["Appointments"])
def cancel_appointment(appointment_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    item=db.get(Appointment, appointment_id)
    if not item: raise HTTPException(404, "Appointment not found")
    item.status="cancelled"; db.commit(); db.refresh(item); return item

@app.get("/api/agents", tags=["AI Agent"])
def agents(_: User = Depends(current_user), db: Session = Depends(get_db)): return db.scalars(select(Agent)).all()
@app.put("/api/agents/{agent_id}", tags=["AI Agent"])
def update_agent(agent_id: int, body: AgentIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    item=db.get(Agent, agent_id)
    if not item: raise HTTPException(404, "Agent not found")
    for key, value in body.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item
@app.get("/api/knowledge", tags=["Knowledge Base"])
def knowledge(_: User = Depends(current_user), db: Session = Depends(get_db)): return db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())).all()
@app.post("/api/knowledge", tags=["Knowledge Base"])
def add_knowledge(body: KnowledgeIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    item=KnowledgeDocument(**body.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.post("/api/webhooks/voice/incoming", tags=["Telephony Webhooks"])
async def incoming_voice(request: Request, db: Session = Depends(get_db)):
    form = await request.form(); phone = form.get("From", "unknown")
    call = create_call(db, str(phone), "inbound"); await manager.broadcast("call.incoming", {"id": call.id, "phone_number": phone})
    greeting = db.scalar(select(Agent.greeting).where(Agent.enabled == True)) or "Hello, how may I help you?"
    return Response(f"<Response><Say>{greeting}</Say></Response>", media_type="application/xml")
@app.post("/api/webhooks/voice/status", tags=["Telephony Webhooks"])
def call_status(): return {"received": True}
@app.post("/api/webhooks/voice/recording", tags=["Telephony Webhooks"])
def recording_status(): return {"received": True}
@app.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except Exception: manager.disconnect(websocket)
