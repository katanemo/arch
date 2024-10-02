import os
from jinja2 import Environment, FileSystemLoader
import yaml
from jsonschema import validate

ENVOY_CONFIG_TEMPLATE_FILE = os.getenv('ENVOY_CONFIG_TEMPLATE_FILE', 'envoy.template.yaml')
ARCH_CONFIG_FILE = os.getenv('ARCH_CONFIG_FILE', '/config/arch_config.yaml')
ENVOY_CONFIG_FILE_RENDERED = os.getenv('ENVOY_CONFIG_FILE_RENDERED', '/etc/envoy/envoy.yaml')
ARCH_CONFIG_SCHEMA_FILE = os.getenv('ARCH_CONFIG_SCHEMA_FILE', 'arch_config_schema.yaml')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', False)
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', False)

def add_secret_key_to_llm_providers(config_yaml) :
    llm_providers = []
    for llm_provider in config_yaml.get("llm_providers", []):
        if llm_provider['access_key'] == "mistral_access_key":
            llm_provider['access_key'] = MISTRAL_API_KEY
        elif llm_provider['access_key'] == "openai_access_key":
            llm_provider['access_key'] = OPENAI_API_KEY
        else:
            llm_provider.pop('access_key')
        llm_providers.push(llm_provider)
    config_yaml["llm_providers"] = llm_providers
    return config_yaml

env = Environment(loader=FileSystemLoader('./'))
template = env.get_template('envoy.template.yaml')

with open(ARCH_CONFIG_FILE, 'r') as file:
    katanemo_config = file.read()

with open(ARCH_CONFIG_SCHEMA_FILE, 'r') as file:
    arch_config_schema = file.read()

config_yaml = yaml.safe_load(katanemo_config)
config_schema_yaml = yaml.safe_load(arch_config_schema)

try:
  validate(config_yaml, config_schema_yaml)
except Exception as e:
  print(f"Error validating arch_config file: {ARCH_CONFIG_FILE}, error: {e.message}")
  exit(1)

inferred_clusters = {}

for prompt_target in config_yaml["prompt_targets"]:
    name = prompt_target.get("endpoint", {}).get("name", "")
    if name not in inferred_clusters:
      inferred_clusters[name] = {
          "name": name,
          "port": 80, # default port
      }

print(inferred_clusters)

endpoints = config_yaml.get("endpoints", {})

# override the inferred clusters with the ones defined in the config
for name, endpoint_details in endpoints.items():
    if name in inferred_clusters:
        print("updating cluster", endpoint_details)
        inferred_clusters[name].update(endpoint_details)
        endpoint = inferred_clusters[name]['endpoint']
        if len(endpoint.split(':')) > 1:
            inferred_clusters[name]['endpoint'] = endpoint.split(':')[0]
            inferred_clusters[name]['port'] = int(endpoint.split(':')[1])
    else:
        inferred_clusters[name] = endpoint_details

print("updated clusters", inferred_clusters)

config_yaml = add_secret_key_to_llm_providers(config_yaml)
arch_llm_providers = config_yaml["llm_providers"]
katanemo_config = config_yaml.dumps()

print("llm_providers:", arch_llm_providers)

data = {
    'katanemo_config': katanemo_config,
    'arch_clusters': inferred_clusters,
    'arch_llm_providers': arch_llm_providers
}

rendered = template.render(data)
print(rendered)
print(ENVOY_CONFIG_FILE_RENDERED)
with open(ENVOY_CONFIG_FILE_RENDERED, 'w') as file:
    file.write(rendered)
