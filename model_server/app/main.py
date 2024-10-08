import os
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from app.load_models import (
    load_transformers,
    load_guard_model,
    load_zero_shot_models,
    get_device,
)
import os
from app.utils import GuardHandler, split_text_into_chunks, load_yaml_config, get_model_server_logger
import torch
import yaml
import string
import time
import logging
from app.arch_fc.arch_fc import chat_completion as arch_fc_chat_completion, ChatMessage
import os.path


logger = get_model_server_logger()
logger.info(f"Devices Avialble: {get_device()}")

transformers = load_transformers()
zero_shot_models = load_zero_shot_models()
guard_model_config = load_yaml_config("guard_model_config.yaml")

mode = os.getenv("MODE", "cloud")
logger.info(f"Serving model mode: {mode}")
if mode not in ["cloud", "local-gpu", "local-cpu"]:
    raise ValueError(f"Invalid mode: {mode}")
if mode == "local-cpu":
    hardware = "cpu"
else:
    hardware = "gpu" if torch.cuda.is_available() else "cpu"

jailbreak_model = load_guard_model(guard_model_config["jailbreak"][hardware], hardware)
guard_handler = GuardHandler(toxic_model=None, jailbreak_model=jailbreak_model)

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

    start = time.time()
    logger.info(f"Embedding Call Start Time: {time.time()}")
    embeddings = transformers[req.model].encode([req.input])
    logger.info(f"Embedding Call Complete Time: {time.time()-start}")
    data = []

    for embedding in embeddings.tolist():
        data.append({"object": "embedding", "embedding": embedding, "index": len(data)})

    usage = {
        "prompt_tokens": 0,
        "total_tokens": 0,
    }
    return {"data": data, "model": req.model, "object": "list", "usage": usage}

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
    start = time.time()
    if req.task in ["both", "toxic", "jailbreak"]:
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
    end = time.time()
    logger.info(f"Time taken for Guard: {end - start}")
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


class HallucinationRequest(BaseModel):
    prompt: str
    parameters: dict
    model: str


@app.post("/hallucination")
async def hallucination(req: HallucinationRequest, res: Response):
    """
    Hallucination API, take input as text and return the prediction of hallucination for each parameter
    parameters: dictionary of parameters and values
        example     {"name": "John", "age": "25"}
    prompt: input prompt from the user
    """
    if req.model not in zero_shot_models:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    classifier = zero_shot_models[req.model]
    candidate_labels = [f"{k} is {v}" for k, v in req.parameters.items()]
    hypothesis_template = "{}"
    result = classifier(
        req.prompt,
        candidate_labels=candidate_labels,
        hypothesis_template=hypothesis_template,
        multi_label=True,
    )
    result_score = result["scores"]
    result_params = {k[0]: s for k, s in zip(req.parameters.items(), result_score)}
    logger.info(f"hallucination result: {result_params}")

    return {
        "params_scores": result_params,
        "model": req.model,
    }


@app.post("/v1/chat/completions")
async def chat_completion(req: ChatMessage, res: Response):
    result = await arch_fc_chat_completion(req, res)
    return result
