.. _monitoring:

Monitoring
==========

`OpenTelemetry <https://opentelemetry.io/>`_ is an open-source observability framework providing APIs
and instrumentation for generating, collecting, processing, and exporting telemetry data, such as traces,
metrics, and logs. Its flexible design supports a wide range of backends and seamlessly integrates with
modern application tools.

Arch acts a *source* for several monitoring metrics related to **prompts** and **LLMs** natively integrated
via `OpenTelemetry <https://opentelemetry.io/>`_ to help you understand three critical aspects of your application:
latency, token usage, and error rates by an upstream LLM provider. Latency measures the speed at which your application
is responding to users, which includes metrics like time to first token (TFT), time per output token (TOT) metrics, and
the total latency as perceived by users. Below are some screenshots how Arch integrates natively with tools like
`Grafana <https://grafana.com/grafana/dashboards/>`_ via `Promethus <https://prometheus.io/>`_


Metrics Dashboard (via Grafana)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. image:: /_static/img/llm-request-metrics.png
   :width: 100%
   :align: center

.. image:: /_static/img/input-token-metrics.png
   :width: 100%
   :align: center

.. image:: /_static/img/output-token-metrics.png
   :width: 100%
   :align: center

Configure Monitoring
~~~~~~~~~~~~~~~~~~~~
Arch gateway publishes stats endpoint at http://localhost:19901/stats. As noted above, Arch is a source for metrics. To view and manipulate dashbaords, you will
need to configiure `Promethus <https://prometheus.io/>`_ (as a metrics store) and `Grafana <https://grafana.com/grafana/dashboards/>`_ for dashboards. Below
are some sample configuration files for both, respectively.

.. code-block:: yaml
    :caption: Sample prometheus.yaml config file

    global:
    scrape_interval: 15s
    scrape_timeout: 10s
    evaluation_interval: 15s
    alerting:
    alertmanagers:
        - static_configs:
            - targets: []
        scheme: http
        timeout: 10s
        api_version: v2
    scrape_configs:
    - job_name: archgw
        honor_timestamps: true
        scrape_interval: 15s
        scrape_timeout: 10s
        metrics_path: /stats
        scheme: http
        static_configs:
        - targets:
            - host.docker.internal:19901
        params:
        format: ["prometheus"]


.. code-block:: yaml
    :caption: Sample grafana datasource.yaml config file

    apiVersion: 1
    datasources:
    - name: Prometheus
        type: prometheus
        url: http://prometheus:9090
        isDefault: true
        access: proxy
        editable: true
