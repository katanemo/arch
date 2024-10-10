import app.commons.globals as glb
import app.commons.utilities as utils
import app.loader as loader

from app.function_calling.model_handler import ArchFunctionHandler
from app.prompt_guard.model_handler import ArchGuardHanlder


arch_function_hanlder = ArchFunctionHandler()
arch_function_endpoint = "https://api.fc.archgw.com/v1"
arch_function_client = utils.get_client(arch_function_endpoint)
arch_function_generation_params = {
    "temperature": 0.2,
    "top_p": 1.0,
    "top_k": 50,
    "max_tokens": 512,
    "stop_token_ids": [151645],
}

arch_guard_model_type = {"cpu": "katanemo/Arch-Guard-cpu", "gpu": "katanemo/Arch-Guard"}


# Model definition
embedding_model = loader.get_embedding_model()
zero_shot_model = loader.get_zero_shot_model()

prompt_guard_dict = loader.get_prompt_guard(
    arch_guard_model_type[glb.HARDWARE], glb.HARDWARE
)

arch_guard_handler = ArchGuardHanlder(model_dict=prompt_guard_dict)
