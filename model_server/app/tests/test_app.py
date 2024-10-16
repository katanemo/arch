import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app  # Assuming your FastAPI app is in main.py
from unittest.mock import patch
import app.commons.globals as glb
import logging

logger = logging.getLogger(__name__)

client = TestClient(app)

logger.info(f"Model will be loaded on device: {glb.DEVICE}")


# Unit tests for the health check endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Unit test for the models endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_models():
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json()["object"] == "list"
    assert len(response.json()["data"]) > 0


# Unit test for embeddings endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_embedding():
    request_data = {"input": "Test embedding", "model": "katanemo/bge-large-en-v1.5"}
    response = client.post("/embeddings", json=request_data)
    if request_data["model"] == "katanemo/bge-large-en-v1.5":
        assert response.status_code == 200
        assert response.json()["object"] == "list"
        assert "data" in response.json()
    else:
        assert response.status_code == 400


# Unit test for the guard endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_guard():
    request_data = {"input": "Test for jailbreak and toxicity", "task": "jailbreak"}
    response = client.post("/guard", json=request_data)
    assert response.status_code == 200
    assert "jailbreak_verdict" in response.json()


# Unit test for the zero-shot endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_zeroshot():
    request_data = {
        "input": "Test input",
        "labels": ["label1", "label2"],
        "model": "katanemo/bart-large-mnli",
    }
    response = client.post("/zeroshot", json=request_data)
    if request_data["model"] == "katanemo/bart-large-mnli":
        assert response.status_code == 200
        assert "predicted_class" in response.json()
    else:
        assert response.status_code == 400


# Unit test for the hallucination endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_hallucination():
    request_data = {
        "prompt": "Test hallucination",
        "parameters": {"param1": "value1"},
        "model": "katanemo/bart-large-mnli",
    }
    response = client.post("/hallucination", json=request_data)
    if request_data["model"] == "katanemo/bart-large-mnli":
        assert response.status_code == 200
        assert "params_scores" in response.json()
    else:
        assert response.status_code == 400


# Unit test for the chat completion endpoint
@pytest.mark.asyncio
@patch("app.loader.glb.DEVICE", glb.DEVICE)  # Mock the device to 'cpu'
async def test_chat_completion():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "model": "Arch-Function-1.5B",
            "tools": [],  # Assuming tools is part of the req as per the function
            "metadata": {"x-arch-state": "[]"},  # Assuming metadata is needed
        }
        response = await client.post("/v1/chat/completions", json=request_data)
        assert response.status_code == 200
        assert "choices" in response.json()
