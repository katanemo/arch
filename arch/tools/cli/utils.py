import subprocess
import os
import time
import select
import shlex
import yaml
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def getLogger(name="cli"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger


log = getLogger(__name__)


def run_docker_compose_ps(compose_file, env):
    """
    Check if all Docker Compose services are in a healthy state.

    Args:
        path (str): The path where the docker-compose.yml file is located.
    """
    try:
        # Run `docker compose ps` to get the health status of each service.
        # This should be a non-blocking call so using subprocess.Popen(...)
        ps_process = subprocess.Popen(
            [
                "docker",
                "compose",
                "-p",
                "arch",
                "ps",
                "--format",
                "table{{.Service}}\t{{.State}}\t{{.Ports}}",
            ],
            cwd=os.path.dirname(compose_file),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env=env,
        )
        # Capture the output of `docker-compose ps`
        services_status, error_output = ps_process.communicate()

        # Check if there is any error output
        if error_output:
            log.info(
                f"Error while checking service status:\n{error_output}",
                file=os.sys.stderr,
            )
            return {}

        services = parse_docker_compose_ps_output(services_status)
        return services

    except subprocess.CalledProcessError as e:
        log.info(f"Failed to check service status. Error:\n{e.stderr}")
        return e


# Helper method to print service status
def print_service_status(services):
    log.info(f"{'Service Name':<25} {'State':<20} {'Ports'}")
    log.info("=" * 72)
    for service_name, info in services.items():
        status = info["STATE"]
        ports = info["PORTS"]
        log.info(f"{service_name:<25} {status:<20} {ports}")


# check for states based on the states passed in
def check_services_state(services, states):
    for service_name, service_info in services.items():
        status = service_info[
            "STATE"
        ].lower()  # Convert status to lowercase for easier comparison
        if any(state in status for state in states):
            return True

    return False


def get_llm_provider_access_keys(arch_config_file):
    with open(arch_config_file, "r") as file:
        arch_config = file.read()
        arch_config_yaml = yaml.safe_load(arch_config)

    access_key_list = []
    for llm_provider in arch_config_yaml.get("llm_providers", []):
        acess_key = llm_provider.get("access_key")
        if acess_key is not None:
            access_key_list.append(acess_key)

    return access_key_list


def load_env_file_to_dict(file_path):
    env_dict = {}

    # Open and read the .env file
    with open(file_path, "r") as file:
        for line in file:
            # Strip any leading/trailing whitespaces
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Split the line into key and value at the first '=' sign
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Add key-value pair to the dictionary
                env_dict[key] = value

    return env_dict


def parse_docker_compose_ps_output(output):
    # Split the output into lines
    lines = output.strip().splitlines()

    # Extract the headers (first row) and the rest of the data
    headers = lines[0].split()
    service_data = lines[1:]

    # Initialize the result dictionary
    services = {}

    # Iterate over each line of data after the headers
    for line in service_data:
        # Split the line by tabs or multiple spaces
        parts = line.split()

        # Create a dictionary entry using the header names
        service_info = {headers[1]: parts[1], headers[2]: parts[2]}  # State  # Ports

        # Add to the result dictionary using the service name as the key
        services[parts[0]] = service_info

    return services
