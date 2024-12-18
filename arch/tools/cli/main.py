import click
import os
import sys
import subprocess
import multiprocessing
import importlib.metadata
from cli import targets
from cli.utils import (
    getLogger,
    get_llm_provider_access_keys,
    load_env_file_to_dict,
    validate_schema,
)
from cli.core import (
    start_arch_modelserver,
    stop_arch_modelserver,
    start_arch,
    stop_arch,
    download_models_from_hf,
)
from cli.consts import (
    KATANEMO_DOCKERHUB_REPO,
    KATANEMO_LOCAL_MODEL_LIST,
    SERVICE_NAME_ARCHGW,
    SERVICE_NAME_MODEL_SERVER,
    SERVICE_ALL,
)

log = getLogger(__name__)

logo = r"""
     _                _
    / \    _ __  ___ | |__
   / _ \  | '__|/ __|| '_ \
  / ___ \ | |  | (__ | | | |
 /_/   \_\|_|   \___||_| |_|

"""

# Command to build archgw and model_server Docker images
ARCHGW_DOCKERFILE = "./arch/Dockerfile"
MODEL_SERVER_BUILD_FILE = "./model_server/pyproject.toml"


def get_version():
    try:
        version = importlib.metadata.version("archgw")
        return version
    except importlib.metadata.PackageNotFoundError:
        return "version not found"


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show the archgw cli version and exit.")
@click.pass_context
def main(ctx, version):
    if version:
        click.echo(f"archgw cli version: {get_version()}")
        ctx.exit()

    log.info(f"Starting archgw cli version: {get_version()}")

    if ctx.invoked_subcommand is None:
        click.echo("""Arch (The Intelligent Prompt Gateway) CLI""")
        click.echo(logo)
        click.echo(ctx.get_help())


@click.command()
@click.option(
    "--service",
    default=SERVICE_ALL,
    help="Optional parameter to specify which service to build. Options are model_server, archgw",
)
def build(service):
    """Build Arch from source. Must be in root of cloned repo."""
    if service not in [SERVICE_NAME_ARCHGW, SERVICE_NAME_MODEL_SERVER, SERVICE_ALL]:
        print(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)
    # Check if /arch/Dockerfile exists
    if service == SERVICE_NAME_ARCHGW or service == SERVICE_ALL:
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
                        "--add-host=host.docker.internal:host-gateway",
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
    if service == SERVICE_NAME_MODEL_SERVER or service == SERVICE_ALL:
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
    default=SERVICE_ALL,
    help="Service to start. Options are model_server, archgw.",
)
@click.option(
    "--foreground",
    default=False,
    help="Run Arch in the foreground. Default is False",
    is_flag=True,
)
def up(file, path, service, foreground):
    """Starts Arch."""
    if service not in [SERVICE_NAME_ARCHGW, SERVICE_NAME_MODEL_SERVER, SERVICE_ALL]:
        log.info(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)

    if service == SERVICE_ALL and foreground:
        # foreground can only be specified when starting individual services
        log.info("foreground flag is only supported for individual services. Exiting.")
        sys.exit(1)

    if service == SERVICE_NAME_MODEL_SERVER:
        log.info("Download archgw models from HuggingFace...")
        download_models_from_hf()
        start_arch_modelserver(foreground)
        return

    if file:
        # If a file is provided, process that file
        arch_config_file = os.path.abspath(file)
    else:
        # If no file is provided, use the path and look for arch_config.yaml
        arch_config_file = os.path.abspath(os.path.join(path, "arch_config.yaml"))

    # Check if the file exists
    if not os.path.exists(arch_config_file):
        log.info(f"Error: {arch_config_file} does not exist.")
        return

    log.info(f"Validating {arch_config_file}")

    try:
        validate_schema(arch_config_file)
    except Exception as e:
        log.info(f"Exiting archgw up: validation failed")
        log.info(f"Error: {str(e)}")
        sys.exit(1)

    log.info("Starting arch model server and arch gateway")

    # Set the ARCH_CONFIG_FILE environment variable
    env_stage = {}
    env = os.environ.copy()
    # check if access_keys are preesnt in the config file
    access_keys = get_llm_provider_access_keys(arch_config_file=arch_config_file)

    # remove duplicates
    access_keys = set(access_keys)
    # remove the $ from the access_keys
    access_keys = [item[1:] if item.startswith("$") else item for item in access_keys]

    if access_keys:
        if file:
            app_env_file = os.path.join(
                os.path.dirname(os.path.abspath(file)), ".env"
            )  # check the .env file in the path
        else:
            app_env_file = os.path.abspath(os.path.join(path, ".env"))

        print(f"app_env_file: {app_env_file}")
        if not os.path.exists(
            app_env_file
        ):  # check to see if the environment variables in the current environment or not
            for access_key in access_keys:
                if env.get(access_key) is None:
                    log.info(f"Access Key: {access_key} not found. Exiting Start")
                    sys.exit(1)
                else:
                    env_stage[access_key] = env.get(access_key)
        else:  # .env file exists, use that to send parameters to Arch
            env_file_dict = load_env_file_to_dict(app_env_file)
            for access_key in access_keys:
                if env_file_dict.get(access_key) is None:
                    log.info(f"Access Key: {access_key} not found. Exiting Start")
                    sys.exit(1)
                else:
                    env_stage[access_key] = env_file_dict[access_key]

    env.update(env_stage)

    if service == SERVICE_NAME_ARCHGW:
        start_arch(arch_config_file, env, foreground=foreground)
    else:
        download_models_from_hf()
        start_arch_modelserver(foreground)
        start_arch(arch_config_file, env, foreground=foreground)


@click.command()
@click.option(
    "--service",
    default=SERVICE_ALL,
    help="Service to down. Options are all, model_server, archgw. Default is all",
)
def down(service):
    """Stops Arch."""

    if service not in [SERVICE_NAME_ARCHGW, SERVICE_NAME_MODEL_SERVER, SERVICE_ALL]:
        log.info(f"Error: Invalid service {service}. Exiting")
        sys.exit(1)

    if service == SERVICE_NAME_MODEL_SERVER:
        stop_arch_modelserver()
    elif service == SERVICE_NAME_ARCHGW:
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


main.add_command(up)
main.add_command(down)
main.add_command(build)
main.add_command(generate_prompt_targets)

if __name__ == "__main__":
    main()
