import os
from jinja2 import Environment, FileSystemLoader
import yaml

ENVOY_CONFIG_TEMPLATE_FILE = os.getenv('ENVOY_CONFIG_TEMPLATE_FILE', 'envoy.template.yaml')
ARCH_CONFIG_FILE = os.getenv('ARCH_CONFIG_FILE', '/config/arch_config.yaml')
ENVOY_CONFIG_FILE_RENDERED = os.getenv('ENVOY_CONFIG_FILE_RENDERED', '/etc/envoy/envoy.yaml')

env = Environment(loader=FileSystemLoader('./'))
template = env.get_template('envoy.template.yaml')

with open(ARCH_CONFIG_FILE, 'r') as file:
    katanemo_config = file.read()

config_yaml = yaml.safe_load(katanemo_config)

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

data = {
    'katanemo_config': katanemo_config,
    'arch_clusters': inferred_clusters
}

rendered = template.render(data)
print(rendered)
print(ENVOY_CONFIG_FILE_RENDERED)
with open(ENVOY_CONFIG_FILE_RENDERED, 'w') as file:
    file.write(rendered)
