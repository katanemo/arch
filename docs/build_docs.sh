#!/bin/bash

# Check if an argument is provided
if [ -z "$1" ]; then
  echo "Usage: ./build_docs.sh [clean|html]"
  exit 1
fi

# Get the argument (flag)
ACTION=$1

# Build the Docker image
docker build -f Dockerfile . -t sphinx

# Execute based on the provided flag
case $ACTION in
  clean)
    echo "Running 'make clean'..."
    docker run --rm -v $(pwd):/docs sphinx make clean
    ;;
  html)
    echo "Running 'make html'..."
    docker run --rm -v $(pwd):/docs sphinx make html
    ;;
  *)
    echo "Invalid option: $ACTION"
    echo "Usage: ./build_docs.sh [clean|html]"
    exit 1
    ;;
esac
