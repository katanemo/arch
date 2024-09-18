import platform
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
import torch


def split_text_into_chunks(text, max_words=300):
    """
    Max number of tokens for tokenizer is 512
    Split the text into chunks of 300 words (as approximation for tokens)
    """
    words = text.split()  # Split text into words
    # Estimate token count based on word count (1 word ≈ 1 token)
    chunk_size = max_words  # Use the word count as an approximation for tokens
    chunks = [
        " ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)
    ]
    return chunks


def is_intel_cpu():
    try:
        # Check the system's platform
        system = platform.system()

        if system == "Windows":
            # For Windows, use the 'platform.processor()' method
            cpu_info = platform.processor()
        elif system == "Linux":
            # For Linux, read from /proc/cpuinfo
            with open("/proc/cpuinfo", "r") as f:
                cpu_info = f.read()
        elif system == "Darwin":  # macOS
            # For macOS, use 'platform.processor()' method
            cpu_info = platform.processor()
        else:
            return False  # Unsupported platform

        # Check if the CPU is from Intel
        return "Intel" in cpu_info

    except Exception as e:
        print(f"Error while checking CPU info: {e}")
        return False


# Example usage
if is_intel_cpu():
    print("This CPU is from Intel.")
else:
    print("This CPU is not from Intel.")


def softmax(x):
    return np.exp(x) / np.exp(x).sum(axis=0)


class PredictHandler:
    def __init__(
        self, model, tokenizer, device, task="toxic", hardware_config="intel_cpu"
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.task = task
        if self.task == "toxic":
            self.positive_class = 1
        elif self.task == "jailbreak":
            self.positive_class = 2
        self.hardware_config = hardware_config

    def predict(self, input_text):
        inputs = self.tokenizer(
            input_text, truncation=True, max_length=512, return_tensors="pt"
        ).to(self.device)
        with torch.no_grad():
            if self.hardware_config == "non_intel_cpu":

                feed = {
                    "input_ids": inputs["input_ids"].numpy(),
                    "attention_mask": inputs["attention_mask"].numpy(),
                }
                if self.task == "toxic":
                    feed["token_type_ids"] = inputs["token_type_ids"].numpy()

                del inputs
                logits = self.model.run(["logits"], feed)[0][0]
                del feed

            else:
                logits = self.model(**inputs).logits.numpy()[0]
                del inputs
        print(logits)
        probabilities = softmax(logits)
        print(probabilities)
        positive_class_probabilities = probabilities[self.positive_class]
        return positive_class_probabilities


class GuardHandler:
    def __init__(self, toxic_model, jailbreak_model):
        self.toxic_model = toxic_model
        self.jailbreak_model = jailbreak_model
        self.task = "both"
        if toxic_model is not None:
            self.toxic_handler = PredictHandler(
                toxic_model["model"],
                toxic_model["tokenizer"],
                toxic_model["device"],
                "toxic",
                toxic_model["hardware_config"],
            )
        else:
            self.task = "jailbreak"
        if jailbreak_model is not None:
            self.jailbreak_handler = PredictHandler(
                jailbreak_model["model"],
                jailbreak_model["tokenizer"],
                jailbreak_model["device"],
                "jailbreak",
                jailbreak_model["hardware_config"],
            )
        else:
            self.task = "toxic"

    def guard_predict(self, input_text):
        start = time.time()
        if self.task == "both":
            with ThreadPoolExecutor() as executor:

                toxic_thread = executor.submit(self.toxic_handler.predict, input_text)
                jailbreak_thread = executor.submit(
                    self.jailbreak_handler.predict, input_text
                )
                # Get results from both models
                toxic_prob = toxic_thread.result()
                jailbreak_prob = jailbreak_thread.result()
            end = time.time()
            if toxic_prob > 0.5:
                toxic_verdict = True
                toxic_sentence = input_text
            else:
                toxic_verdict = False
                toxic_sentence = None
            if jailbreak_prob > 0.5:
                jailbreak_verdict = True
                jailbreak_sentence = input_text
            else:
                jailbreak_verdict = False
                jailbreak_sentence = None
            result_dict = {
                "toxic_prob": toxic_prob.item(),
                "jailbreak_prob": jailbreak_prob.item(),
                "time": end - start,
                "toxic_verdict": toxic_verdict,
                "jailbreak_verdict": jailbreak_verdict,
                "toxic_sentence": toxic_sentence,
                "jailbreak_sentence": jailbreak_sentence,
            }
        else:
            if self.toxic_model is not None:
                prob = self.toxic_handler.predict(input_text)
            elif self.jailbreak_model is not None:
                prob = self.jailbreak_handler.predict(input_text)
            else:
                raise Exception("No model loaded")
            if prob > 0.5:
                verdict = True
                sentence = input_text
            else:
                verdict = False
                sentence = None
            result_dict = {
                f"{self.task}_prob": prob.item(),
                f"{self.task}_verdict": verdict,
                f"{self.task}_sentence": sentence,
            }
        return result_dict
