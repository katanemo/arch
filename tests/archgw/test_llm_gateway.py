import json
import pytest
import requests

from common import LLM_GATEWAY_ENDPOINT, get_data_chunks


# test default llm
@pytest.mark.parametrize("stream", [True, False])
@pytest.mark.parametrize("provider_hint", [None, "gpt-3.5-turbo-0125"])
def test_llm_gateway(stream, provider_hint):
    expected_llm = "gpt-4o-mini-2024-07-18" if provider_hint is None else provider_hint
    body = {
        "messages": [
            {
                "role": "user",
                "content": "hello",
            }
        ],
        "stream": stream,
    }
    headers = {}
    if provider_hint:
        headers["x-arch-llm-provider-hint"] = provider_hint
    response = requests.post(
        LLM_GATEWAY_ENDPOINT, json=body, stream=stream, headers=headers
    )
    assert response.status_code == 200
    if stream:
        chunks = get_data_chunks(response)
        assert len(chunks) > 0
        response_json = json.loads(chunks[0])
        assert response_json.get("model") == expected_llm
    else:
        response_json = response.json()
        assert response_json.get("model") == expected_llm
