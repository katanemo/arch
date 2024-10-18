import os
import app.commons.globals as glb

from transformers import AutoTokenizer, AutoModel, pipeline
from optimum.onnxruntime import (
    ORTModelForFeatureExtraction,
    ORTModelForSequenceClassification,
)
import app.commons.utilities as utils
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from optimum.intel import OVModelForSequenceClassification


logger = utils.get_model_server_logger()


def get_embedding_model(
    model_name=os.getenv("MODELS", "katanemo/bge-large-en-v1.5"),
):
    logger.info("Loading Embedding Model...")

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
    model_name=os.getenv("ZERO_SHOT_MODELS", "katanemo/bart-large-mnli"),
):
    logger.info("Loading Zero-shot Model...")

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


def get_prompt_guard(model_name):
    logger.info("Loading Guard Model...")

    if glb.DEVICE == "cpu":
        model_class = OVModelForSequenceClassification
    else:
        model_class = AutoModelForSequenceClassification

    prompt_guard = {
        "device": glb.DEVICE,
        "model_name": model_name,
        "tokenizer": AutoTokenizer.from_pretrained(model_name, trust_remote_code=True),
        "model": model_class.from_pretrained(
            model_name, device_map=glb.DEVICE, low_cpu_mem_usage=True
        ),
    }

    return prompt_guard
