import click
import os
import pkg_resources
import sys
import subprocess
from cli import targets
from cli import config_generator
from cli.core import (
    start_arch_modelserver,
    stop_arch_modelserver,
    start_arch,
    stop_arch,
    stream_gateway_logs,
)
from cli.utils import get_llm_provider_access_keys, load_env_file_to_dict
from cli.consts import KATANEMO_DOCKERHUB_REPO
from cli.utils import getLogger
import multiprocessing

log = getLogger(__name__)

logo = r"""
     _                _
    / \    _ __  ___ | |__
   / _ \  | '__|/ __|| '_ \
  / ___ \ | |  | (__ | | | |
 /_/   \_\|_|   \___||_| |_|

"""


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("""Arch (The Intelligent Prompt Gateway) CLI""")
        click.echo(logo)
        click.echo(ctx.get_help())


# Command to build archgw and model_server Docker images
ARCHGW_DOCKERFILE = "./arch/Dockerfile"
MODEL_SERVER_BUILD_FILE = "./model_server/pyproject.toml"


@click.command()
@click.option(
    "--service",
    default="all",
    help="Optioanl parameter to specify which service to build. Options are model_server, archgw",
)
def build(service):
    """Build Arch from source. Must be in root of cloned repo."""
    if service not in ["model_server", "archgw", "all"]:
        print(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)
    # Check if /arch/Dockerfile exists
    if service == "archgw" or service == "all":
        if os.path.exists(ARCHGW_DOCKERFILE):
            click.echo("Building archgw image...")
            try:
                subprocess.run(
                    [
                        "docker",
                        "build",
                        "-f",
                        ARCHGW_DOCKERFILE,
                        "-t",
                        f"{KATANEMO_DOCKERHUB_REPO}:latest",
                        ".",
                    ],
                    check=True,
                )
                click.echo("archgw image built successfully.")
            except subprocess.CalledProcessError as e:
                click.echo(f"Error building archgw image: {e}")
                sys.exit(1)
        else:
            click.echo("Error: Dockerfile not found in /arch")
            sys.exit(1)

    click.echo("archgw image built successfully.")

    """Install the model server dependencies using Poetry."""
    if service == "model_server" or service == "all":
        # Check if pyproject.toml exists
        if os.path.exists(MODEL_SERVER_BUILD_FILE):
            click.echo("Installing model server dependencies with Poetry...")
            try:
                subprocess.run(
                    ["poetry", "install", "--no-cache"],
                    cwd=os.path.dirname(MODEL_SERVER_BUILD_FILE),
                    check=True,
                )
                click.echo("Model server dependencies installed successfully.")
            except subprocess.CalledProcessError as e:
                click.echo(f"Error installing model server dependencies: {e}")
                sys.exit(1)
        else:
            click.echo(f"Error: pyproject.toml not found in {MODEL_SERVER_BUILD_FILE}")
            sys.exit(1)


