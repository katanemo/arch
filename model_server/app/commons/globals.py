import app.commons.utilities as utils

from app.commons.constants import *
from app.model_handler.function_calling import ArchIntentHandler, ArchFunctionHandler
from app.model_handler.guardrails import ArchGuardHanlder

from transformers import AutoTokenizer, AutoModelForSequenceClassification
from optimum.intel import OVModelForSequenceClassification
from openai import OpenAI


logger = utils.get_model_server_logger()


def get_guardrail_handler():
    device = utils.get_device()

    model_class, model_name = None, None
    if device == "cpu":
        model_class = OVModelForSequenceClassification
        model_name = "katanemo/Arch-Guard-cpu"
    else:
        model_class = AutoModelForSequenceClassification
        if device == "cuda":
            model_name = "katanemo/Arch-Guard"
        else:
            model_name = "katanemo/Arch-Guard"

    guardrail_dict = {
        "device": device,
        "model_name": model_name,
        "tokenizer": AutoTokenizer.from_pretrained(model_name, trust_remote_code=True),
        "model": model_class.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        ),
    }

    return ArchGuardHanlder(model_dict=guardrail_dict)


# Define the client
ARCH_CLIENT = OpenAI(base_url="https://api.fc.archgw.com/v1", api_key="EMPTY")


# Define model handlers
handler_map = {
    "Arch-Intent": ArchIntentHandler(
        ARCH_CLIENT,
        ARCH_INTENT_MODEL_ALIAS,
        ARCH_INTENT_TASK_PROMPT,
        ARCH_INTENT_TOOL_PROMPT,
        ARCH_INTENT_FORMAT_PROMPT,
        ARCH_INTENT_INSTRUCTION,
        **ARCH_INTENT_GENERATION_CONFIG,
    ),
    "Arch-Function": ArchFunctionHandler(
        ARCH_CLIENT,
        ARCH_FUNCTION_MODEL_ALIAS,
        ARCH_FUNCTION_TASK_PROMPT,
        ARCH_FUNCTION_TOOL_PROMPT,
        ARCH_FUNCTION_FORMAT_PROMPT,
        **ARCH_FUNCTION_GENERATION_CONFIG,
    ),
    "Arch-Guard": get_guardrail_handler(),
}
