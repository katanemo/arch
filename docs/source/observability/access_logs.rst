.. _arch_access_logging:

Access Logging
==============

Access logging in Arch refers to the logging of detailed information about each request and response that flows through Arch. 
It provides visibility into the traffic passing through Arch, which is crucial for monitoring, debugging, and analyzing the 
behavior of AI applications and their interactions.

Key Features of Access Logging in Arch:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* **Per-Request Logging**: 
  Each request that passes through Arch is logged. This includes important metadata such as HTTP method, 
  path, response status code, request duration, upstream host, and more. 
* **Integration with Monitoring Tools**: 
  Access logs can be exported to centralized logging systems (e.g., ELK stack or Fluentd) or used to feed monitoring and alerting systems.
* **Structured Logging**: where each request is logged as a object, making it easier to parse and analyze using tools like Elasticsearch and Kibana.

.. code-block:: yaml

    [2024-09-27T14:52:01.123Z] "ARCH REQUEST" GET /path/to/resource HTTP/1.1 200 512 1024 56 upstream_service.com D
    X-Arch-Upstream-Service-Time: 25
    X-Arch-Attempt-Count: 1