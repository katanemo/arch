import click
from core import start_arch
import targets

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

@click.command()
@click.option('--path', default='.', help='Path to the directory containing prompt_config.yml')
def up(path):
    """Starts Arch."""
    start_arch(path)

@click.command()
@click.option('--path', default='.', help='Path to the directory containing prompt_config.yml')
def down(path):
    """Stops Arch."""
    stop_arch(path)

@click.command()
@click.argument('file', type=click.Path(exists=True))
def generate_prompt_targets(file):
    """Generats prompt_targets from python methods.
       Note: This works for simple data types like ['int', 'float', 'bool', 'str', 'list', 'tuple', 'set', 'dict']:
       If you have a complex pydantic data type, you will have to flatten those manually until we add support for it."""

    if file.endswith(".py"):
        output_file = file.replace(".py", "_prompt_targets.yml")
    else:
        print("Error: Input file must be a .py file")
        sys.exit(1)

    targets.generate_prompt_targets(file, output_file)
    print(f"Sucessfully generated targets file: {output_file}")

main.add_command(up)
main.add_command(down)
main.add_command(generate_prompt_targets)

if __name__ == '__main__':
    main()
