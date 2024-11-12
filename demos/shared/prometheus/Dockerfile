
FROM prom/prometheus:latest

# Set the command to run Prometheus with the specified configuration file
CMD ["--config.file=/etc/prometheus/prometheus.yaml"]

# Copy the Prometheus configuration files
COPY ./prometheus.yaml /etc/prometheus/prometheus.yaml

# Expose Prometheus port
EXPOSE 9090
