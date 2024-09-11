import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import load_ner_models, load_transformers, load_toxic_model, load_jailbreak_model
from datetime import date, timedelta
import torch
import torch.nn.functional as F

transformers = load_transformers()
ner_models = load_ner_models()
toxic_model = load_toxic_model()
jailbreak_model = load_jailbreak_model()


app = FastAPI()
def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()
    
class EmbeddingRequest(BaseModel):
  input: str
  model: str

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }

@app.get("/models")
async def models():
    models = []

    for model in transformers.keys():
        models.append({
            "id": model,
            "object": "model"
        })

    return {
        "data": models,
        "object": "list"
    }

@app.post("/embeddings")
async def embedding(req: EmbeddingRequest, res: Response):
    if req.model not in transformers:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    embeddings = transformers[req.model].encode([req.input])

    data = []

    for embedding in embeddings.tolist():
        data.append({
            "object": "embedding",
            "embedding": embedding,
            "index": len(data)
        })

    usage = {
        "prompt_tokens": 0,
        "total_tokens": 0,
    }
    return {
        "data": data,
        "model": req.model,
        "object": "list",
        "usage": usage
    }

class NERRequest(BaseModel):
  input: str
  labels: list[str]
  model: str


@app.post("/ner")
async def ner(req: NERRequest, res: Response):
    if req.model not in ner_models:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    model = ner_models[req.model]
    entities = model.predict_entities(req.input, req.labels)

    return {
        "data": entities,
        "model": req.model,
        "object": "list",
    }

class ToxicRequest(BaseModel):
  input: str
  model: str


@app.post("/toxic")
async def toxic(req: ToxicRequest, res: Response):
    if req.model != toxic_model['model_name']:
        raise HTTPException(status_code=400, detail="unknown toxic model: " + req.model)

    model = toxic_model['model']
    tokenizer = toxic_model['tokenizer']
    assert type(req.input) == str
    inputs = tokenizer(req.input, return_tensors="pt").to("cpu")

    feed = {'input_ids':inputs['input_ids'].numpy(),
            'attention_mask': inputs['attention_mask'].numpy(),
            'token_type_ids': inputs['token_type_ids'].numpy() }

    del inputs
    logits = model.run(["logits"], feed)[0]
    probabilities = softmax(logits)
    positive_class_probabilities = probabilities[:,toxic_model['positive_class']]
    verdict = "No"
    if positive_class_probabilities > 0.5:
        verdict = "Toxic"
    return {
        "probability": positive_class_probabilities,
        "verdict": verdict,
        "model": req.model,
    }

class JailBreakRequest(BaseModel):
  input: str
  model: str


@app.post("/jailbreak")
async def jailbreak(req: JailBreakRequest, res: Response):
    if req.model != jailbreak_model['model_name']:
        raise HTTPException(status_code=400, detail="unknown jail break model: " + req.model)

    model = jailbreak_model['model']
    tokenizer = jailbreak_model['tokenizer']
    assert type(req.input) == str
    inputs = tokenizer(req.input, return_tensors="pt").to("cpu")

    feed = {'input_ids':inputs['input_ids'].numpy(),
            'attention_mask': inputs['attention_mask'].numpy()}

    del inputs
    logits = model.run(["logits"], feed)[0]
    probabilities = softmax(logits)
    positive_class_probabilities = probabilities[:,jailbreak_model['positive_class']]
    verdict = "No"
    if positive_class_probabilities > 0.5:
        verdict = "Jailbreak"
    return {
        "probability": positive_class_probabilities,
        "verdict": verdict,
        "model": req.model,
    }

class WeatherRequest(BaseModel):
  city: str


@app.post("/weather")
async def weather(req: WeatherRequest, res: Response):

    weather_forecast = {
        "city": req.city,
        "temperature": [],
        "unit": "F",
    }
    for i in range(7):
       min_temp = random.randrange(50,90)
       max_temp = random.randrange(min_temp+5, min_temp+20)
       weather_forecast["temperature"].append({
           "date": str(date.today() + timedelta(days=i)),
           "temperature": {
              "min": min_temp,
              "max": max_temp
           }
       })

    return weather_forecast
