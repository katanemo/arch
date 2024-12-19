#!/bin/bash

wait_for_healthz() {
  local healthz_url="$1"
  local timeout_seconds="${2:-30}"  # Default timeout: 30 seconds
  local start_time=$(date +%s)
  local current_time

  while true; do
    local status_code=$(curl -s -o /dev/null -w "%{http_code}\n" "$healthz_url")

    if [ "$status_code" -eq 200 ]; then
      echo "Service is healthy!"
      return 0
    fi

    current_time=$(date +%s)
    if [ $((current_time - start_time)) -gt $timeout_seconds ]; then
      echo "Timeout waiting for service to become healthy."
      return 1
    fi

    echo "Waiting for service to become healthy, returned code $status_code, elapsed time: $((current_time - start_time)) seconds"
    sleep 5
  done
}
