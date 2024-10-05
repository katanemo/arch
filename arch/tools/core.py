import subprocess
import os
import time
import pkg_resources
import select
from utils import run_docker_compose_ps, print_service_status, check_services_state

def start_arch(arch_config_file, env, log_timeout=120, check_interval=1):
    """
    Start Docker Compose in detached mode and stream logs until services are healthy.

    Args:
        path (str): The path where the prompt_confi.yml file is located.
        log_timeout (int): Time in seconds to show logs before checking for healthy state.
        check_interval (int): Time in seconds between health status checks.
    """

    compose_file = pkg_resources.resource_filename(__name__, 'config/docker-compose.yaml')

    try:
        # Run the Docker Compose command in detached mode (-d)
        subprocess.run(
            ["docker", "compose", "-p", "arch", "up", "-d",],
            cwd=os.path.dirname(compose_file),  # Ensure the Docker command runs in the correct path
            env=env,                   # Pass the modified environment
            check=True                 # Raise an exception if the command fails
        )
        print(f"Arch docker-compose started in detached.")
        print("Monitoring `docker-compose ps` logs...")

        start_time = time.time()
        services_status = {}
        services_running = False #assume that the services are not running at the moment

        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # Check if timeout is reached
            if elapsed_time > log_timeout:
                print(f"Stopping log monitoring after {log_timeout} seconds.")
                break

            current_services_status = run_docker_compose_ps(compose_file=compose_file, env=env)
            if not current_services_status:
                print("Status for the services could not be detected. Something went wrong. Please run docker logs")
                break

            if not services_status:
                services_status = current_services_status #set the first time
                print_service_status(services_status) #print the services status and proceed.

            #check if anyone service is failed or exited state, if so print and break out
            unhealthy_states = ["unhealthy", "exit", "exited", "dead", "bad"]
            running_states = ["running", "up"]

            if check_services_state(current_services_status, running_states):
                print("Arch is up and running!")
                break

            if check_services_state(current_services_status, unhealthy_states):
                print("One or more Arch services are unhealthy. Please run `docker logs` for more information")
                print_service_status(current_services_status) #print the services status and proceed.
                break

            #check to see if the status of one of the services has changed from prior. Print and loop over until finish, or error
            for service_name in services_status.keys():
                if services_status[service_name]['State'] != current_services_status[service_name]['State']:
                    print("One or more Arch services have changed state. Printing current state")
                    print_service_status(current_services_status)
                    break

            services_status = current_services_status

    except subprocess.CalledProcessError as e:
        print(f"Failed to start Arch: {str(e)}")


def stop_arch():
    """
    Shutdown all Docker Compose services by running `docker-compose down`.

    Args:
        path (str): The path where the docker-compose.yml file is located.
    """
    compose_file = pkg_resources.resource_filename(__name__, 'config/docker-compose.yaml')

    try:
        # Run `docker-compose down` to shut down all services
        subprocess.run(
            ["docker", "compose", "-p", "arch", "down"],
            cwd=os.path.dirname(compose_file),
            check=True,
        )
        print("Successfully shut down all services.")

    except subprocess.CalledProcessError as e:
        print(f"Failed to shut down services: {str(e)}")
