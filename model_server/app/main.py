import time
import torch
import app.commons.utilities as utils
import app.commons.globals as glb
import app.prompt_guard.model_utils as guard_utils

from typing import List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, Response, HTTPException
from app.function_calling.model_utils import ChatMessage

from app.commons.constants import embedding_model, zero_shot_model, arch_guard_handler
from app.function_calling.model_utils import (
    chat_completion as arch_function_chat_completion,
)
from unittest.mock import patch

logger = utils.get_model_server_logger()

logger.info(f"Ready to serve traffic. available device: {glb.DEVICE}")

app = FastAPI()


class EmbeddingRequest(BaseModel):
    input: str
    model: str


class GuardRequest(BaseModel):
    input: str
    task: str


class ZeroShotRequest(BaseModel):
    input: str
    labels: List[str]
    model: str


class HallucinationRequest(BaseModel):
    prompt: str
    parameters: Dict
    model: str


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/models")
async def models():
    return {
        "object": "list",
        "data": [{"id": embedding_model["model_name"], "object": "model"}],
    }


@app.post("/embeddings")
async def embedding(req: EmbeddingRequest, res: Response):
    logger.info(f"Embedding req: {req}")

    if req.model != embedding_model["model_name"]:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    start_time = time.perf_counter()

    encoded_input = embedding_model["tokenizer"](
        req.input, padding=True, truncation=True, return_tensors="pt"
    ).to(glb.DEVICE)

    with torch.no_grad():
        embeddings = embedding_model["model"](**encoded_input)
        embeddings = embeddings[0][:, 0]
        embeddings = (
            torch.nn.functional.normalize(embeddings, p=2, dim=1).detach().cpu().numpy()
        )

    logger.info(f"Embedding Call Complete Time: {time.perf_counter()-start_time}")

    data = [
        {"object": "embedding", "embedding": embedding, "index": index + 1}
        for index, embedding in enumerate(embeddings.tolist())
    ]

    usage = {
        "prompt_tokens": 0,
        "total_tokens": 0,
    }

    return {"data": data, "model": req.model, "object": "list", "usage": usage}


@app.post("/guard")
async def guard(req: GuardRequest, res: Response, max_num_words=300):
    """
    Take input as text and return the prediction of toxic and jailbreak
    """

    if req.task in ["both", "toxic", "jailbreak"]:
        arch_guard_handler.task = req.task
    else:
        raise NotImplementedError(f"{req.task} is not supported!")

    start_time = time.perf_counter()

    if len(req.input.split()) < max_num_words:
        guard_result = arch_guard_handler.guard_predict(req.input)
    else:
        # text is long, split into chunks
        chunks = guard_utils.split_text_into_chunks(req.input)

        guard_result = {
            "jailbreak_prob": [],
            "time": 0,
            "jailbreak_verdict": False,
            "toxic_sentence": [],
            "jailbreak_sentence": [],
        }

        for chunk in chunks:
            chunk_result = arch_guard_handler.guard_predict(chunk)
            guard_result["time"] += chunk_result["time"]
            if chunk_result[f"{arch_guard_handler.task}_verdict"]:
                guard_result[f"{arch_guard_handler.task}_verdict"] = True
                guard_result[f"{arch_guard_handler.task}_sentence"].append(
                    chunk_result[f"{arch_guard_handler.task}_sentence"]
                )
                guard_result[f"{arch_guard_handler.task}_prob"].append(
                    chunk_result[f"{arch_guard_handler.task}_prob"].item()
                )

    logger.info(f"Time taken for Guard: {time.perf_counter() - start_time}")

    return guard_result


@app.post("/zeroshot")
async def zeroshot(req: ZeroShotRequest, res: Response):
    logger.info(f"zero-shot request: {req}")

    if req.model != zero_shot_model["model_name"]:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    classifier = zero_shot_model["pipeline"]

    label_map = utils.get_label_map(req.labels)

    start_time = time.perf_counter()

    predictions = classifier(
        req.input, candidate_labels=list(label_map.keys()), multi_label=True
    )

    logger.info(f"zero-shot taking {time.perf_counter() - start_time} seconds")

    predicted_class = label_map[predictions["labels"][0]]
    predicted_score = predictions["scores"][0]

    scores = {
        label_map[label]: score
        for label, score in zip(predictions["labels"], predictions["scores"])
    }

    predicted_class = label_map[predictions["labels"][0]]

    return {
        "predicted_class": predicted_class,
        "predicted_class_score": predicted_score,
        "scores": scores,
        "model": req.model,
    }


@app.post("/hallucination")
@patch("app.loader.glb.DEVICE", "cpu")  # Mock the device to 'cpu'
async def hallucination(req: HallucinationRequest, res: Response):
    """
    Take input as text and return the prediction of hallucination for each parameter
    """
    logger.info(f"hallucination request: {req}")
    if req.model != zero_shot_model["model_name"]:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    start_time = time.perf_counter()
    classifier = zero_shot_model["pipeline"]

    if "messages" in req.parameters:
        req.parameters.pop("messages")

    candidate_labels = {f"{k} is {v}": k for k, v in req.parameters.items()}

    predictions = classifier(
        req.prompt,
        candidate_labels=list(candidate_labels.keys()),
        hypothesis_template="{}",
        multi_label=True,
    )

    params_scores = {
        candidate_labels[label]: score
        for label, score in zip(predictions["labels"], predictions["scores"])
    }

    logger.info(
        f"hallucination time cost: {params_scores}, taking {time.perf_counter() - start_time} seconds"
    )

    return {
        "params_scores": params_scores,
        "model": req.model,
    }


@app.post("/v1/chat/completions")
async def chat_completion(req: ChatMessage, res: Response):
    result = await arch_function_chat_completion(req, res)
    return result
