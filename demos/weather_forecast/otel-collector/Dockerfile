FROM otel/opentelemetry-collector:latest

COPY otel-collector-config.yaml /etc/otel-collector-config.yaml

ENTRYPOINT ["/otelcol", "--config=/etc/otel-collector-config.yaml"]
