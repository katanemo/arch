import subprocess
import os
import time
import pkg_resources
import select
import sys
import glob
from cli.utils import run_docker_compose_ps, print_service_status, check_services_state
from cli.utils import getLogger
from cli.consts import (
    KATANEMO_LOCAL_MODEL_LIST,
    MODEL_SERVER_LOG_FILE,
    ACCESS_LOG_FILES,
)
from huggingface_hub import snapshot_download

log = getLogger(__name__)


def stream_gateway_logs(follow):
    """
    Stream logs from the arch gateway service.
    """
    compose_file = pkg_resources.resource_filename(
        __name__, "../config/docker-compose.yaml"
    )

    log.info("Logs from arch gateway service.")

    options = ["docker", "compose", "-p", "arch", "logs"]
    if follow:
        options.append("-f")
    try:
        # Run `docker-compose logs` to stream logs from the gateway service
        subprocess.run(
            options,
            cwd=os.path.dirname(compose_file),
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    except subprocess.CalledProcessError as e:
        log.info(f"Failed to stream logs: {str(e)}")


def stream_model_server_logs(follow):
    """
    Get the model server logs, check if the user wants to follow/tail them.
    """
    log_file_expanded = os.path.expanduser(MODEL_SERVER_LOG_FILE)

    stream_command = ["tail"]
    if follow:
        stream_command.append("-f")

    stream_command.append(log_file_expanded)
    subprocess.run(
        stream_command,
        check=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def stream_access_logs(follow):
    """
    Get the archgw access logs
    """
    log_file_pattern_expanded = os.path.expanduser(ACCESS_LOG_FILES)
    log_files = glob.glob(log_file_pattern_expanded)

    stream_command = ["tail"]
    if follow:
        stream_command.append("-f")

    stream_command.extend(log_files)
    subprocess.run(
        stream_command,
        check=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def start_arch(arch_config_file, env, log_timeout=120):
    """
    Start Docker Compose in detached mode and stream logs until services are healthy.

    Args:
        path (str): The path where the prompt_confi.yml file is located.
        log_timeout (int): Time in seconds to show logs before checking for healthy state.
    """
    log.info("Starting arch gateway")
    compose_file = pkg_resources.resource_filename(
        __name__, "../config/docker-compose.yaml"
    )

    try:
        # Run the Docker Compose command in detached mode (-d)
        subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                "arch",
                "up",
                "-d",
            ],
            cwd=os.path.dirname(
                compose_file
            ),  # Ensure the Docker command runs in the correct path
            env=env,  # Pass the modified environment
            check=True,  # Raise an exception if the command fails
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        log.info(f"Arch docker-compose started in detached.")

        start_time = time.time()
        services_status = {}
        services_running = (
            False  # assume that the services are not running at the moment
        )

        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # Check if timeout is reached
            if elapsed_time > log_timeout:
                log.info(f"Stopping log monitoring after {log_timeout} seconds.")
                break

            current_services_status = run_docker_compose_ps(
                compose_file=compose_file, env=env
            )
            if not current_services_status:
                log.info(
                    "Status for the services could not be detected. Something went wrong. Please run docker logs"
                )
                break

            if not services_status:
                services_status = current_services_status  # set the first time
                print_service_status(
                    services_status
                )  # print the services status and proceed.

            # check if anyone service is failed or exited state, if so print and break out
            unhealthy_states = ["unhealthy", "exit", "exited", "dead", "bad"]
            running_states = ["running", "up"]

            if check_services_state(current_services_status, running_states):
                log.info("Arch gateway is up and running!")
                break

            if check_services_state(current_services_status, unhealthy_states):
                log.info(
                    "One or more Arch services are unhealthy. Please run `docker logs` for more information"
                )
                print_service_status(
                    current_services_status
                )  # print the services status and proceed.
                break

            # check to see if the status of one of the services has changed from prior. Print and loop over until finish, or error
            for service_name in services_status.keys():
                if (
                    services_status[service_name]["State"]
                    != current_services_status[service_name]["State"]
                ):
                    log.info(
                        "One or more Arch services have changed state. Printing current state"
                    )
                    print_service_status(current_services_status)
                    break

            services_status = current_services_status

    except subprocess.CalledProcessError as e:
        log.info(f"Failed to start Arch: {str(e)}")


def stop_arch():
    """
    Shutdown all Docker Compose services by running `docker-compose down`.

    Args:
        path (str): The path where the docker-compose.yml file is located.
    """
    compose_file = pkg_resources.resource_filename(
        __name__, "../config/docker-compose.yaml"
    )

    log.info("Shutting down arch gateway service.")

    try:
        # Run `docker-compose down` to shut down all services
        subprocess.run(
            ["docker", "compose", "-p", "arch", "down"],
            cwd=os.path.dirname(compose_file),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        log.info("Successfully shut down arch gateway service.")

    except subprocess.CalledProcessError as e:
        log.info(f"Failed to shut down services: {str(e)}")


def download_models_from_hf():
    for model in KATANEMO_LOCAL_MODEL_LIST:
        log.info(f"Downloading model: {model}")
        snapshot_download(repo_id=model)


def start_arch_modelserver():
    """
    Start the model server. This assumes that the archgw_modelserver package is installed locally

    """
    try:
        log.info("archgw_modelserver restart")
        subprocess.run(
            ["archgw_modelserver", "restart"], check=True, start_new_session=True
        )
        log.info("Successfull ran model_server")
    except subprocess.CalledProcessError as e:
        log.info(f"Failed to start model_server. Please check archgw_modelserver logs")
        sys.exit(1)


def stop_arch_modelserver():
    """
    Stop the model server. This assumes that the archgw_modelserver package is installed locally

    """
    try:
        subprocess.run(
            ["archgw_modelserver", "stop"],
            check=True,
        )
        log.info("Successfull stopped the archgw model_server")
    except subprocess.CalledProcessError as e:
        log.info(f"Failed to start model_server. Please check archgw_modelserver logs")
        sys.exit(1)
