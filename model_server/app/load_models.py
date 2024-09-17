import os
import sentence_transformers
from gliner import GLiNER
from transformers import pipeline
import sqlite3
import pandas as pd

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
    data = pd.read_csv("Employee_Data.csv")
    conn = sqlite3.connect(':memory:')
    data.to_sql('employees', conn, index=False)
    return conn

