#!/bin/bash

log() {
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  message="$*"
  echo "$timestamp: $message"
}

print_disk_usage() {
    echo free disk space
    df -h | grep "/$"
}

wait_for_healthz() {
  local healthz_url="$1"
  local timeout_seconds="${2:-30}"  # Default timeout of 30 seconds
  local sleep_between="${3:-5}"  # Default sleep of 5 seconds

  local start_time=$(date +%s)

  while true; do
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "$healthz_url")

    log "Healthz endpoint $healthz_url response code: $response_code"
    if [[ "$response_code" -eq 200 ]]; then
      log "Healthz endpoint is healthy. Proceeding..."
      return 0
    fi

    local elapsed_time=$(( $(date +%s) - $start_time ))
    if [[ $elapsed_time -ge $timeout_seconds ]]; then
      log "Timeout reached. Healthz endpoint is still unhealthy. Exiting..."
      return 1
    fi

    print_disk_usage

    sleep $sleep_between
  done
}
