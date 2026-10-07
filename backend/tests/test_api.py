import os
os.environ["DATABASE_URL"] = "sqlite:///./test_voxagent.db"
os.environ["DEMO_MODE"] = "true"
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
def token():
    response = client.post("/api/auth/login", json={"email":"admin@voxagent.local", "password":"DemoPass123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
def test_health_and_auth():
    with client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/auth/me", headers=token()).status_code == 200
def test_booking_and_demo_call():
    with client:
        headers=token()
        appointment=client.post("/api/appointments", headers=headers, json={"customer_name":"Ada","phone":"+15550001111","date":"2026-10-09","time":"10:00"})
        assert appointment.status_code == 200
        call=client.post("/api/calls/outbound", headers=headers, json={"phone_number":"+15550001111"}).json()
        reply=client.post(f"/api/calls/{call['id']}/messages", headers=headers, json={"content":"I need an appointment"})
        assert reply.status_code == 200 and reply.json()["intent"] == "book_appointment"
