import sys
import subprocess
import os
import signal
import time
import requests

# Path to the file where the server process ID will be stored
PID_FILE = "/tmp/model_server.pid"

def run_server():
    """Start, stop, or restart the Uvicorn server based on command-line arguments."""
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        action = "start"

    if action == "start":
        start_server()
    elif action == "stop":
        stop_server()
    elif action == "restart":
        restart_server()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


def start_server():
    """Start the Uvicorn server and save the process ID."""
    if os.path.exists(PID_FILE):
        print("Server is already running. Use 'model_server restart' to restart it.")
        sys.exit(1)

    print(f"Starting Archgw Model Server")
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "51000"],
    )

    if wait_for_health_check("http://0.0.0.0:51000/healthz"):
        # Write the process ID to the PID file
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
        print(f"ARCH GW Model Server started with PID {process.pid}")
    else:
        #Add model_server boot-up logs
        print(f"ARCH GW Model Server - Didn't Sart In Time. Shutting Down")
        process.terminate()

def wait_for_health_check(url, timeout=60):
    """Wait for the Uvicorn server to respond to health-check requests."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            time.sleep(1)
    print("Timed out waiting for ARCH GW Model Server to respond.")
    return False


def stop_server():
    """Stop the running Uvicorn server."""
    if not os.path.exists(PID_FILE):
        print("Server is not running.")
        sys.exit(1)

    # Read the process ID from the PID file
    with open(PID_FILE, "r") as f:
        pid = int(f.read())

    # Kill the process
    os.kill(pid, signal.SIGTERM)
    os.remove(PID_FILE)
    print(f"Server with PID {pid} stopped.")


def restart_server():
    """Restart the Uvicorn server."""
    stop_server()
    start_server()
