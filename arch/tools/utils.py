import subprocess
import os
import time
import select
import shlex

def run_docker_compose_ps(compose_file, env):
    """
    Check if all Docker Compose services are in a healthy state.

    Args:
        path (str): The path where the docker-compose.yml file is located.
    """
    try:
        # Run `docker-compose ps` to get the health status of each service
        ps_process = subprocess.Popen(
            ["docker-compose", "ps"],
            cwd=os.path.dirname(compose_file),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        # Capture the output of `docker-compose ps`
        services_status, error_output = ps_process.communicate()

        # Check if there is any error output
        if error_output:
            print(f"Error while checking service status:\n{error_output}", file=os.sys.stderr)
            return {}

        lines = services_status.strip().splitlines()
        services = {}

        # Skip the header row and parse each service
        for line in lines[1:]:
            parts = shlex.split(line)
            if len(parts) >= 5:
                service_name = parts[0]  # Service name
                status_index = 3  # Status is typically at index 3, but may have multiple words

                # Check if the status has multiple words (e.g., "running (healthy)")
                if '(' in parts[status_index+1] :
                    # Combine the status field if it's split over two parts
                    status = f"{parts[status_index]} {parts[status_index + 1]}"
                    ports = parts[status_index + 2]
                else:
                    status = parts[status_index]
                    ports = parts[status_index + 1]

                # Store both status and ports in a dictionary for each service
                services[service_name] = {
                    'status': status,
                    'ports': ports
                }

        return services

    except subprocess.CalledProcessError as e:
        print(f"Failed to check service status. Error:\n{e.stderr}")
        return e

#Helper method to print service status
def print_service_status(services):
    print(f"{'Service Name':<25} {'Status':<20} {'Ports'}")
    print("="*72)
    for service_name, info in services.items():
        status = info['status']
        ports = info['ports']
        print(f"{service_name:<25} {status:<20} {ports}")

#check for states based on the states passed in
def check_services_state(services, states):
    for service_name, service_info in services.items():
        status = service_info['status'].lower()  # Convert status to lowercase for easier comparison
        if any(state in status for state in states):
            return True

    return False
