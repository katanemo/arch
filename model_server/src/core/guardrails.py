import time
import torch
import numpy as np
import src.commons.utils as utils
from transformers import AutoTokenizer
from src.core.model_utils import GuardRequest, GuardResponse
from optimum.intel import OVModelForSequenceClassification
from transformers import AutoModelForSequenceClassification


class ArchGuardHanlder:
    def __init__(self, model_dict):
        """
        Initializes the ArchGuardHanlder with the given model dictionary.

        Args:
            model_dict (dict): A dictionary containing the model, tokenizer, and device information.
        """

        self.model = model_dict["model"]
        self.model_name = model_dict["model_name"]
        self.tokenizer = model_dict["tokenizer"]
        self.device = model_dict["device"]

        self.support_tasks = {"jailbreak": {"positive_class": 2, "threshold": 0.5}}

    def _split_text_into_chunks(self, text, max_num_words=300):
        """
        Splits the input text into chunks of up to `max_num_words` words.

        Args:
            text (str): The input text to be split.
            max_num_words (int, optional): The maximum number of words in each chunk. Defaults to 300.

        Returns:
            List[str]: A list of text chunks.
        """

        words = text.split()

        chunks = [
            " ".join(words[i : i + max_num_words])
            for i in range(0, len(words), max_num_words)
        ]

        return chunks

    @staticmethod
    def softmax(x):
        """
        Computes the softmax of the input array.

        Args:
            x (np.ndarray): The input array.

        Returns:
            np.ndarray: The softmax of the input.
        """
        return np.exp(x) / np.exp(x).sum(axis=0)

    def _predict_text(self, task, text, max_length=512) -> GuardResponse:
        """
        Predicts the result for the provided text for a specific task.

        Args:
            task (str): The task to perform (e.g., "jailbreak").
            text (str): The input text to classify.
            max_length (int, optional): The maximum length for tokenization. Defaults to 512.

        Returns:
            GuardResponse: A GuardResponse object containing the prediction.
        """

        inputs = self.tokenizer(
            text, truncation=True, max_length=max_length, return_tensors="pt"
        ).to(self.device)

        start_time = time.perf_counter()

        with torch.no_grad():
            logits = self.model(**inputs).logits.cpu().detach().numpy()[0]
            prob = ArchGuardHanlder.softmax(logits)[
                self.support_tasks[task]["positive_class"]
            ]

        latency = time.perf_counter() - start_time

        if prob > self.support_tasks[task]["threshold"]:
            verdict = True
            sentence = text
        else:
            verdict = False
            sentence = None

        return GuardResponse(
            prob=[prob.item()], verdict=verdict, sentence=[sentence], latency=latency
        )

    def predict(self, req: GuardRequest, max_num_words=300) -> GuardResponse:
        """
        Makes a prediction based on the GuardRequest input.

        Args:
            req (GuardRequest): The GuardRequest object containing the input text and task.
            max_num_words (int, optional): The maximum number of words in each chunk if splitting is needed. Defaults to 300.

        Returns:
            GuardResponse: A GuardResponse object containing the prediction.

        Note:
            currently only support jailbreak check
        """

        if req.task not in self.support_tasks:
            raise NotImplementedError(f"{req.task} is not supported!")

        if len(req.input.split()) < max_num_words:
            return self._predict_text(req.task, req.input)
        else:
            # split into chunks if text is long
            text_chunks = self._split_text_into_chunks(req.input)

            prob, verdict, sentence, latency = [], False, [], 0

            for chunk in text_chunks:
                chunk_result = self._predict_text(req.task, chunk)

                if chunk_result.verdict:
                    prob.append(chunk_result.prob[0])
                    verdict = True
                    sentence.append(chunk_result.sentence[0])
                    latency += chunk_result.latency

            return GuardResponse(
                prob=prob, verdict=verdict, sentence=sentence, latency=latency
            )


def get_guardrail_handler(device: str = None):
    """
    Initializes and returns an instance of ArchGuardHanlder based on the specified device.

    Args:
        device (str, optional): The device to use for model inference (e.g., "cpu" or "cuda"). Defaults to None.

    Returns:
        ArchGuardHanlder: An instance of ArchGuardHanlder configured for the specified device.
    """

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
