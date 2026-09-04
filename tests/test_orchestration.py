import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_orchestrate_requires_api_key(client):
    response = await client.post("/api/v1/orchestrate", json={"task": "hello"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_orchestrate_rejects_empty_task(client, override_orchestrator):
    response = await client.post(
        "/api/v1/orchestrate",
        json={"task": "   "},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 422


async def test_orchestrate_happy_path(client, override_orchestrator):
    response = await client.post(
        "/api/v1/orchestrate",
        json={"task": "Explain vector databases briefly."},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["task"] == "Explain vector databases briefly."
    assert len(body["steps"]) == 3
    assert body["steps"][0]["agent"] == "researcher"
    assert body["final_output"]


async def test_orchestrate_custom_agent_subset(client, override_orchestrator):
    response = await client.post(
        "/api/v1/orchestrate",
        json={"task": "Just summarize this.", "agents": ["summarizer"]},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["steps"]) == 1
    assert body["steps"][0]["agent"] == "summarizer"


async def test_invalid_api_key_rejected(client, override_orchestrator):
    response = await client.post(
        "/api/v1/orchestrate",
        json={"task": "hello"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
