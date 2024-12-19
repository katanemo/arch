import json
import os
import pytest
import requests
from deepdiff import DeepDiff
import logging
import yaml

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MODEL_SERVER_ENDPOINT = os.getenv(
    "MODEL_SERVER_ENDPOINT", "http://localhost:51000/function_calling"
)

# Load test data from YAML file
script_dir = os.path.dirname(__file__)

# Construct the full path to the YAML file
yaml_file_path = os.path.join(script_dir, "test_hallucination_data.yaml")

# Load test data from YAML file
with open(yaml_file_path, "r") as file:
    test_data_yaml = yaml.safe_load(file)


@pytest.mark.parametrize(
    "test_data",
    [
        pytest.param(test_case, id=test_case["id"])
        for test_case in test_data_yaml["test_cases"]
    ],
)
def test_model_server(test_data):
    input = test_data["input"]
    expected = test_data["expected"]

    response = requests.post(MODEL_SERVER_ENDPOINT, json=input)
    assert response.status_code == 200
    # print(json.dumps(response.json()))
    # ensure that response is json
    assert response.headers["content-type"] == "application/json"
    response_json = response.json()
    assert response_json
    metadata = response_json.get("metadata", [])
    assert (metadata["hallucination"].lower() == "true") == expected[0]["hallucination"]
    assert (metadata["prompt_prefilling"].lower() == "true") == expected[0][
        "prompt_prefilling"
    ]
