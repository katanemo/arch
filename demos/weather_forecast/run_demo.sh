#!/bin/bash
set -e

# Directory where the Docker Compose files are stored

# Function to determine the docker-compose file based on the argument
get_compose_file() {
  case "$1" in
    jaeger)
      echo "docker-compose-jaeger.yaml"
      ;;
    logfire)
      echo "docker-compose-logfire.yaml"
      ;;
    signoz)
      echo "docker-compose-signoz.yaml"
      ;;
    *)
      echo "docker-compose.yaml"  # Default to Jaeger
      ;;
  esac
}

# Function to start the demo
start_demo() {
  # Step 1: Determine the docker-compose file
  COMPOSE_FILE=$(get_compose_file "$1")

  # Step 2: Check if .env file exists
  if [ -f ".env" ]; then
    echo ".env file already exists. Skipping creation."
  else
    # Step 3: Create `.env` file and set OpenAI key
    if [ -z "$OPENAI_API_KEY" ]; then
      echo "Error: OPENAI_API_KEY environment variable is not set for the demo."
      exit 1
    fi

    echo "Creating .env file..."
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env
    echo ".env file created with OPENAI_API_KEY."
  fi

  # Step 4: Start Arch
  echo "Starting Arch with arch_config.yaml..."
  archgw up arch_config.yaml

  # Step 5: Start Network Agent with the chosen Docker Compose file
  echo "Starting Network Agent using $COMPOSE_FILE..."
  docker compose -f "$COMPOSE_FILE" up -d  # Run in detached mode
}

# Function to stop the demo
stop_demo() {
  echo "Stopping all Docker Compose services..."

  # Stop all services by iterating through all configurations
  for compose_file in ./docker-compose*.yaml; do
    echo "Stopping services in $compose_file..."
    docker compose -f "$compose_file" down
  done

  # Stop Arch
  echo "Stopping Arch..."
  archgw down
}

# Main script logic
if [ "$1" == "down" ]; then
  stop_demo
else
  # Use the argument (jaeger, logfire, signoz) to determine the compose file
  start_demo "$1"
fi
