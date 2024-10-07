import os
import sentence_transformers
from transformers import AutoTokenizer, pipeline
import sqlite3
import torch


def get_device():
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    return device


def load_transformers(models=os.getenv("MODELS", "BAAI/bge-large-en-v1.5")):
    transformers = {}
    device = get_device()
    for model in models.split(","):
        transformers[model] = sentence_transformers.SentenceTransformer(
            model, device=device
        )

    return transformers


def load_guard_model(
    model_name,
    hardware_config="cpu",
):
    guard_mode = {}
    guard_mode["tokenizer"] = AutoTokenizer.from_pretrained(
        model_name, trust_remote_code=True
    )
    guard_mode["model_name"] = model_name
    if hardware_config == "cpu":
        from optimum.intel import OVModelForSequenceClassification

        device = "cpu"
        guard_mode["model"] = OVModelForSequenceClassification.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        )
    elif hardware_config == "gpu":
        from transformers import AutoModelForSequenceClassification
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        guard_mode["model"] = AutoModelForSequenceClassification.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        )
    guard_mode["device"] = device
    guard_mode["hardware_config"] = hardware_config
    return guard_mode


def load_zero_shot_models(
    models=os.getenv("ZERO_SHOT_MODELS", "tasksource/deberta-base-long-nli")
):
    zero_shot_models = {}
    device = get_device()
    for model in models.split(","):
        zero_shot_models[model] = pipeline(
            "zero-shot-classification", model=model, device=device
        )

    return zero_shot_models


if __name__ == "__main__":
    print(get_device())
