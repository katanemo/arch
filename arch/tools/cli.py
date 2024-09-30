import click
from core import start_arch
from targets import generate_prompt_targets

@click.group()
def main():
    """CLI to manage Arch - The Intelligent Prompt Gateway."""
    pass

@click.command()
@click.option('--dir', default='.', help='Path to the directory containing prompt_config.yml')
def up(dir):
    """Reads prompt_config.yml and starts up Arch using Docker."""
    start_arch(dir)  # Placeholder for Docker interaction

@click.command()
@click.argument('file', type=click.Path(exists=True))
def generate_targets_python(file):
    """Reads a Python file and generates prompt_targets.yml. 
       Note: This works for simple data types like ['int', 'float', 'bool', 'str', 'list', 'tuple', 'set', 'dict']: 
       If you have a complex pydantic data type, you will have to flatten those manually until we add support for it."""
    
    if file.endswith(".py"):
        output_file = file.replace(".py", "_prompt_targets.yml")
    else:
        print("Error: Input file must be a .py file")
        sys.exit(1)
        
    generate_prompt_targets(file, output_file)
    print(f"Sucessfully generated targets file: {output_file}")

main.add_command(up)
main.add_command(generate_targets_python)

if __name__ == '__main__':
    main()
