from setuptools import setup, find_packages

# Function to read requirements.txt
def parse_requirements(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip() and not line.startswith("#")]

# Call the parse_requirements function to get the list of dependencies
requirements = parse_requirements('requirements.txt')
print(f"packages to install: {find_packages()}")

setup(
    name="model_server",
    version="0.1",
    packages=find_packages(),
    install_requires=requirements,
    package_data={
        # Specify the package and the data files you want to include
        'app': ['/*.yaml'],  # Includes all .yaml files in the config/ folder
    },
    entry_points={
        'console_scripts': [
            'model_server=app:run_server',
        ],
    },
)
