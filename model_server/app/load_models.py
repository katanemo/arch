import os
import sentence_transformers
from gliner import GLiNER
from transformers import AutoTokenizer, pipeline
import sqlite3
from employee_data_generator import generate_employee_data
from network_data_generator import (
    generate_device_data,
    generate_interface_stats_data,
    generate_flow_data,
)


def load_transformers(models=os.getenv("MODELS", "BAAI/bge-large-en-v1.5")):
    transformers = {}

    for model in models.split(","):
        transformers[model] = sentence_transformers.SentenceTransformer(model)

    return transformers


def load_ner_models(models=os.getenv("NER_MODELS", "urchade/gliner_large-v2.1")):
    ner_models = {}

    for model in models.split(","):
        ner_models[model] = GLiNER.from_pretrained(model)

    return ner_models


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

    for model in models.split(","):
        zero_shot_models[model] = pipeline("zero-shot-classification", model=model)

    return zero_shot_models


def load_sql():
    # Example Usage
    conn = sqlite3.connect(":memory:")

    # create and load the employees table
    generate_employee_data(conn)

    # create and load the devices table
    device_data = generate_device_data(conn)

    # create and load the interface_stats table
    generate_interface_stats_data(conn, device_data)

    # create and load the flow table
    generate_flow_data(conn, device_data)

    return conn
