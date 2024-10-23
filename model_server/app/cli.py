import sys
import os
import time
import requests
import psutil
import tempfile
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

log = logging.getLogger("model_server.cli")
log.setLevel(logging.INFO)

# Path to the file where the server process ID will be stored
PID_FILE = os.path.join(tempfile.gettempdir(), "model_server.pid")


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
    """Start the Uvicorn server and save the process ID."""
    if os.path.exists(PID_FILE):
        log.info("Server is already running. Use 'model_server restart' to restart it.")
        sys.exit(1)

    log.info(
        "Starting model server - loading some awesomeness, this may take some time :)"
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
        # Write the process ID to the PID file
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
        log.info(f"Model server started with PID {process.pid}")
    else:
        # Add model_server boot-up logs
        log.info("Model server - Didn't Sart In Time. Shutting Down")
        process.terminate()


def wait_for_health_check(url, timeout=180):
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


def kill_process_on_port(port=51000):
    try:
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
            print(f"Killing process with PID {pid}")
            subprocess.run(f"kill {pid}", shell=True)

    except Exception as e:
        print(f"Error occurred: {e}")


def stop_server(port=51000):
    """Stop the running Uvicorn server."""
    log.info("Stopping model server")
    if not os.path.exists(PID_FILE):
        log.info("Process id file not found, seems like model server was not running")
        return

    # Read the process ID from the PID file
    with open(PID_FILE, "r") as f:
        pid = int(f.read())

    try:
        # Get process by PID
        process = psutil.Process(pid)

        # Gracefully terminate the process
        for child in process.children(recursive=True):
            child.terminate()
        process.terminate()

        process.wait(timeout=20)  # Wait for up to 20 seconds for the process to exit

        if process.is_running():
            log.info(f"Process with PID {pid} is still running. Forcing shutdown.")
            process.kill()  # Forcefully kill the process

        log.info(f"Model server with PID {pid} stopped.")
        os.remove(PID_FILE)

        kill_process_on_port(port)

    except psutil.NoSuchProcess:
        log.info(f"Model server with PID {pid} not found. Cleaning up PID file.")
        os.remove(PID_FILE)
    except psutil.TimeoutExpired:
        log.info(
            f"Model server with PID {pid} did not terminate in time. Forcing shutdown."
        )
        process.kill()  # Forcefully kill the process
        os.remove(PID_FILE)


def restart_server(port=51000):
    """Restart the Uvicorn server."""
    stop_server(port)
    start_server(port)
