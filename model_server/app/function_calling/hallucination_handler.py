import torch
import numpy as np
from typing import List, Dict

def filter_tokens_and_probs(tokens: List[str], probs: List[float]) -> Tuple[List[], List[float]]:
    """
    Filters out special tokens from the list of tokens and their corresponding probabilities.

    Args:
        tokens (list): List of tokens.
        probs (list): List of probabilities corresponding to the tokens.

    Returns:
        tuple: A tuple containing two lists - filtered tokens and their corresponding probabilities.
    """
    # Use regex to identify tokens without special characters
    special_tokens = ['\\n', '{"', '":', ' "', '",', ' {"', '"}}\\n', ' ', '"}}\n']
    filtered_tokens = [
        token for token in tokens 
        if token not in special_tokens
    ]
    filtered_probs = [
        prob for token, prob in zip(tokens, probs)  
        if token not in special_tokens
    ]
    return filtered_tokens, filtered_probs
def get_all_parameter_values(tokens: List[str], probs: List[float], parameter_names: Dict[str, List[str]]) -> Tuple[Dict[str, List[str]], Dict[str, List[float]]]:
    """
    Extracts parameter values and their corresponding probabilities from the tokens.

    Args:
        tokens (list): List of tokens.
        probs (list): List of probabilities corresponding to the tokens.
        parameter_names (dict): Dictionary of parameter names for each function.

    Returns:
        tuple: A tuple containing two dictionaries - parameter values and their corresponding probabilities.
    """
    parameter_values = {}
    probs_values = {}
    i = 0

    while i < len(tokens):
        # Try to form parameter names by combining tokens
        combined_token = ""
        start = i
        found_param = False

        # Incrementally combine tokens to find a full match with any parameter name
        while i < len(tokens):
            if combined_token:
                combined_token += tokens[i]  # Append next token to the current combination
            else:
                combined_token = tokens[i]  # Start a new combination

            # Check if the combined token matches any parameter name
            for func, params in parameter_names.items():
                if combined_token in params:
                    # Collect values associated with this parameter
                    values = []
                    prob_values = []
                    i += 1  # Move past the parameter name

                    # Collect tokens as values until the next parameter or end marker
                    while i < len(tokens) and tokens[i] not in params and tokens[i] != '</tool_call>':
                        values.append(tokens[i])
                        prob_values.append(probs[i])
                        i += 1

                    # Store the parameter values and probabilities
                    parameter_values[combined_token] = values
                    probs_values[combined_token] = prob_values

                    found_param = True
                    break  # Stop combining further once a parameter is matched

            if found_param:
                break  # Exit the outer loop if parameter was matched
            i += 1  # Move to the next token if no match was found yet

        # Reset to the next token if no parameter match was found
        if not found_param:
            i = start + 1

    return parameter_values, probs_values
def calculate_stats(data: Dict, function_description: Dict) -> Dict:
    """
    Calculates statistical metrics for the given data.

    Args:
        data (dict): Dictionary containing parameter values and their corresponding probabilities.
        function_description (dict): Description of the function containing parameter properties.

    Returns:
        dict: Dictionary containing statistical metrics for each parameter.
    """
    stats = {}
    try:
        for key, values in data.items():
            if len(data[key])>=1:
                first = values[0]
                max_value = max(values)
                min_value = min(values)
                avg_value = sum(values) / len(values)
                has_format = check_parameter_property(function_description, key, "format")
                has_default = check_parameter_property(function_description, key , "default")
                stats[key] = {'first':first, 'max': max_value, 'min': min_value, 'avg': avg_value, 'has_format': has_format, 'has_default': has_default}
    except Exception as e:
        print(data)
    return stats

def check_parameter_property(api_description: Dict, parameter_name: str, property_name: str)-> bool:
    """
    Check if a parameter in an API description has a specific property.

    Args:
        api_description (dict): The API description in JSON format.
        parameter_name (str): The name of the parameter to check.
        property_name (str): The property to look for (e.g., 'format', 'default').

    Returns:
        bool: True if the parameter has the specified property, False otherwise.
    """
    parameters = api_description.get("parameters", {}).get("properties", {})
    parameter_info = parameters.get(parameter_name, {})

    return property_name in parameter_info



