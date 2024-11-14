import os
import time
import requests
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


otel_tracing_endpoint = os.getenv(
    "OTEL_TRACING_HTTP_ENDPOINT", "http://localhost:4318/v1/traces"
)
envoy_log_path = os.getenv("ENVOY_LOG_PATH", "/var/log/envoy.log")

logging.info(f"Using otel-tracing host: {otel_tracing_endpoint}")
logging.info(f"Using envoy log path: {envoy_log_path}")


def process_log_line(line):
    try:
        response = requests.post(
            url=otel_tracing_endpoint,
            data=line,
            headers={"Content-Type": "application/json"},
        )
        logging.info(f"Sent trace to otel-tracing: {response.status_code}")
    except Exception as e:
        logging.error(f"Failed to send trace to otel-tracing: {e}")


with open(envoy_log_path, "r") as f:
    while True:
        line = f.readline()
        if not line:
            time.sleep(1)
            continue
        tokens = line.split("gateway: upstream_llm trace details: ")
        if len(tokens) > 1:
            process_log_line(tokens[1])
