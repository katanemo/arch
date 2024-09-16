import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import (
    load_ner_models,
    load_transformers,
    load_toxic_model,
    load_jailbreak_model,
)
from datetime import date, timedelta
from utils import is_intel_cpu, GuardHandler
import json

transformers = load_transformers()
ner_models = load_ner_models()


if is_intel_cpu():
    hardware_config = "intel_cpu"
else:
    hardware_config = "non_intel_cpu"

guard_model_config = json.loads("guard_model_config.json")
toxic_model = load_toxic_model(
    guard_model_config["toxic"][hardware_config], hardware_config
)
jailbreak_model = load_jailbreak_model(
    guard_model_config["jailbreak"][hardware_config], hardware_config
)
guard_handler = GuardHandler(toxic_model, jailbreak_model, hardware_config)

app = FastAPI()


class EmbeddingRequest(BaseModel):
    input: str
    model: str


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/models")
async def models():
    models = []

    for model in transformers.keys():
        models.append({"id": model, "object": "model"})

    return {"data": models, "object": "list"}


@app.post("/embeddings")
async def embedding(req: EmbeddingRequest, res: Response):
    if req.model not in transformers:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    embeddings = transformers[req.model].encode([req.input])

    data = []

    for embedding in embeddings.tolist():
        data.append({"object": "embedding", "embedding": embedding, "index": len(data)})

    usage = {
        "prompt_tokens": 0,
        "total_tokens": 0,
    }
    return {"data": data, "model": req.model, "object": "list", "usage": usage}


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


class GuardRequest(BaseModel):
    input: str
    model: str


@app.post("/guard")
async def guard(req: GuardRequest, res: Response):
    result = guard_handler.guard_predict(req.input)
    return result


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
        min_temp = random.randrange(50, 90)
        max_temp = random.randrange(min_temp + 5, min_temp + 20)
        weather_forecast["temperature"].append(
            {
                "date": str(date.today() + timedelta(days=i)),
                "temperature": {"min": min_temp, "max": max_temp},
            }
        )

    return weather_forecast
