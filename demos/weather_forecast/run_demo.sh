#!/bin/bash
set -e

# Function to load environment variables from the .env file
load_env() {
  if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
  fi
}

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
      echo "docker-compose.yaml"
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
    # Step 3: Check for required environment variables
    if [ -z "$OPENAI_API_KEY" ]; then
      echo "Error: OPENAI_API_KEY environment variable is not set for the demo."
      exit 1
    fi
    if [ "$1" == "logfire" ] && [ -z "$LOGFIRE_API_KEY" ]; then
      echo "Error: LOGFIRE_API_KEY environment variable is required for Logfire."
      exit 1
    fi

    # Create .env file
    echo "Creating .env file..."
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env
    if [ "$1" == "logfire" ]; then
      echo "LOGFIRE_API_KEY=$LOGFIRE_API_KEY" >> .env
    fi
    echo ".env file created with required API keys."
  fi

  load_env

  # Step 4: Start Arch
  echo "Starting Arch with arch_config.yaml..."
  archgw up arch_config.yaml

  # Step 5: Start Network Agent with the chosen Docker Compose file
  docker compose -f "$COMPOSE_FILE" up -d  # Run in detached mode
}

# Function to stop the demo
stop_demo() {
  # Step 1: Determine the demo to stop (default to jaeger if no argument provided)
  DEMO=${1:-jaeger}
  COMPOSE_FILE=$(get_compose_file "$DEMO")

  # Step 2: Stop the specified Docker Compose services
  echo "Stopping services for $DEMO using $COMPOSE_FILE..."
  docker compose -f "$COMPOSE_FILE" down

  # Step 3: Stop Arch
  echo "Stopping Arch..."
  archgw down
}

# Main script logic
if [ "$1" == "down" ]; then
  # Call stop_demo with the second argument as the demo to stop
  stop_demo "$2"
else
  # Use the argument (jaeger, logfire, signoz) to determine the compose file
  start_demo "$1"
fi
