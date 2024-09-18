import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import (
    load_ner_models,
    load_transformers,
    load_toxic_model,
    load_jailbreak_model,
    load_zero_shot_models,
)
from datetime import date, timedelta
from utils import is_intel_cpu, GuardHandler, split_text_into_chunks
import json
import string
import torch
import yaml

transformers = load_transformers()
ner_models = load_ner_models()
zero_shot_models = load_zero_shot_models()

with open('bolt_config.yaml', 'r') as file:
    config = yaml.safe_load(file)
if is_intel_cpu():
    cpu = "intel_cpu"
else:
    cpu = "non_intel_cpu"
with open("guard_model_config.json") as f:
    guard_model_config = json.load(f)

if 'prompt_guards' in config.keys():
    if len(config['prompt_guards']['input_guards']) == 2:
        task = 'both'
        jailbreak_hardware = [item for item in config['model_host_preferences'] if item['name'] == 'jailbreak'][0]['host_preference'][0]
        toxic_hardware = [item for item in config['model_host_preferences'] if item['name'] == 'toxic'][0]['host_preference'][0]
        if jailbreak_hardware == 'cpu' or torch.cuda.is_available() == False:
            jailbreak_hardware = cpu
        if toxic_hardware == 'cpu' or torch.cuda.is_available() == False:
            toxic_hardware = cpu


        toxic_model = load_toxic_model(
            guard_model_config["toxic"][jailbreak_hardware], toxic_hardware
        )
        jailbreak_model = load_jailbreak_model(
            guard_model_config["jailbreak"][toxic_hardware], jailbreak_hardware
        )

    else:
        task = list(config['prompt_guards']['input_guards'].keys())[0]

        hardware = [item for item in config['model_host_preferences'] if item['name'] == task][0]['host_preference'][0]
        if hardware == 'cpu' or torch.cuda.is_available() == False:
            hardware = cpu
        if task == 'toxic':
            toxic_model = load_toxic_model(
                guard_model_config["toxic"][hardware], hardware
            )
            jailbreak_model = None
        elif task == 'jailbreak':
            jailbreak_model = load_jailbreak_model(
                guard_model_config["jailbreak"][hardware], hardware
            )
            toxic_model = None
    

guard_handler = GuardHandler(toxic_model, jailbreak_model)

app = FastAPI()


class EmbeddingRequest(BaseModel):
    input: str
    model: str


@app.get("/healthz")
async def healthz():
    import os

    print(os.getcwd())
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
    task: str


@app.post("/guard")
async def guard(req: GuardRequest, res: Response):
    """
    Guard API, take input as text and return the prediction of toxic and jailbreak
    result format: dictionary
            "toxic_prob": toxic_prob,
            "jailbreak_prob": jailbreak_prob,
            "time": end - start,
            "toxic_verdict": toxic_verdict,
            "jailbreak_verdict": jailbreak_verdict,
    """
    max_words = 300
    if req.task in ['both', 'toxic', 'jailbreak']:
        guard_handler.task = req.task
    if len(req.input.split()) < max_words:
        final_result = guard_handler.guard_predict(req.input)
    else:
        # text is long, split into chunks
        chunks = split_text_into_chunks(req.input)
        final_result = {
            "toxic_prob": [],
            "jailbreak_prob": [],
            "time": 0,
            "toxic_verdict": False,
            "jailbreak_verdict": False,
            "toxic_sentence": [],
            "jailbreak_sentence": [],
        }
        if guard_handler.task == "both":

            for chunk in chunks:
                result_chunk = guard_handler.guard_predict(chunk)
                final_result["time"] += result_chunk["time"]
                if result_chunk["toxic_verdict"]:
                    final_result["toxic_verdict"] = True
                    final_result["toxic_sentence"].append(
                        result_chunk["toxic_sentence"]
                    )
                    final_result["toxic_prob"].append(result_chunk["toxic_prob"].item())
                if result_chunk["jailbreak_verdict"]:
                    final_result["jailbreak_verdict"] = True
                    final_result["jailbreak_sentence"].append(
                        result_chunk["jailbreak_sentence"]
                    )
                    final_result["jailbreak_prob"].append(
                        result_chunk["jailbreak_prob"]
                    )
        else:
            task = guard_handler.task
            for chunk in chunks:
                result_chunk = guard_handler.guard_predict(chunk)
                final_result["time"] += result_chunk["time"]
                if result_chunk[f"{task}_verdict"]:
                    final_result[f"{task}_verdict"] = True
                    final_result[f"{task}_sentence"].append(
                        result_chunk[f"{task}_sentence"]
                    )
                    final_result[f"{task}_prob"].append(
                        result_chunk[f"{task}_prob"].item()
                    )
    return final_result


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
    predicted_classes = classifier(
        req.input, candidate_labels=labels_without_punctuations, multi_label=True
    )
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
        min_temp = random.randrange(50, 90)
        max_temp = random.randrange(min_temp + 5, min_temp + 20)
        weather_forecast["temperature"].append(
            {
                "date": str(date.today() + timedelta(days=i)),
                "temperature": {"min": min_temp, "max": max_temp},
            }
        )

    return weather_forecast
