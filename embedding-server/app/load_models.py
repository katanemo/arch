import os
import sentence_transformers
from gliner import GLiNER
import onnxruntime as ort

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

def load_toxic_model(model_name = os.getenv("TOXIC_MODELS", "katanemolabs/toxic-onnx-quantized")):
    opts = ort.SessionOptions()
    
    toxic_model = {}
    toxic_model['tokenizer'] = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    toxic_model['model_name'] = model_name
    toxic_model['model'] = ort.InferenceSession(model_name, opts, providers=["CPUExecutionProvider"])
    toxic_model['positive_class'] = 1
    
    return toxic_model

def load_jailbreak_model(model_name = os.getenv("JAILBREAK_MODELS", "katanemolabs/jailbreak-onnx-quantized")):
    opts = ort.SessionOptions()
    
    jailbreak_model = {}
    jailbreak_model['tokenizer'] = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    jailbreak_model['model_name'] = model_name
    jailbreak_model['model'] = ort.InferenceSession(model_name, opts, providers=["CPUExecutionProvider"])
    jailbreak_model['positive_class'] = 2
    
    return jailbreak_model