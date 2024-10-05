from setuptools import setup, find_packages

setup(
    name="archgw",
    version="0.1.0",
    description="Python-based CLI tool to manage Arch and generate targets.",
    author="Katanemo Labs, Inc.",
    packages=find_packages(),
    py_modules = ['cli', 'core', 'targets', 'utils', 'config_generator'],
    include_package_data=True,
    package_data={
        '': ['config/docker-compose.yaml', 'config/arch_config_schema.yaml'] #Specify to include the docker-compose.yml file
    },
    install_requires=['pyyaml', 'pydantic', 'click', 'jinja2','pyyaml','jsonschema', 'setuptools'],  # Add dependencies here, e.g., 'PyYAML' for YAML processing
    entry_points={
        'console_scripts': [
            'archgw=cli:main',
        ],
    },
)
