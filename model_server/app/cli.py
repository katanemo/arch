import importlib
import sys
import os
import time
import requests
import psutil
import tempfile
import subprocess
import logging


def get_version():
    try:
        version = importlib.metadata.version("archgw_modelserver")
        return version
    except importlib.metadata.PackageNotFoundError:
        return "version not found"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

log = logging.getLogger("model_server.cli")
log.setLevel(logging.INFO)
log.info(f"model server version: {get_version()}")


def run_server(port=51000):
    """Start, stop, or restart the Uvicorn server based on command-line arguments."""
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        action = "start"

    if action == "start":
        start_server(port)
    elif action == "stop":
        stop_server(port)
    elif action == "restart":
        restart_server(port)
    else:
        log.info(f"Unknown action: {action}")
        sys.exit(1)


def start_server(port=51000):
    """Start the Uvicorn server"""
    log.info(
        "starting model server - loading some awesomeness, this may take some time :)"
    )

    process = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            f"{port}",
        ],
        start_new_session=True,
        bufsize=1,
        universal_newlines=True,
        stdout=subprocess.PIPE,  # Suppress standard output. There is a logger that model_server prints to
        stderr=subprocess.PIPE,  # Suppress standard error. There is a logger that model_server prints to
    )

    if wait_for_health_check(f"http://0.0.0.0:{port}/healthz"):
        log.info(f"Model server started with PID {process.pid}")
    else:
        # Add model_server boot-up logs
        log.info("model server - didn't start in time, shutting down")
        process.terminate()


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
    print("Timed out waiting for model server to respond.")
    return False


def check_and_install_lsof():
    """Check if lsof is installed, and if not, install it using apt-get."""
    try:
        # Check if lsof is installed by running "lsof -v"
        subprocess.run(
            ["lsof", "-v"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print("lsof is already installed.")
    except subprocess.CalledProcessError:
        print("lsof not found, installing...")
        try:
            # Update package list and install lsof
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "lsof"], check=True)
            print("lsof installed successfully.")
        except subprocess.CalledProcessError as install_error:
            print(f"Failed to install lsof: {install_error}")


def kill_process(port=51000, wait=True, timeout=10):
    """Stop the running Uvicorn server."""
    log.info("Stopping model server")
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


def stop_server(port=51000, wait=True, timeout=10):
    check_and_install_lsof()
    kill_process(port, wait, timeout)


def restart_server(port=51000):
    """Restart the Uvicorn server."""
    stop_server(port)
    start_server(port)
