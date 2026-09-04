<div align="center">

# 🤖 Multi-Agent Orchestration API

**A production-grade FastAPI service that orchestrates a pipeline of LLM agents — built to demonstrate software engineering, security engineering, and AI engineering practices together.**

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](./tests)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](./Dockerfile)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

</div>

---

Most "LLM API" side-projects are a single endpoint that forwards a prompt to OpenAI. This one isn't. It's built the way a real backend service ships: layered architecture, authentication, rate limiting, structured logging, caching, retries, typed contracts, and a CI pipeline — wrapped around a genuine multi-agent orchestration engine.

**The pipeline:** a task goes in → a `Researcher` agent gathers key considerations → a `Summarizer` agent drafts an answer → a `Critic` agent reviews and improves it → a validated, cached, traceable response comes out.

## Table of contents

- [Why this project](#why-this-project)
- [Architecture](#architecture)
- [Key design decisions](#key-design-decisions)
- [API reference](#api-reference)
- [Quickstart](#quickstart)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Tech stack](#tech-stack)
- [Possible extensions](#possible-extensions)

---

## Why this project

| Discipline | What's implemented |
|---|---|
| 🏗️ **Software engineering** | Layered architecture (`api` → `agents` → `services` → `core`), dependency injection, Pydantic v2 schemas, structured JSON logs with request-correlation IDs, centralized error handling, fully async, fully typed, pytest suite with mocked LLM calls, GitHub Actions CI (lint + type-check + test + Docker build) |
| 🔒 **Security engineering** | API-key auth with constant-time comparison, per-key rate limiting (Redis-backed), strict input validation as a first line of defense against prompt injection and cost abuse, security response headers (HSTS, X-Frame-Options, etc.), zero secrets in code, generic error responses that never leak internals, non-root Docker user |
| 🧠 **AI engineering** | Clean `BaseAgent` abstraction for a multi-agent pipeline, async LLM client with exponential-backoff retry and timeouts, per-step token-usage tracking, response caching to cut redundant LLM spend, configurable agent subsets and step limits |

## Architecture

```
Client
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI app                                                 │
│  ┌───────────────┐   ┌──────────────────┐   ┌─────────────┐  │
│  │ Middleware     │→ │ Auth / RateLimit  │→ │ Routers      │  │
│  │ (req-id, sec   │   │ (API key, Redis)  │   │ (/v1/...)    │  │
│  │  headers, log) │   └──────────────────┘   └──────┬──────┘  │
│  └───────────────┘                                  │         │
└──────────────────────────────────────────────────────┼─────────┘
                                                         ▼
                                          ┌────────────────────────┐
                                          │      Orchestrator       │
                                          │  Researcher → Summarizer│
                                          │       → Critic          │
                                          └───────────┬────────────┘
                                                       ▼
                                          ┌────────────────────────┐
                                          │   LLMClient (OpenAI)    │
                                          │  retry + timeout        │
                                          └────────────────────────┘
                                                       │
                                          ┌────────────▼───────────┐
                                          │  Cache (Redis / memory) │
                                          └─────────────────────────┘
```

**Layering rule:** each layer only depends on the one below it. `api/` knows about HTTP; `agents/` knows about orchestration logic but nothing about HTTP; `services/` wraps external integrations (LLM provider, cache); `core/` holds cross-cutting config, security, and error handling. This means the OpenAI provider can be swapped for a local model, or the pipeline logic can be tested, without touching the other layers.

## Key design decisions

A few choices worth knowing the reasoning behind (useful context for a code review or interview):

- **Constant-time API key comparison** (`secrets.compare_digest`) instead of `==`, to avoid timing side-channels that let an attacker infer a valid key one byte at a time.
- **Retries only on transient errors** (timeouts, rate limits) with exponential backoff via `tenacity` — not on every failure, since retrying a malformed request just wastes quota.
- **Cache key is a hash of `task + agent list`**, so identical requests are served instantly without re-running the LLM pipeline, and the cache degrades gracefully to in-memory when Redis isn't configured (so the project runs with zero external services for local development).
- **Every unhandled exception returns a generic, stable error contract** (`{"error": {"code", "message"}}`) — internals are logged server-side but never exposed to the client.
- **Pydantic input limits double as a cost/abuse control** — capping task length isn't just validation, it's a cheap guardrail against runaway LLM spend from oversized prompts.
- **Health check is unauthenticated and dependency-free** on purpose, since load balancers and orchestration platforms need to hit it cheaply and frequently.

## API reference

Full interactive docs are auto-generated at `GET /docs` (Swagger UI) and `GET /redoc`.

### `GET /api/v1/health`
Unauthenticated liveness/readiness probe.

### `POST /api/v1/orchestrate`
Runs the requested agent pipeline against a task. Requires an `X-API-Key` header and is rate-limited per key.

<details>
<summary><strong>Example request/response</strong></summary>

```bash
curl -X POST http://localhost:8000/api/v1/orchestrate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-key" \
  -d '{
        "task": "Summarize the trade-offs of using vector databases for RAG.",
        "agents": ["researcher", "summarizer", "critic"]
      }'
```

```json
{
  "task": "Summarize the trade-offs of using vector databases for RAG.",
  "final_output": "...",
  "steps": [
    {"agent": "researcher", "output": "...", "input_tokens": 42, "output_tokens": 88, "latency_ms": 812.3},
    {"agent": "summarizer", "output": "...", "input_tokens": 120, "output_tokens": 150, "latency_ms": 934.1},
    {"agent": "critic", "output": "...", "input_tokens": 180, "output_tokens": 140, "latency_ms": 701.5}
  ],
  "total_latency_ms": 2447.9,
  "cached": false
}
```

</details>

| Status | Meaning |
|---|---|
| `200` | Success |
| `401` | Missing or invalid API key |
| `422` | Invalid request payload |
| `429` | Rate limit exceeded |
| `502` | Upstream LLM provider error (after retries) |

## Quickstart

### Option A — Docker (recommended)

```bash
git clone https://github.com/<your-username>/fast-api-service.git
cd fast-api-service
cp .env.example .env      # then set OPENAI_API_KEY
docker compose up --build
```

API available at `http://localhost:8000/docs`.

### Option B — Local Python

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env      # then set OPENAI_API_KEY
uvicorn app.main:app --reload
```

## Testing

```bash
pytest -v
```

Tests exercise the real ASGI app via `httpx.AsyncClient` (no network calls) with a stub orchestrator dependency-override, so the full suite runs without an OpenAI API key or a Redis instance — and in CI.

```bash
ruff check .        # lint
black --check .     # formatting
mypy app            # static types
```

## Project structure

```
app/
├── main.py                    # App factory: middleware, routers, exception handlers
├── core/
│   ├── config.py               # Typed settings via pydantic-settings
│   ├── security.py             # API key auth dependency
│   ├── rate_limit.py           # Redis/in-memory rate limiter
│   ├── exceptions.py           # Domain exceptions + centralized handlers
│   └── logging_config.py       # Structured JSON logging + request-id context
├── middleware/
│   └── request_context.py      # Request ID, timing, security headers
├── api/
│   ├── deps.py                  # DI wiring for services/orchestrator
│   └── v1/
│       ├── router.py
│       └── endpoints/
│           ├── health.py
│           └── orchestration.py
├── agents/
│   ├── base.py                  # BaseAgent abstraction
│   ├── researcher.py / summarizer.py / critic.py
│   └── orchestrator.py          # Sequential multi-agent pipeline
├── services/
│   ├── llm_client.py            # Async OpenAI client, retry + timeout
│   └── cache.py                 # Redis/in-memory response cache
└── schemas/
    ├── agent.py                 # Request/response contracts
    └── common.py                # Shared error/health schemas

tests/                           # pytest suite (mocked orchestrator, no live calls)
.github/workflows/ci.yml         # Lint, type-check, test, Docker build
Dockerfile                       # Multi-stage, non-root runtime
docker-compose.yml               # API + Redis
```

## Tech stack

**Core:** FastAPI · Pydantic v2 · Uvicorn · Python 3.12
**AI:** OpenAI API · Tenacity (retry/backoff)
**Infra:** Docker · Docker Compose · Redis
**Quality:** pytest · pytest-asyncio · ruff · black · mypy · GitHub Actions

## Possible extensions

- Swap the sequential pipeline for a graph-based orchestrator (LangGraph) to support branching/parallel agents.
- Add streaming responses (`text/event-stream`) for token-by-token output.
- Replace static API keys with JWT auth and per-tenant usage metering.
- Add OpenTelemetry tracing spans around each agent step for distributed tracing.

---

<div align="center">

Built with FastAPI · See <a href="./LICENSE">LICENSE</a> for details.

</div>
