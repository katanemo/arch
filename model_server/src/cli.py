import logging
import sys
import subprocess
import argparse

from src.commons.globals import logger
from src.commons.utils import (
    wait_for_health_check,
    check_lsof,
    install_lsof,
    find_processes_by_port,
    kill_processes,
)


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
        logger.info(f"Unknown action: {action}")
        sys.exit(1)


def start_server(port=51000):
    """Start the Uvicorn server."""

    logger.info("Starting model server - loading some awesomeness, please wait...")

    process = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ],
        start_new_session=True,
        bufsize=1,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if wait_for_health_check(f"http://0.0.0.0:{port}/healthz"):
        logger.info(f"Model server started successfully with PID {process.pid}.")
    else:
        logger.error("Model server failed to start in time, shutting it down.")
        process.terminate()


def stop_server(port=51000, wait=True, timeout=10):
    """Stop the Uvicorn server."""
    if check_lsof():
        logger.info("`lsof` is already installed.")
    else:
        logger.info("`lsof` not found, attempting to install...")
        if install_lsof():
            logger.info("`lsof` installed successfully.")
        else:
            logger.error("Failed to install `lsof`.")
            sys.exit(1)

    logger.info(f"Stopping processes on port {port}...")
    port_processes = find_processes_by_port(port)
    if port_processes is None:
        logger.info(f"No processes found listening on port {port}.")
    else:
        if len(port_processes):
            process_killed = kill_processes(port_processes, wait, timeout)
            if not process_killed:
                logger.error(f"Unable to kill all processes on {port}")
            else:
                logger.info(f"All processes on port {port} have been killed.")
        else:
            logger.error(f"Unable to find processes on {port}")


def restart_server(port=51000):
    """Restart the Uvicorn server."""
    stop_server(port)
    start_server(port)


def main():
    """
    Start, stop, or restart the Uvicorn server based on command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Manage the Uvicorn server.")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart"],
        default="start",
        nargs="?",
        help="Action to perform on the server (default: start).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=51000,
        help="Port number for the server (default: 51000).",
    )

    args = parser.parse_args()

    logger.info(f"Model server version: {get_version()}")

    if args.action == "start":
        start_server(args.port)
    elif args.action == "stop":
        stop_server(args.port)
    elif args.action == "restart":
        restart_server(args.port)
    else:
        logger.error(f"Unknown action: {args.action}")
        sys.exit(1)
