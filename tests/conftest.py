import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_orchestrator
from app.core.config import get_settings
from app.main import app
from app.schemas.agent import AgentStepResult, OrchestrationResponse


class StubOrchestrator:
    """Deterministic stand-in for the real orchestrator — no network calls."""

    async def run(self, task, agent_names, max_steps):
        steps = [
            AgentStepResult(
                agent=name,
                output=f"stub output for {name.value}",
                input_tokens=10,
                output_tokens=10,
                latency_ms=1.0,
            )
            for name in agent_names
        ]
        return OrchestrationResponse(
            task=task,
            final_output=steps[-1].output if steps else "",
            steps=steps,
            total_latency_ms=1.0,
            cached=False,
        )


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch):
    monkeypatch.setenv("API_KEYS", "test-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def override_orchestrator():
    app.dependency_overrides[get_orchestrator] = lambda: StubOrchestrator()
    yield
    app.dependency_overrides.pop(get_orchestrator, None)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
