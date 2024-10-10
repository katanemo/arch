import os
import app.commons.globals as glb

from transformers import AutoTokenizer, AutoModel, pipeline
from optimum.onnxruntime import (
    ORTModelForFeatureExtraction,
    ORTModelForSequenceClassification,
)


def get_embedding_model(
    model_name=os.getenv("MODELS", "katanemo/bge-large-en-v1.5"),
):
    print("Loading Embedding Model...")

    if glb.DEVICE != "cuda":
        model = ORTModelForFeatureExtraction.from_pretrained(
            model_name, file_name="onnx/model.onnx"
        )
    else:
        model = AutoModel.from_pretrained(model_name, device_map=glb.DEVICE)

    embedding_model = {
        "model_name": model_name,
        "tokenizer": AutoTokenizer.from_pretrained(model_name, trust_remote_code=True),
        "model": model,
    }

    return embedding_model


def get_zero_shot_model(
    model_name=os.getenv("ZERO_SHOT_MODELS", "katanemo/deberta-base-nli"),
):
    print("Loading Zero-shot Model...")

    if glb.DEVICE != "cuda":
        model = ORTModelForSequenceClassification.from_pretrained(
            model_name, file_name="onnx/model.onnx"
        )
    else:
        model = model_name

    zero_shot_model = {
        "model_name": model_name,
        "tokenizer": AutoTokenizer.from_pretrained(model_name),
        "model": model,
    }

    zero_shot_model["pipeline"] = pipeline(
        "zero-shot-classification",
        model=zero_shot_model["model"],
        tokenizer=zero_shot_model["tokenizer"],
        device=glb.DEVICE,
    )

    return zero_shot_model


def get_prompt_guard(model_name, hardware_config="cpu"):
    print("Loading Guard Model...")

    if hardware_config == "cpu":
        from optimum.intel import OVModelForSequenceClassification

        device = "cpu"
        model_class = OVModelForSequenceClassification
    elif hardware_config == "gpu":
        import torch
        from transformers import AutoModelForSequenceClassification

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_class = AutoModelForSequenceClassification

    prompt_guard = {
        "hardware_config": hardware_config,
        "device": device,
        "model_name": model_name,
        "tokenizer": AutoTokenizer.from_pretrained(model_name, trust_remote_code=True),
        "model": model_class.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        ),
    }

    return prompt_guard
