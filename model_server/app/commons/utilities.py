import os
import yaml
import torch
import string
import logging
import pkg_resources

from openai import OpenAI


logger_instance = None


def load_yaml_config(file_name):
    # Load the YAML file from the package
    yaml_path = pkg_resources.resource_filename("app", file_name)
    with open(yaml_path, "r") as yaml_file:
        return yaml.safe_load(yaml_file)


def get_device():
    available_device = {
        "cpu": True,
        "cuda": torch.cuda.is_available(),
        "mps": (
            torch.backends.mps.is_available()
            if hasattr(torch.backends, "mps")
            else False
        ),
    }

    if available_device["cuda"]:
        device = "cuda"
    elif available_device["mps"]:
        device = "mps"
    else:
        device = "cpu"

    return device


def get_client(endpoint):
    client = OpenAI(base_url=endpoint, api_key="EMPTY")
    return client


def get_model_server_logger():
    global logger_instance

    if logger_instance is not None:
        # If the logger is already initialized, return the existing instance
        return logger_instance

    # Define log file path outside current directory (e.g., ~/archgw_logs)
    log_dir = os.path.expanduser("~/archgw_logs")
    log_file = "modelserver.log"
    log_file_path = os.path.join(log_dir, log_file)

    # Ensure the log directory exists, create it if necessary, handle permissions errors
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)  # Create directory if it doesn't exist

        # Check if the script has write permission in the log directory
        if not os.access(log_dir, os.W_OK):
            raise PermissionError(f"No write permission for the directory: {log_dir}")
            # Configure logging to file and console using basicConfig

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file_path, mode="w"),  # Overwrite logs in file
            ],
        )
    except (PermissionError, OSError):
        # Dont' fallback to console logging if there are issues writing to the log file
        raise RuntimeError(f"No write permission for the directory: {log_dir}")

    # Initialize the logger instance after configuring handlers
    logger_instance = logging.getLogger("model_server_logger")
    return logger_instance


def remove_punctuations(s):
    s = s.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    return " ".join(s.split()).lower()


def get_label_map(labels):
    return {remove_punctuations(label): label for label in labels}