@click.command()
@click.argument("file", required=False)  # Optional file argument
@click.option(
    "--path", default=".", help="Path to the directory containing arch_config.yaml"
)
@click.option(
    "--service",
    default="all",
    help="Service to start. Options are model_server, archgw.",
)
def up(file, path, service):
    """Starts Arch."""
    if service not in ["all", "model_server", "archgw"]:
        print(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)

    if service == "model_server":
        start_arch_modelserver()
        return

    if file:
        # If a file is provided, process that file
        arch_config_file = os.path.abspath(file)
    else:
        # If no file is provided, use the path and look for arch_config.yaml
        arch_config_file = os.path.abspath(os.path.join(path, "arch_config.yaml"))

    # Check if the file exists
    if not os.path.exists(arch_config_file):
        print(f"Error: {arch_config_file} does not exist.")
        return

    print(f"Validating {arch_config_file}")
    arch_schema_config = pkg_resources.resource_filename(
        __name__, "../config/arch_config_schema.yaml"
    )

    try:
        config_generator.validate_prompt_config(
            arch_config_file=arch_config_file,
            arch_config_schema_file=arch_schema_config,
        )
    except Exception as e:
        print(f"Exiting archgw up: {e}")
        sys.exit(1)

    log.info("Starging arch model server and arch gateway")

    # Set the ARCH_CONFIG_FILE environment variable
    env_stage = {}
    env = os.environ.copy()
    # check if access_keys are preesnt in the config file
    access_keys = get_llm_provider_access_keys(arch_config_file=arch_config_file)
    if access_keys:
        if file:
            app_env_file = os.path.join(
                os.path.dirname(os.path.abspath(file)), ".env"
            )  # check the .env file in the path
        else:
            app_env_file = os.path.abspath(os.path.join(path, ".env"))

        if not os.path.exists(
            app_env_file
        ):  # check to see if the environment variables in the current environment or not
            for access_key in access_keys:
                if env.get(access_key) is None:
                    print(f"Access Key: {access_key} not found. Exiting Start")
                    sys.exit(1)
                else:
                    env_stage[access_key] = env.get(access_key)
        else:  # .env file exists, use that to send parameters to Arch
            env_file_dict = load_env_file_to_dict(app_env_file)
            for access_key in access_keys:
                if env_file_dict.get(access_key) is None:
                    print(f"Access Key: {access_key} not found. Exiting Start")
                    sys.exit(1)
                else:
                    env_stage[access_key] = env_file_dict[access_key]

    with open(
        pkg_resources.resource_filename(__name__, "../config/stage.env"), "w"
    ) as file:
        for key, value in env_stage.items():
            file.write(f"{key}={value}\n")

    env.update(env_stage)
    env["ARCH_CONFIG_FILE"] = arch_config_file

    if service == "archgw":
        start_arch(arch_config_file, env)
    else:
        start_arch_modelserver()
        start_arch(arch_config_file, env)


@click.command()
@click.option(
    "--service",
    default="all",
    help="Service to down. Options are all, model_server, archgw. Default is all",
)
def down(service):
    """Stops Arch."""

    if service not in ["all", "model_server", "archgw"]:
        print(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)
    if service == "model_server":
        stop_arch_modelserver()
    elif service == "archgw":
        stop_arch()
    else:
        stop_arch_modelserver()
        stop_arch()


@click.command()
@click.option(
    "--f",
    "--file",
    type=click.Path(exists=True),
    required=True,
    help="Path to the Python file",
)
def generate_prompt_targets(file):
    """Generats prompt_targets from python methods.
    Note: This works for simple data types like ['int', 'float', 'bool', 'str', 'list', 'tuple', 'set', 'dict']:
    If you have a complex pydantic data type, you will have to flatten those manually until we add support for it.
    """

    print(f"Processing file: {file}")
    if not file.endswith(".py"):
        print("Error: Input file must be a .py file")
        sys.exit(1)

    targets.generate_prompt_targets(file)


def stream_model_server_logs(follow):
    log_file = "~/archgw_logs/modelserver.log"
    log_file_expanded = os.path.expanduser(log_file)
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


@click.command()
@click.option(
    "--service",
    default="all",
    help="Service to monitor. By default it will monitor both gateway and model_serve",
)
@click.option("--follow", help="Follow the logs", is_flag=True)
def logs(service, follow):
    if service not in ["all", "model_server", "archgw"]:
        print(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)
    archgw_process = None
    if service == "archgw" or service == "all":
        archgw_process = multiprocessing.Process(
            target=stream_gateway_logs, args=(follow,)
        )
        archgw_process.start()

    model_server_process = None
    if service == "model_server" or service == "all":
        model_server_process = multiprocessing.Process(
            target=stream_model_server_logs, args=(follow,)
        )
        model_server_process.start()

    if archgw_process:
        archgw_process.join()
    if model_server_process:
        model_server_process.join()


main.add_command(up)
main.add_command(down)
main.add_command(build)
main.add_command(logs)
main.add_command(generate_prompt_targets)

if __name__ == "__main__":
    main()
