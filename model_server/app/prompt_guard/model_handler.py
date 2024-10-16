import time
import torch
import app.prompt_guard.model_utils as model_utils


class ArchGuardHanlder:
    def __init__(self, model_dict, threshold=0.5):
        self.task = "jailbreak"
        self.positive_class = 2

        self.model = model_dict["model"]
        self.tokenizer = model_dict["tokenizer"]
        self.device = model_dict["device"]

        self.threshold = threshold

    def guard_predict(self, input_text, max_length=512):
        start_time = time.perf_counter()

        inputs = self.tokenizer(
            input_text, truncation=True, max_length=max_length, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            logits = self.model(**inputs).logits.cpu().detach().numpy()[0]
            prob = model_utils.softmax(logits)[self.positive_class]

        if prob > self.threshold:
            verdict = True
            sentence = input_text
        else:
            verdict = False
            sentence = None

        result_dict = {
            f"{self.task}_prob": prob.item(),
            f"{self.task}_verdict": verdict,
            f"{self.task}_sentence": sentence,
            "time": time.perf_counter() - start_time,
        }

        return result_dict
