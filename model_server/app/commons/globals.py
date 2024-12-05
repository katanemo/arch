import app.commons.utilities as utils

from openai import OpenAI
from app.commons.constants import *
from app.model_handler.function_calling import ArchIntentHandler, ArchFunctionHandler
from app.model_handler.guardrails import get_guardrail_handler


logger = utils.get_model_server_logger()


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
