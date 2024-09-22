import os
import sentence_transformers
from gliner import GLiNER
from transformers import pipeline
import sqlite3
from employee_data_generator import generate_employee_data, generate_certifications, generate_salary_history, generate_project_data
from network_data_generator import generate_device_data, generate_interface_stats_data, generate_flow_data

def load_transformers(models = os.getenv("MODELS", "BAAI/bge-large-en-v1.5")):
    transformers = {}

    for model in models.split(','):
        transformers[model] = sentence_transformers.SentenceTransformer(model)

    return transformers

def load_ner_models(models = os.getenv("NER_MODELS", "urchade/gliner_large-v2.1")):
    ner_models = {}

    for model in models.split(','):
        ner_models[model] = GLiNER.from_pretrained(model)

    return ner_models

def load_zero_shot_models(models = os.getenv("ZERO_SHOT_MODELS", "tasksource/deberta-base-long-nli")):
    zero_shot_models = {}

    for model in models.split(','):
        zero_shot_models[model] = pipeline("zero-shot-classification",model=model)

    return zero_shot_models

def load_sql():
    # Example Usage
    conn = sqlite3.connect(':memory:')

    # create and load the employees table
    generate_employee_data(conn)

    # create and load the devices table
    device_data = generate_device_data(conn)

    # create and load the interface_stats table
    generate_interface_stats_data(conn, device_data)

    # create and load the flow table
    generate_flow_data(conn, device_data)


    return conn
