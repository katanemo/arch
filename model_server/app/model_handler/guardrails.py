import time
import torch
import numpy as np
import app.commons.utilities as utils

from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from optimum.intel import OVModelForSequenceClassification


class GuardRequest(BaseModel):
    input: str
    task: str


class ArchGuardHanlder:
    def __init__(self, model_dict):
        self.model = model_dict["model"]
        self.tokenizer = model_dict["tokenizer"]
        self.device = model_dict["device"]

        self.support_tasks = {"jailbreak": {"positive_class": 2, "threshold": 0.5}}

    def _split_text_into_chunks(self, text, max_num_words=300):
        """
        Split the text into chunks of `max_num_words` words
        """
        words = text.split()  # Split text into words

        chunks = [
            " ".join(words[i : i + max_num_words])
            for i in range(0, len(words), max_num_words)
        ]

        return chunks

    @staticmethod
    def softmax(x):
        return np.exp(x) / np.exp(x).sum(axis=0)

    def _predict_text(self, task, text, max_length=512):
        inputs = self.tokenizer(
            text, truncation=True, max_length=max_length, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            logits = self.model(**inputs).logits.cpu().detach().numpy()[0]
            prob = ArchGuardHanlder.softmax(logits)[
                self.support_tasks[task]["positive_class"]
            ]

        if prob > self.support_tasks[task]["threshold"]:
            verdict = True
            sentence = text
        else:
            verdict = False
            sentence = None

        result_dict = {
            "prob": prob.item(),
            "verdict": verdict,
            "sentence": sentence,
        }

        return result_dict

    def predict(self, req: GuardRequest, max_num_words=300):
        """
        Note: currently only support jailbreak check
        """

        if req.task not in self.support_tasks:
            raise NotImplementedError(f"{req.task} is not supported!")

        guard_result = {
            "prob": [],
            "verdict": False,
            "sentence": [],
        }

        start_time = time.perf_counter()

        if len(req.input.split()) < max_num_words:
            guard_result = self._predict_text(req.task, req.input)
        else:
            # split into chunks if text is long
            text_chunks = self._split_text_into_chunks(req.input)

            for chunk in text_chunks:
                chunk_result = self._predict_text(req.task, chunk)
                if chunk_result["verdict"]:
                    guard_result["verdict"] = True
                    guard_result["sentence"].append(chunk_result["sentence"])
                    guard_result["prob"].append(chunk_result["prob"].item())

        guard_result["latency"] = time.perf_counter() - start_time

        return guard_result


def get_guardrail_handler(device: str = None):
    if device is None:
        device = utils.get_device()

    model_class, model_name = None, None
    if device == "cpu":
        model_class = OVModelForSequenceClassification
        model_name = "katanemo/Arch-Guard-cpu"
    else:
        model_class = AutoModelForSequenceClassification
        model_name = "katanemo/Arch-Guard"

    guardrail_dict = {
        "device": device,
        "model_name": model_name,
        "tokenizer": AutoTokenizer.from_pretrained(model_name, trust_remote_code=True),
        "model": model_class.from_pretrained(
            model_name, device_map=device, low_cpu_mem_usage=True
        ),
    }

    return ArchGuardHanlder(model_dict=guardrail_dict)
