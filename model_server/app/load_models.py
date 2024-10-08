import os
import sentence_transformers
from transformers import AutoTokenizer, pipeline
import sqlite3
import torch
from optimum.onnxruntime import ORTModelForFeatureExtraction, ORTModelForSequenceClassification  # type: ignore


def get_device():
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    return device


def load_transformers(model_name=os.getenv("MODELS", "katanemolabs/bge-large-en-v1.5-onnx")):
    transformers = {}
    device = get_device()
    transformers["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
    transformers["model"] = ORTModelForFeatureExtraction.from_pretrained(
        model_name, device_map = device
    )
    transformers["model_name"] = model_name

    return transformers


def load_guard_model(
    model_name,
    hardware_config="cpu",
):
    guard_model = {}
    guard_model["tokenizer"] = AutoTokenizer.from_pretrained(
        model_name, trust_remote_code=True
    )
    guard_model["model_name"] = model_name
    if hardware_config == "cpu":
        from optimum.intel import OVModelForSequenceClassification

        device = "cpu"
        guard_model["model"] = OVModelForSequenceClassification.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        )
    elif hardware_config == "gpu":
        from transformers import AutoModelForSequenceClassification
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        guard_model["model"] = AutoModelForSequenceClassification.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        )
    guard_model["device"] = device
    guard_model["hardware_config"] = hardware_config
    return guard_model


def load_zero_shot_models(
    model_name=os.getenv("ZERO_SHOT_MODELS", "katanemolabs/deberta-base-nli-onnx")
):
    zero_shot_model = {}
    device = get_device()
    zero_shot_model["model"] = ORTModelForSequenceClassification.from_pretrained(
        model_name
    )
    zero_shot_model["tokenizer"] = AutoTokenizer.from_pretrained(model_name)

    # create pipeline
    zero_shot_model["pipeline"] = pipeline(
        "zero-shot-classification",
        model=zero_shot_model["model"],
        tokenizer=zero_shot_model["tokenizer"],
        device=device,
    )
    zero_shot_model["model_name"] = model_name

    return zero_shot_model


if __name__ == "__main__":
    print(get_device())
