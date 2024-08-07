import os
import sentence_transformers
from gliner import GLiNER

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
