from setuptools import setup, find_packages

setup(
    name="archgw",
    version="0.1.0",
    description="Python-based CLI tool to manage Arch and generate targets.",
    author="Katanemo Labs, Inc.",
    packages=find_packages(),
    py_modules = ['cli', 'core', 'targets', 'utils'],
    include_package_data=True,
    package_data={
        '': ['../docker-compose.yml'],  # Specify to include the docker-compose.yml file
    },
    install_requires=['pyyaml', 'pydantic', 'click'],  # Add dependencies here, e.g., 'PyYAML' for YAML processing
    entry_points={
        'console_scripts': [
            'archgw=cli:main',
        ],
    },
)
