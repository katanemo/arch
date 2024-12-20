import os
import sys
import time
import logging
import requests
import subprocess
import importlib


PROJ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Default log directory and file
DEFAULT_LOG_DIR = os.path.join(PROJ_DIR, ".logs")
DEFAULT_LOG_FILE = "modelserver.log"


def get_model_server_logger(log_dir=None, log_file=None):
    """
    Get or initialize the logger instance for the model server.

    Parameters:
    - log_dir (str): Custom directory to store the log file. Defaults to `./.logs`.
    - log_file (str): Custom log file name. Defaults to `modelserver.log`.

    Returns:
    - logging.Logger: Configured logger instance.
    """
    log_dir = log_dir or DEFAULT_LOG_DIR
    log_file = log_file or DEFAULT_LOG_FILE
    log_file_path = os.path.join(log_dir, log_file)

    # Check if the logger is already configured
    logger = logging.getLogger("model_server_logger")
    if logger.hasHandlers():
        # Return existing logger instance if already configured
        return logger

    # Ensure the log directory exists, create it if necessary
    try:
        # Create directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Check for write permissions
        if not os.access(log_dir, os.W_OK):
            raise PermissionError(f"No write permission for the directory: {log_dir}")
    except (PermissionError, OSError) as e:
        raise RuntimeError(f"Failed to initialize logger: {e}")

    # Configure logging to file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            # logging.FileHandler(log_file_path, mode="w"),  # Overwrite logs in the file
            logging.StreamHandler(),  # Also log to console
        ],
    )

    return logger


logger = get_model_server_logger()

logging.info("initializing torch device ...")
import torch


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
