import os
import pytest
from unittest.mock import patch, MagicMock
import app.commons.globals as glb
from app.loader import get_embedding_model, get_zero_shot_model, get_prompt_guard

# Mock constants
glb.DEVICE = "cpu"  # Adjust as needed for your test case
arch_guard_model_type = {
    "cpu": "katanemo/Arch-Guard-cpu",
    "cuda": "katanemo/Arch-Guard",
    "mps": "katanemo/Arch-Guard",
}


@pytest.fixture
def mock_env():
    # Mock environment variables
    os.environ["MODELS"] = "katanemo/bge-large-en-v1.5"
    os.environ["ZERO_SHOT_MODELS"] = "katanemo/bart-large-mnli"


# Test for get_embedding_model function
@patch("app.loader.ORTModelForFeatureExtraction.from_pretrained")
@patch("app.loader.AutoModel.from_pretrained")
@patch("app.loader.AutoTokenizer.from_pretrained")
def test_get_embedding_model(mock_tokenizer, mock_automodel, mock_ort_model, mock_env):
    mock_automodel.return_value = MagicMock()
    mock_ort_model.return_value = MagicMock()
    mock_tokenizer.return_value = MagicMock()

    embedding_model = get_embedding_model()

    # Assertions
    assert embedding_model["model_name"] == "katanemo/bge-large-en-v1.5"
    mock_tokenizer.assert_called_once_with(
        "katanemo/bge-large-en-v1.5", trust_remote_code=True
    )
    if glb.DEVICE != "cuda":
        mock_ort_model.assert_called_once_with(
            "katanemo/bge-large-en-v1.5", file_name="onnx/model.onnx"
        )
    else:
        mock_automodel.assert_called_once_with(
            "katanemo/bge-large-en-v1.5", device_map=glb.DEVICE
        )


# Test for get_zero_shot_model function
@patch("app.loader.ORTModelForSequenceClassification.from_pretrained")
@patch("app.loader.pipeline")
@patch("app.loader.AutoTokenizer.from_pretrained")
def test_get_zero_shot_model(mock_tokenizer, mock_pipeline, mock_ort_model, mock_env):
    mock_pipeline.return_value = MagicMock()
    mock_ort_model.return_value = MagicMock()
    mock_tokenizer.return_value = MagicMock()

    zero_shot_model = get_zero_shot_model()

    # Assertions
    assert zero_shot_model["model_name"] == "katanemo/bart-large-mnli"
    mock_tokenizer.assert_called_once_with("katanemo/bart-large-mnli")
    if glb.DEVICE != "cuda":
        mock_ort_model.assert_called_once_with(
            "katanemo/bart-large-mnli", file_name="onnx/model.onnx"
        )
    else:
        assert mock_pipeline.called_once()


# Test for get_prompt_guard function
@patch("app.loader.AutoTokenizer.from_pretrained")
@patch("app.loader.OVModelForSequenceClassification.from_pretrained")
@patch("app.loader.AutoModelForSequenceClassification.from_pretrained")
def test_get_prompt_guard(mock_auto_model, mock_ov_model, mock_tokenizer):
    # Mock model based on device
    if glb.DEVICE == "cpu":
        mock_ov_model.return_value = MagicMock()
    else:
        mock_auto_model.return_value = MagicMock()

    mock_tokenizer.return_value = MagicMock()

    prompt_guard = get_prompt_guard(arch_guard_model_type[glb.DEVICE])

    # Assertions
    assert prompt_guard["model_name"] == arch_guard_model_type[glb.DEVICE]
    mock_tokenizer.assert_called_once_with(
        arch_guard_model_type[glb.DEVICE], trust_remote_code=True
    )
    if glb.DEVICE == "cpu":
        mock_ov_model.assert_called_once_with(
            arch_guard_model_type[glb.DEVICE],
            device_map=glb.DEVICE,
            low_cpu_mem_usage=True,
        )
    else:
        mock_auto_model.assert_called_once_with(
            arch_guard_model_type[glb.DEVICE],
            device_map=glb.DEVICE,
            low_cpu_mem_usage=True,
        )
