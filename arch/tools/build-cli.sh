#!/bin/bash

# Define paths
source_schema="../arch_config_schema.yaml"
source_compose="../docker-compose.yaml"
destination_dir="config"

# Ensure the destination directory exists only if it doesn't already
if [ ! -d "$destination_dir" ]; then
    mkdir -p "$destination_dir"
    echo "Directory $destination_dir created."
fi

# Copy the files
cp "$source_schema" "$destination_dir/arch_config_schema.yaml"
cp "$source_compose" "$destination_dir/docker-compose.yaml"

# Print success message
echo "Files copied successfully!"

echo "Building the cli"
pip install -e .
