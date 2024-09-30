import ast
import sys
import yaml
from typing import Any
from pydantic import BaseModel

FLASK_ROUTE_DECORATORS = ["route", "get", "post", "put", "delete", "patch"]
FASTAPI_ROUTE_DECORATORS = ["get", "post", "put", "delete", "patch"]


def detect_framework(tree: Any) -> str:
    """Detect whether the file is using Flask or FastAPI based on imports."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "flask":
                return "flask"
            elif node.module == "fastapi":
                return "fastapi"
    return "unknown"

def get_route_decorators(node: Any, framework: str) -> list:
    """Extract route decorators based on the framework."""
    decorators = []
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            if framework == "flask" and decorator.func.attr in FLASK_ROUTE_DECORATORS:
                decorators.append(decorator.func.attr)
            elif framework == "fastapi" and decorator.func.attr in FASTAPI_ROUTE_DECORATORS:
                decorators.append(decorator.func.attr)
    return decorators


def get_route_path(node: Any, framework: str) -> str:
    """Extract route path based on the framework."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and decorator.args:
            return decorator.args[0].s  # Assuming it's a string literal

def is_pydantic_model(annotation: ast.expr, tree: ast.AST) -> bool:
    """Check if a given type annotation is a Pydantic model."""
    # We walk through the AST to find class definitions and check if they inherit from Pydantic's BaseModel
    if isinstance(annotation, ast.Name):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == annotation.id:
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        return True
    return False

def get_pydantic_model_fields(model_name: str, tree: ast.AST) -> list:
    """Extract fields from a Pydantic model."""
    fields = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == model_name:
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign):
                    # Initialize the default field description
                    description = "Field, description not present. Please fix."
                    
                    # Check if there is a default value and if it's a call to `Field`
                    if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == 'Field':
                        # Search for the description argument inside the Field call
                        for keyword in stmt.value.keywords:
                            if keyword.arg == 'description' and isinstance(keyword.value, ast.Str):
                                description = keyword.value.s  # Extract the string value of the description
                                
                    field_info = {
                        "name": stmt.target.id,
                        "type": stmt.annotation.id if isinstance(stmt.annotation, ast.Name) else "Unknown: Please Fix This!",
                        "description": description,  # Use extracted description
                        "default_value": getattr(stmt, 'value', None),  # Can be enhanced further
                        "required": not hasattr(stmt, 'value')  # If it has a default value, it's optional
                    }
                    fields.append(field_info)
                    
    return fields

def get_function_parameters(node: Any, tree: Any) -> list:
    """Extract the parameters and their types from the function definition."""
    parameters = []
    for arg in node.args.args:
        if arg.arg != "self":  # Skip 'self' or 'cls' in class methods
            param_info = {"name": arg.arg}
            
            # Handle Pydantic model types
            if is_pydantic_model(arg.annotation, tree):
                # Extract and flatten Pydantic model fields
                pydantic_fields = get_pydantic_model_fields(arg.annotation.id, tree)
                parameters.extend(pydantic_fields)  # Flatten the model fields into the parameters list
            
            # Handle standard Python types
            elif isinstance(arg.annotation, ast.Name):
                if arg.annotation.id in ['int', 'float', 'bool', 'str', 'list', 'tuple', 'set', 'dict']:
                    param_info["type"] = arg.annotation.id  # Use the type as a string
                else:
                    param_info["type"] = "[UNKNOWN - PLEASE FIX]"
                param_info["description"] = f"[ADD DESCRIPTION FOR]{arg.arg}"
                param_info["required"] = True
                parameters.append(param_info)
            
            # Handle generic subscript types (e.g., Optional, List[Type], etc.)
            elif isinstance(arg.annotation, ast.Subscript):
                if isinstance(arg.annotation.value, ast.Name) and arg.annotation.value.id in ['list', 'tuple', 'set', 'dict']:
                    param_info["type"] = f"{arg.annotation.value.id}"  # e.g., "List", "Tuple", etc.
                else:
                    param_info["type"] = "[UNKNOWN - PLEASE FIX]"
                param_info["description"] = f"[ADD DESCRIPTION FOR] {arg.arg}"
                param_info["required"] = True
                parameters.append(param_info)
            
            # Default for unknown types
            else:
                param_info["type"] = "[UNKNOWN - PLEASE FIX]"  # If unable to detect type
                param_info["description"] = f"[ADD DESCRIPTION FOR] {arg.arg}"
                param_info["required"] = True
                parameters.append(param_info)
    
    return parameters

def get_function_docstring(node: Any) -> str:
    """Extract the function's docstring if present."""
    if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
        return node.body[0].value.s.strip()
    return "No description provided."


def generate_prompt_targets(input_file_path: str, output_file_path: str) -> None:
    """Introspect routes and generate YAML for either Flask or FastAPI."""
    with open(input_file_path, "r") as source:
        tree = ast.parse(source.read())

    # Detect the framework (Flask or FastAPI)
    framework = detect_framework(tree)
    if framework == "unknown":
        print("Could not detect Flask or FastAPI in the file.")
        return

    print(f"Detected framework: {framework}")

    # Extract routes
    routes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            route_decorators = get_route_decorators(node, framework)
            if route_decorators:
                route_path = get_route_path(node, framework)
                function_params = get_function_parameters(node, tree)  # Get parameters for the route
                function_docstring = get_function_docstring(node)  # Extract docstring
                routes.append({
                    'name': node.name,
                    'path': route_path,
                    'methods': route_decorators,
                    'parameters': function_params,  # Add parameters to the route
                    'description': function_docstring  # Add the docstring as the description
                })

    # Generate YAML structure
    output_structure = {
        "prompt_targets": []
    }

    for route in routes:
        target = {
            "name": route['name'],
            "path": route['path'],
            "description": route['description'],  # Use extracted docstring
            "parameters": [
                {
                    "name": param['name'],
                    "type": param['type'],
                    "description": param['description'],
                    "default_value": param['default_value'],
                    "required": param['required']
                } for param in route['parameters']
            ]
        }
        
        if route['name'] == "default":
            # Special case for `information_extraction` based on your YAML format
            target["type"] = "default"
            target["auto-llm-dispatch-on-response"] = True

        output_structure["prompt_targets"].append(target)

    # Output as YAML
    print(yaml.dump(output_structure, sort_keys=False))
    with open(output_file_path, 'w') as output_file:
        yaml.dump(output_structure, output_file, sort_keys=False , default_flow_style=False, indent=2)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python targets.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Automatically generate the output file name
    if input_file.endswith(".py"):
        output_file = input_file.replace(".py", "_prompt_targets.yml")
    else:
        print("Error: Input file must be a .py file")
        sys.exit(1)

    # Call the function with the input and generated output file names
    generate_prompt_targets(input_file, output_file)

# Example usage:
# python targets.py api.yaml

