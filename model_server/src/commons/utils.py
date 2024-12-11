import os
import sys
import time
import torch
import logging
import requests
import subprocess
import importlib


PROJ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Default log directory and file
DEFAULT_LOG_DIR = os.path.join(PROJ_DIR, ".logs")
DEFAULT_LOG_FILE = "modelserver.log"


def get_version():
    try:
        version = importlib.metadata.version("archgw_modelserver")
        return version
    except importlib.metadata.PackageNotFoundError:
        return "version not found"


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
            logging.FileHandler(log_file_path, mode="w"),  # Overwrite logs in the file
            logging.StreamHandler(),  # Also log to console
        ],
    )

    return logger


def wait_for_health_check(url, timeout=300):
    """Wait for the Uvicorn server to respond to health-check requests."""

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            time.sleep(1)

    return False


def check_lsof():
    """Check if lsof is installed or not"""
    try:
        subprocess.run(
            ["lsof", "-v"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return True
    except subprocess.CalledProcessError:
        return False


def install_lsof():
    """Install lsof using apt-get."""
    try:
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "lsof"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
        sys.exit(1)


def terminate_process_by_pid(pid, timeout):
    """Terminate a process to terminate."""

    start_time = time.time()
    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["ps", "-p", str(pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            print.info(f"Process {pid} terminated successfully.")
            return
        time.sleep(0.5)

    print.warning(
        f"Process {pid} did not terminate within {timeout} seconds. Force killing..."
    )
    subprocess.run(["kill", "-9", str(pid)], check=False)


def find_processes_by_port(port=51000):
    """Find processes listening on a specific port."""

    port_processes = []

    try:
        lsof_command = f"lsof -n | grep {port} | grep -i LISTEN"
        result = subprocess.run(
            lsof_command, shell=True, capture_output=True, text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None
        else:
            port_processes = result.stdout.splitlines()
            return port_processes

    except Exception:
        return []


def kill_process(port=51000, wait=True, timeout=10):
    """Stop the running Uvicorn server."""
    try:
        # Run the function to check and install lsof if necessary
        # Step 1: Run lsof command to get the process using the port
        lsof_command = f"lsof -n | grep {port} | grep -i LISTEN"
        result = subprocess.run(
            lsof_command, shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"No process found listening on port {port}.")
            return

        # Step 2: Parse the process IDs from the output
        process_ids = [line.split()[1] for line in result.stdout.splitlines()]

        if not process_ids:
            print(f"No process found listening on port {port}.")
            return

        # Step 3: Kill each process using its PID
        for pid in process_ids:
            print(f"Killing model server process with PID {pid}")
            subprocess.run(f"kill {pid}", shell=True)

            if wait:
                # Step 4: Wait for the process to be killed by checking if it's still running
                start_time = time.time()

                while True:
                    check_process = subprocess.run(
                        f"ps -p {pid}", shell=True, capture_output=True, text=True
                    )
                    if check_process.returncode != 0:
                        print(f"Process {pid} has been killed.")
                        break

                    elapsed_time = time.time() - start_time
                    if elapsed_time > timeout:
                        print(
                            f"Process {pid} did not terminate within {timeout} seconds."
                        )
                        print(f"Attempting to force kill process {pid}...")
                        subprocess.run(f"kill -9 {pid}", shell=True)  # SIGKILL
                        break

                    print(
                        f"Waiting for process {pid} to be killed... ({elapsed_time:.2f} seconds)"
                    )
                    time.sleep(0.5)

    except Exception as e:
        print(f"Error occurred: {e}")


def kill_processes(port_processes, wait=True, timeout=10):
    """Kill processes on a specific port."""

    try:
        # Extract process IDs from lsof output
        process_ids = [line.split()[1] for line in port_processes]
        for pid in process_ids:
            print(f"Killing process with PID {pid}...")
            subprocess.run(["kill", pid], check=False)

            if wait:
                terminate_process_by_pid(pid, timeout)

        return True

    except Exception:
        return False
