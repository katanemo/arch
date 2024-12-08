import src.commons.utilities as utils

from openai import OpenAI
from src.commons.constants import *
from src.core.function_calling import ArchIntentHandler, ArchFunctionHandler
from src.core.guardrails import get_guardrail_handler


logger = utils.get_model_server_logger()


# Define the client
ARCH_ENDPOINT = "https://api.fc.archgw.com/v1"
ARCH_API_KEY = "EMPTY"
ARCH_CLIENT = OpenAI(base_url=ARCH_ENDPOINT, api_key=ARCH_API_KEY)


# Define model handlers
handler_map = {
    "Arch-Intent": ArchIntentHandler(
        ARCH_CLIENT,
        ARCH_INTENT_MODEL_ALIAS,
        ARCH_INTENT_TASK_PROMPT,
        ARCH_INTENT_TOOL_PROMPT_TEMPLATE,
        ARCH_INTENT_FORMAT_PROMPT,
        ARCH_INTENT_INSTRUCTION,
        **ARCH_INTENT_GENERATION_CONFIG,
    ),
    "Arch-Function": ArchFunctionHandler(
        ARCH_CLIENT,
        ARCH_FUNCTION_MODEL_ALIAS,
        ARCH_FUNCTION_TASK_PROMPT,
        ARCH_FUNCTION_TOOL_PROMPT_TEMPLATE,
        ARCH_FUNCTION_FORMAT_PROMPT,
        **ARCH_FUNCTION_GENERATION_CONFIG,
    ),
    "Arch-Guard": get_guardrail_handler(),
}
