from unittest.mock import patch, MagicMock
from src.core.guardrails import get_guardrail_handler

# Mock constants
arch_guard_model_type = {
    "cpu": "katanemo/Arch-Guard-cpu",
    "cuda": "katanemo/Arch-Guard",
    "mps": "katanemo/Arch-Guard",
}


# [TODO] Review: check the following code to test under `cpu`, `cuda`, and `mps`
# Test for `get_guardrail_handler()` function on `cpu`
@patch("src.core.guardrails.AutoTokenizer.from_pretrained")
@patch("src.core.guardrails.OVModelForSequenceClassification.from_pretrained")
@patch("src.core.guardrails.AutoModelForSequenceClassification.from_pretrained")
def test_guardrail_handler_on_cpu(mock_auto_model, mock_ov_model, mock_tokenizer):
    device = "cpu"

    mock_ov_model.return_value = MagicMock()
    mock_tokenizer.return_value = MagicMock()

    guardrail = get_guardrail_handler(device=device)

    mock_tokenizer.assert_called_once_with(guardrail.model_name, trust_remote_code=True)

    mock_ov_model.assert_called_once_with(
        guardrail.model_name,
        device_map=device,
        low_cpu_mem_usage=True,
    )


# Test for `get_guardrail_handler()` function on `cuda`
@patch("src.core.guardrails.AutoTokenizer.from_pretrained")
@patch("src.core.guardrails.OVModelForSequenceClassification.from_pretrained")
@patch("src.core.guardrails.AutoModelForSequenceClassification.from_pretrained")
def test_guardrail_handler_on_cuda(mock_auto_model, mock_ov_model, mock_tokenizer):
    device = "cuda"

    mock_auto_model.return_value = MagicMock()
    mock_tokenizer.return_value = MagicMock()

    guardrail = get_guardrail_handler(device=device)

    mock_tokenizer.assert_called_once_with(guardrail.model_name, trust_remote_code=True)

    mock_auto_model.assert_called_once_with(
        guardrail.model_name,
        device_map=device,
        low_cpu_mem_usage=True,
    )


# Test for `get_guardrail_handler()` function on `mps`
@patch("src.core.guardrails.AutoTokenizer.from_pretrained")
@patch("src.core.guardrails.OVModelForSequenceClassification.from_pretrained")
@patch("src.core.guardrails.AutoModelForSequenceClassification.from_pretrained")
def test_guardrail_handler_on_mps(mock_auto_model, mock_ov_model, mock_tokenizer):
    device = "mps"

    mock_auto_model.return_value = MagicMock()
    mock_tokenizer.return_value = MagicMock()

    guardrail = get_guardrail_handler(device=device)

    mock_tokenizer.assert_called_once_with(guardrail.model_name, trust_remote_code=True)

    mock_auto_model.assert_called_once_with(
        guardrail.model_name,
        device_map=device,
        low_cpu_mem_usage=True,
    )
