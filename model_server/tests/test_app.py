import pytest
import httpx

from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


# [TODO] Review: check the following code. Seems something wrong with asyncio package❗
# Unit tests for the health check endpoint
@pytest.mark.asyncio
async def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# [TODO] Review: check the following code. Seems something wrong with asyncio package❗
# Unit test for the models endpoint
@pytest.mark.asyncio
async def test_models():
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json()["object"] == "list"
    assert len(response.json()["data"]) > 0


# [TODO] Review: check the following code. Seems something wrong with asyncio package❗
# Unit test for the guardrail endpoint
@pytest.mark.asyncio
async def test_guardrail_endpoint():
    request_data = {"input": "Test for jailbreak and toxicity", "task": "jailbreak"}
    response = client.post("/guardrails", json=request_data)
    assert response.status_code == 200
    assert "response" in response.json()


# [TODO] Review: check the following code. Seems something wrong with asyncio package❗
# Unit test for the function calling endpoint
@pytest.mark.asyncio
async def test_function_calling_endpoint():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "model": "Arch-Function",
            "tools": [],
            "metadata": {"x-arch-state": "[]"},
        }
        response = await client.post("/function_calling", json=request_data)
        assert response.status_code == 200
        assert "result" in response.json()
