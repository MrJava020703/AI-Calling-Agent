# VoxAgent — AI Voice Calling Agent

VoxAgent is a production-style AI receptionist platform for inbound and outbound calling workflows. It combines a React operations dashboard, FastAPI APIs, PostgreSQL persistence, JWT authorization, a modular telephony boundary, realtime updates, and a clearly-labelled credential-free Demo Mode.

## Features

- Secure administrator login and role-protected operations APIs
- Call lifecycle, transcript storage, summaries, intent and sentiment fields
- Appointment availability, booking and cancellation shared by dashboard and agent services
- Live call simulator with agent responses and WebSocket dashboard events
- Twilio-ready provider abstraction and incoming/status/recording webhook endpoints
- Knowledge base, contacts, agent configuration, analytics shell, OpenAPI docs
- Docker Compose deployment with PostgreSQL

## Architecture

`React dashboard → FastAPI REST/WebSocket API → service layer → SQLAlchemy → PostgreSQL`

Inbound calls additionally follow `Twilio webhook → call service → AI/tool orchestration → TwiML response`. The local deterministic Demo Agent is deliberately labelled as simulated; it gives a complete local demo without implying real calling or model access. Configure OpenAI and Twilio to integrate real services.

## Quick start

1. Copy `.env.example` to `.env` and keep `DEMO_MODE=true`.
2. Run `docker compose up --build`.
3. Open `http://localhost:5173` and sign in with `admin@voxagent.local` / `DemoPass123!`.
4. Start a simulated call from **Live Calls**. API docs are at `http://localhost:8000/docs`.

For local development, install `backend/requirements.txt`, run `uvicorn app.main:app --reload` in `backend`, then run `npm install && npm run dev` in `frontend`.

## Environment

Required for production: `DATABASE_URL`, a long `JWT_SECRET`, `FRONTEND_URL`, and `BACKEND_URL`. Add `OPENAI_API_KEY`/`OPENAI_MODEL` for an LLM integration and `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` for telephony. Credentials are server-only and must never be committed.

## Demo Mode

Demo Mode uses SQLite by default outside Docker, a deterministic receptionist response engine, simulated call creation, persisted transcripts, and real API/WebSocket application flow. It does not claim to place calls or synthesize voice. Use this mode for a portfolio demonstration before external credentials are available.

## Real calling setup

Set `DEMO_MODE=false`, configure Twilio credentials, deploy the API behind HTTPS, and register `/api/webhooks/voice/incoming`, `/status`, and `/recording` on the Twilio phone number. Validate Twilio request signatures at the edge before production use. The provider boundary allows a different telephony platform later.

## Testing

Run `pytest` from `backend`. Tests cover health/authentication, appointment booking, outbound Demo Mode calls, and agent intent handling. Run `npm run build` from `frontend` for a production bundle.

## Production notes and roadmap

This evaluation implementation provides the full runnable product spine. An initial PostgreSQL migration is included at `database/migrations/001_initial.sql`. Before a live launch, add an Alembic migration runner, Twilio signature validation, a rate limiter, provider-backed audio streaming/STT/TTS, OpenAI Responses/Realtime tool orchestration, encrypted recording storage, background summary jobs, comprehensive frontend component tests, and observability/alerting.
