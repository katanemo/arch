import click
from core import start_arch, stop_arch
import targets
import os
import config_generator
import pkg_resources
import sys
import subprocess

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
        click.echo( """Arch (The Intelligent Prompt Gateway) CLI""")
        click.echo(logo)
        click.echo(ctx.get_help())

# Command to build archgw and model_server Docker images
ARCHGW_DOCKERFILE = "./arch/Dockerfile"
MODEL_SERVER_DOCKERFILE = "./model_server/Dockerfile"

@click.command()
def build():
    """Build Arch from source. Must be in root of cloned repo."""
    # Check if /arch/Dockerfile exists
    if os.path.exists(ARCHGW_DOCKERFILE):
        click.echo("Building archgw image...")
        try:
            subprocess.run(["docker", "build", "-f", ARCHGW_DOCKERFILE, "-t", "archgw:latest", "."], check=True)
            click.echo("archgw image built successfully.")
        except subprocess.CalledProcessError as e:
            click.echo(f"Error building archgw image: {e}")
            sys.exit(1)
    else:
        click.echo("Error: Dockerfile not found in /arch")
        sys.exit(1)

    click.echo("All images built successfully.")

@click.command()
@click.argument('file', required=False)  # Optional file argument
@click.option('-path', default='.', help='Path to the directory containing arch_config.yml')
def up(file, path):
    """Starts Arch."""
    if file:
        # If a file is provided, process that file
        arch_config_file = os.path.abspath(file)
    else:
        # If no file is provided, use the path and look for arch_config.yml
        arch_config_file = os.path.abspath(os.path.join(path, "arch_config.yml"))

    # Check if the file exists
    if not os.path.exists(arch_config_file):
        print(f"Error: {arch_config_file} does not exist.")
        return

    print(f"Processing config file: {arch_config_file}")
    arch_schema_config = pkg_resources.resource_filename(__name__, "config/arch_config_schema.yaml")

    print(f"Validating {arch_config_file}")

    try:
        config_generator.validate_prompt_config(arch_config_file=arch_config_file, arch_config_schema_file=arch_schema_config)
    except Exception as e:
        print("Exiting archgw up")
        sys.exit(1)

    print("Starting Arch gateway and Arch model server services via docker ")
    start_arch(arch_config_file)

@click.command()
def down():
    """Stops Arch."""
    stop_arch()

@click.command()
@click.option('-f', '--file', type=click.Path(exists=True), required=True, help="Path to the Python file")
def generate_prompt_targets(file):
    """Generats prompt_targets from python methods.
       Note: This works for simple data types like ['int', 'float', 'bool', 'str', 'list', 'tuple', 'set', 'dict']:
       If you have a complex pydantic data type, you will have to flatten those manually until we add support for it."""

    print(f"Processing file: {file}")
    if not file.endswith(".py"):
        print("Error: Input file must be a .py file")
        sys.exit(1)

    targets.generate_prompt_targets(file)

main.add_command(up)
main.add_command(down)
main.add_command(build)
main.add_command(generate_prompt_targets)

if __name__ == '__main__':
    main()
