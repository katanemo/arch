FROM grafana/grafana:latest

FROM grafana/grafana:latest

# Set environment variables
ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=grafana

# Copy provisioning files
COPY ./datasource.yaml /etc/grafana/provisioning/datasources/datasource.yaml
COPY ./dashboard.yaml /etc/grafana/provisioning/dashboards/main.yaml
COPY ./dashboards /var/lib/grafana/dashboards

# Expose Grafana port
EXPOSE 3000
