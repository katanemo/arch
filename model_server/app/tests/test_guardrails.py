import os
import pytest
from unittest.mock import patch, MagicMock
import app.commons.globals as glb

# Mock constants
glb.DEVICE = "cpu"  # Adjust as needed for your test case
arch_guard_model_type = {
    "cpu": "katanemo/Arch-Guard-cpu",
    "cuda": "katanemo/Arch-Guard",
    "mps": "katanemo/Arch-Guard",
}


# [TODO] Review: update the following code to test under `cpu`, `cuda`, and `mps`
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