def hallucination_detect(token:str, log_probs:List[float], current_state: Dict, entropy_thd : float= 0.7, varentropy_thd :float = 4.0) -> bool:
    """
    Detects hallucinations in the token sequence based on entropy and varentropy thresholds.

    Args:
        token (str): The current token.
        log_probs (list): List of log probabilities for the current token.
        current_state (dict): The current state of the detection process.
        entropy_thd (float): Entropy threshold for detecting hallucinations.
        varentropy_thd (float): Variance of entropy threshold for detecting hallucinations.

    Returns:
        bool: True if a hallucination is detected, False otherwise.
    """
            
    if token:
        # check if there is content in token
        current_state["tokens"].append(token)
        current_state['content'] += token
        current_state['logprobs'].append(log_probs)
        # keep track of entropy and varentropy
        _, entropy, varentropy = calculate_entropy(log_probs)
        current_state["entropy"].append(entropy)
        current_state["varentropy"].append(varentropy)
        # first check if tool call token is certain
        if token == "<tool_call>":
            if entropy > entropy_thd or varentropy > varentropy_thd:
                current_state["hallucination"] = True
                current_state["hallucination_message"] = f"{token} with entropy {entropy}, varentropy {varentropy} doesn't pass the threshold {entropy_thd} | {varentropy_thd}"
                return True
        elif token == "</tool_call>":
            current_state["state"] = "tool_call_end"
            # try to extract tool call, else raise error
            try:
                current_state['tool_call'] = extract_tool_calls(current_state["content"])[0]
                current_state['tool_call_process'] = True
            except:
                current_state['tool_call_process'] = False
                print(f"cant process tool")
                return True
            # check if function name is valid
            if current_state['tool_call']['function']['name'] not in current_state['parameter_names'].keys():
                current_state["hallucination"] = True
                current_state["hallucination_message"] = f"function name {current_state['tool_call']['name']} not found"
                return True

            # check if parameter names are from the given function tools
            current_parameter_names = current_state['tool_call']['function']['arguments'].keys()
            given_parameter_names = current_state['parameter_names'][current_state['tool_call']['function']['name']]
            if not set(current_parameter_names).issubset(given_parameter_names):

                missing_keys = set(current_parameter_names) - set(given_parameter_names)

                current_state["hallucination"] = True
                current_state["hallucination_message"] = f"parameter names {missing_keys} not found"
                return True

            # filtered special tokens that are not needed in the hallucination check for parameter values
            current_state["filtered_tokens"], current_state["filtered_entropy"] = filter_tokens_and_probs(current_state["tokens"], current_state["entropy"])
            current_state["filtered_tokens"], current_state["filtered_varentropy"] = filter_tokens_and_probs(current_state["tokens"], current_state["varentropy"])
            parameter_values, entropy_values = get_all_parameter_values(current_state["filtered_tokens"], current_state["filtered_entropy"], current_state['parameter_names'])
            parameter_values, varentropy_values = get_all_parameter_values(current_state["filtered_tokens"], current_state["filtered_varentropy"], current_state['parameter_names'])

            current_state['parameter_values'] = parameter_values
            current_state['parameter_values_entropy'] = entropy_values
            current_state['parameter_values_varentropy'] = varentropy_values
            # calculate the max, first, avg of sub tokens for parameter value
            current_state['parameter_value_entropy_stat'] = calculate_stats(current_state['parameter_values_entropy'], current_state['function_description'][0])
            current_state['parameter_value_varentropy_stat'] = calculate_stats(current_state['parameter_values_varentropy'], current_state['function_description'][0])
            # get map for debugging
            current_state['token_entropy_map'] = {x : y for x,y in zip(current_state['tokens'], current_state['entropy'])}
            current_state['token_varentropy_map'] = {x : y for x,y in zip(current_state['tokens'], current_state['varentropy'])}

            # checking hallucination for parameter value
            current_state['parameter_value_check'] = {x : {'hallucination': False, 'message': ''} for x in current_state['parameter_values'].keys()}
            for key in current_state['parameter_value_check'].keys():
                # if parameter is given a format, check the first token
                if current_state['parameter_value_entropy_stat'][key]['has_format']:
                    if current_state['parameter_value_entropy_stat'][key]['first'] > entropy_thd or current_state['parameter_value_varentropy_stat'][key]['first'] > varentropy_thd:
                        current_state['parameter_value_check'][key]['hallucination'] = True
                        current_state["hallucination"] = True
                        current_state['parameter_value_check'][key]['message'] = f"parameter {key} with formatting doesn't pass threshold"
                # if parameter gis given a default value, we can always use default
                elif current_state['parameter_value_entropy_stat'][key]['has_default']:
                    current_state['parameter_value_check'][key]['hallucination'] = False
                    current_state['parameter_value_check'][key]['message'] = f"parameter {key} with default"
                # check if max sub token is > thresholds
                else:
                    if current_state['parameter_value_entropy_stat'][key]['max'] > entropy_thd or current_state['parameter_value_varentropy_stat'][key]['max'] > varentropy_thd:
                        current_state['parameter_value_check'][key]['hallucination'] = True
                        current_state['parameter_value_check'][key]['message'] = f"parameter {key}  with {current_state['parameter_value_entropy_stat'][key]['max']} and {current_state['parameter_value_varentropy_stat'][key]['max']} doesnt pass threshold"
                        current_state["hallucination"] = True
            if current_state["hallucination"] == True:
                current_state["hallucination_message"] = "\n".join([current_state['parameter_value_check'][key]['message'] for key in current_state['parameter_value_check'].keys()])
                return True
    return False