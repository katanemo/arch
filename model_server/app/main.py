import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import load_ner_models, load_transformers, load_zero_shot_models
from datetime import date, timedelta
import string

transformers = load_transformers()
ner_models = load_ner_models()
zero_shot_models = load_zero_shot_models()

app = FastAPI()

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

class ZeroShotRequest(BaseModel):
  input: str
  labels: list[str]
  model: str


def remove_punctuations(s, lower=True):
    s = s.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    s = " ".join(s.split())
    if lower:
        s = s.lower()
    return s


@app.post("/zeroshot")
async def zeroshot(req: ZeroShotRequest, res: Response):
    if req.model not in zero_shot_models:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    classifier = zero_shot_models[req.model]
    labels_without_punctuations = [remove_punctuations(label) for label in req.labels]
    predicted_classes = classifier(req.input, candidate_labels=labels_without_punctuations, multi_label=True)
    label_map = dict(zip(labels_without_punctuations, req.labels))

    orig_map = [label_map[label] for label in predicted_classes["labels"]]
    final_scores = dict(zip(orig_map, predicted_classes["scores"]))
    predicted_class = label_map[predicted_classes["labels"][0]]

    return {
        "predicted_class": predicted_class,
        "predicted_class_score": final_scores[predicted_class],
        "scores": final_scores,
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
