import platform
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
import torch


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
    """Compute softmax values for each sets of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


class PredictHandler:
    def __init__(
            self,
            model,
            tokenizer,
            device,
            task="toxic",
            hardware_config="intel_cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.task = "toxic"
        if self.task == "toxic":
            self.positive_class = 1
        elif self.task == "jailbreak":
            self.positive_class = 2
        self.hardware_config = hardware_config

    def predict(self, input_text):
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt").to(
            self.device)
        with torch.no_grad():
            if self.hardware_config == "non_intel_cpu":
                feed = {
                    "input_ids": inputs["input_ids"].numpy(),
                    "attention_mask": inputs["attention_mask"].numpy(),
                    "token_type_ids": inputs["token_type_ids"].numpy(),
                }

                del inputs
                logits = self.model.run(["logits"], feed)[0]
                del feed

            else:
                logits = self.model(**inputs).logits
                del inputs

        probabilities = softmax(logits)
        positive_class_probabilities = probabilities[:, self.positive_class]
        return positive_class_probabilities


class GuardHandler:
    def __init__(
            self,
            toxic_model,
            jailbreak_model,
            hardware_config="intel_cpu"):
        self.toxic_model = toxic_model
        self.jailbreak_model = jailbreak_model
        if toxic_model is not None:
            self.toxic_handler = PredictHandler(
                toxic_model["model"],
                toxic_model["tokenizer"],
                toxic_model["device"],
                "toxic",
                hardware_config,
            )
        else:
            self.single = True
        if jailbreak_model is not None:
            self.jailbreak_handler = PredictHandler(
                jailbreak_model["model"],
                jailbreak_model["tokenizer"],
                jailbreak_model["device"],
                "jailbreak",
                hardware_config,
            )
        else:
            self.single = True
        self.hardware_config = hardware_config

    def guard_predict(self, input_text):
        start = time.time()
        if not self.single:
            with ThreadPoolExecutor() as executor:

                toxic_thread = executor.submit(
                    self.toxic_handler.predict, input_text
                )
                jailbreak_thread = executor.submit(
                    self.jailbreak_handler.predict, input_text
                )
                # Get results from both models
                toxic_prob = toxic_thread.result()
                jailbreak_prob = jailbreak_thread.result()
            end = time.time()
            if toxic_prob > 0.5:
                toxic_verdict = "toxic"
            if jailbreak_prob > 0.5:
                jailbreak_verdict = "jailbreak"
            result_dict = {
                "toxic_prob": toxic_prob,
                "jailbreak_prob": jailbreak_prob,
                "time": end - start,
                "toxic_verdict": toxic_verdict,
                "jailbreak_verdict": jailbreak_verdict,
            }
        else:
            if self.toxic_model is not None:
                prob = self.toxic_handler.predict(input_text)
            elif self.jailbreak_model is not None:
                jailbreak_prob = self.jailbreak_handler.predict(input_text)
            else:
                raise Exception("No model loaded")
            if prob > 0.5:
                verdict = "toxic"
            result_dict = {
                "prob": toxic_prob,
                "verdict": verdict,
            }
        return result_dict
