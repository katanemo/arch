import os
import sentence_transformers

def load_transformers(models = os.getenv("MODELS", "sentence-transformers/all-MiniLM-L6-v2")):
    transformers = {}

    for model in models.split(','):
        transformers[model] = sentence_transformers.SentenceTransformer(model)

    return transformers
