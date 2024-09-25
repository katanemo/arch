import inspect
import yaml
import functions  # This is your module containing the function definitions
import os


def generate_config_from_function(func):
    func_name = func.__name__
    func_doc = func.__doc__

    # Get function signature
    sig = inspect.signature(func)
    params = []

    # Extract parameter info
    for name, param in sig.parameters.items():
        param_info = {
            'name': name,
            'description': f"Provide the {name.replace('_', ' ')}",  # Customize as needed
            'required': param.default == inspect.Parameter.empty,  # True if no default value
            'type': param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'str'  # Get type if available
        }
        params.append(param_info)

    # Define the config for this function
    config = {
        'name': func_name,
        'description': func_doc or "",
        'parameters': params,
        'endpoint': {
            'cluster': 'api_server',
            'path': f"/{func_name}"
        },
        'system_prompt': f"You are responsible for handling {func_name} requests."
    }

    return config


def generate_full_config(module):
    config = {'prompt_targets': []}

    # Automatically get all functions from the module
    functions_list = inspect.getmembers(module, inspect.isfunction)

    for func_name, func_obj in functions_list:
        func_config = generate_config_from_function(func_obj)
        config['prompt_targets'].append(func_config)

    return config


def replace_prompt_targets_in_config(file_path, new_prompt_targets):
    # Load the existing bolt_config.yaml
    with open(file_path, 'r') as file:
        config_data = yaml.safe_load(file)

    # Replace the prompt_targets section with the new one
    config_data['prompt_targets'] = new_prompt_targets

    # Write the updated config back to the YAML file
    with open("bolt_config.yaml", 'w+') as file:
        yaml.dump(config_data, file, sort_keys=False)

    print(f"Updated prompt_targets in bolt_config.yaml")


# Main execution
if __name__ == "__main__":
    # Path to the existing bolt_config.yaml two directories up
    bolt_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../bolt_config.yaml'))

    # Generate new prompt_targets from the functions module
    new_config = generate_full_config(functions)
    new_prompt_targets = new_config['prompt_targets']

    # Replace the prompt_targets in the existing bolt_config.yaml
    replace_prompt_targets_in_config(bolt_config_path, new_prompt_targets)
