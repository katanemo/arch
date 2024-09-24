.. _arch_overview_tracing:

Tracing 
=======

Overview
--------

`OpenTelemetry <https://opentelemetry.io/>`_ is an open-source observability framework providing APIs 
and instrumentation for generating, collecting, processing, and exporting telemetry data, such as traces, 
metrics, and logs. Its flexible design supports a wide range of backends and seamlessly integrates with 
modern application tools. A key feature of OpenTelemetry is its commitment to standards like the 
`W3C Trace Context <https://www.w3.org/TR/trace-context/>`_

**Tracing** is a critical tool that allows developers to visualize and understand the flow of 
requests in an AI application. With tracing, you can capture a detailed view of how requests propagate 
through various services and components, which is crucial for **debugging**, **performance optimization**, 
and understanding complex AI agent architectures like Co-pilots.

**Arch** propagates trace context using the W3C Trace Context standard, specifically through the 
``traceparent`` header. This allows each component in the system to record its part of the request 
flow, enabling **end-to-end tracing** across the entire application. By using OpenTelemetry, Arch ensures 
that developers can capture this trace data consistently and in a format compatible with various observability 
tools.
______________________________________________________________________________________________

Benefits of using ``traceparent`` headers 
-----------------------------------------

- **Standardization**: The W3C Trace Context standard ensures compatibility across ecosystem tools, allowing 
  traces to be propagated uniformly through different layers of the system.
- **Ease of Integration**: OpenTelemetry's design allows developers to easily integrate tracing with minimal 
  changes to their codebase, enabling quick adoption of end-to-end observability.
- **Interoperability**: Works seamlessly with popular tracing tools like AWS X-Ray, Datadog, Jaeger, and many others,
  making it easy to visualize traces in the tools you're already usi

How to initiate a trace
-----------------------

1. **Enable Tracing Configuration**: Simply add the ``tracing: 100`` flag to in the :ref:`listener <arch_overview_listeners>` config

2. **Trace Context Propagation**: Arch automatically propagates the ``traceparent`` header. When a request is received, Arch will:

   - Generate a new ``traceparent`` header if one is not present.
   - Extract the trace context from the ``traceparent`` header if it exists.
   - Start a new span representing its processing of the request.
   - Forward the ``traceparent`` header to downstream services.

3. **Sampling Policy**: The 100 in ``tracing: 100`` means that all the requests as sampled for tracing. 
   You can adjust this value from 0-100.


Trace Propagation
-----------------

Arch uses the W3C Trace Context standard for trace propagation, which relies on the ``traceparent`` header. 
This header carries tracing information in a standardized format, enabling interoperability between different 
tracing systems.

Header Format
~~~~~~~~~~~~~

The ``traceparent`` header has the following format::

   traceparent: {version}-{trace-id}-{parent-id}-{trace-flags}

- {version}: The version of the Trace Context specification (e.g., ``00``).
- {trace-id}: A 16-byte (32-character hexadecimal) unique identifier for the trace.
- {parent-id}: An 8-byte (16-character hexadecimal) identifier for the parent span.
- {trace-flags}: Flags indicating trace options (e.g., sampling).

Instrumentation
~~~~~~~~~~~~~~~

To integrate AI tracing, your application needs to follow a few simple steps. The steps
below are very common practice, and not unique to Arch, when you reading tracing headers and export 
`spans <https://docs.lightstep.com/docs/understand-distributed-tracing>`_ for distributed tracing.

- Read the ``traceparent`` header from incoming requests.
- Start new spans as children of the extracted context.
- Include the ``traceparent`` header in outbound requests to propagate trace context.
- Send tracing data to a collector or tracing backend to export spans

Example with OpenTelemetry in Python
************************************

Install OpenTelemetry packages:

.. code-block:: bash

   pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
   pip install opentelemetry-instrumentation-requests

Set up the tracer and exporter:

.. code-block:: python

   from opentelemetry import trace
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.instrumentation.requests import RequestsInstrumentor
   from opentelemetry.sdk.resources import Resource
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor

   # Define the service name
   resource = Resource(attributes={
       "service.name": "customer-support-agent"
   })

   # Set up the tracer provider and exporter
   tracer_provider = TracerProvider(resource=resource)
   otlp_exporter = OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
   span_processor = BatchSpanProcessor(otlp_exporter)
   tracer_provider.add_span_processor(span_processor)
   trace.set_tracer_provider(tracer_provider)

   # Instrument HTTP requests
   RequestsInstrumentor().instrument()

Handle incoming requests:

.. code-block:: python

   from opentelemetry import trace
   from opentelemetry.propagate import extract, inject
   import requests

   def handle_request(request):
       # Extract the trace context
       context = extract(request.headers)
       tracer = trace.get_tracer(__name__)

       with tracer.start_as_current_span("process_customer_request", context=context):
           # Example of processing a customer request
           print("Processing customer request...")

           # Prepare headers for outgoing request to payment service
           headers = {}
           inject(headers)

           # Make outgoing request to external service (e.g., payment gateway)
           response = requests.get("http://payment-service/api", headers=headers)

           print(f"Payment service response: {response.content}")


AI Agent Tracing Visualization Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following is an example of tracing for an AI-powered customer support system. 
A customer interacts with AI agents, which forward their requests through different 
specialized services and external systems.

::

    +--------------------------+
    |   Customer Interaction   |  
    +--------------------------+
               |
               v
    +--------------------------+        +--------------------------+
    |  Agent 1 (Main - Arch)   | ---->  | External Payment Service |
    +--------------------------+        +--------------------------+
               |                                  |
               v                                  v
    +--------------------------+        +--------------------------+
    |  Agent 2 (Support - Arch)| ---->  |   Internal Tech Support  |
    +--------------------------+        +--------------------------+
               |                                  |
               v                                  v
    +--------------------------+        +--------------------------+
    | Agent 3 (Orders- Arch)   | ---->  |   Inventory Management   |
    +--------------------------+        +--------------------------+

Trace Breakdown:
****************

- **Customer Interaction**:
    - Span 1: Customer initiates a request via the AI-powered chatbot for billing support (e.g., asking for payment details).

- **AI Agent 1 (Main - Arch)**:
    - Span 2: AI Agent 1 (Main) processes the request and identifies it as related to billing, forwarding the request 
      to an external payment service.
    - Span 3: AI Agent 1 determines that additional technical support is needed for processing and forwards the request 
      to AI Agent 2.

- **External Payment Service**:
    - Span 4: The external payment service processes the payment-related request (e.g., verifying payment status) and sends 
      the response back to AI Agent 1.

- **AI Agent 2 (Tech - Arch)**:
    - Span 5: AI Agent 2, responsible for technical queries, processes a request forwarded from AI Agent 1 (e.g., checking for 
      any account issues).
    - Span 6: AI Agent 2 forwards the query to Internal Tech Support for further investigation.

- **Internal Tech Support**:
    - Span 7: Internal Tech Support processes the request (e.g., resolving account access issues) and responds to AI Agent 2.

- **AI Agent 3 (Orders - Arch)**:
    - Span 8: AI Agent 3 handles order-related queries. AI Agent 1 forwards the request to AI Agent 3 after payment verification 
      is completed.
    - Span 9: AI Agent 3 forwards a request to the Inventory Management system to confirm product availability for a pending order.

- **Inventory Management**:
    - Span 10: The Inventory Management system checks stock and availability and returns the information to AI Agent 3.

Integrating with Tracing Tools
------------------------------

AWS X-Ray
~~~~~~~~~

To send tracing data to `AWS X-Ray <https://aws.amazon.com/xray/>`_ :

1. **Configure OpenTelemetry Collector**: Set up the collector to export traces to AWS X-Ray.

   Collector configuration (``otel-collector-config.yaml``):

   .. code-block:: yaml

      receivers:
        otlp:
          protocols:
            grpc:

      processors:
        batch:

      exporters:
        awsxray:
          region: your-aws-region

      service:
        pipelines:
          traces:
            receivers: [otlp]
            processors: [batch]
            exporters: [awsxray]

2. **Deploy the Collector**: Run the collector as a Docker container, Kubernetes pod, or standalone service.
3. **Ensure AWS Credentials**: Provide AWS credentials to the collector, preferably via IAM roles.
4. **Verify Traces**: Access the AWS X-Ray console to view your traces.

Datadog
~~~~~~~

Datadog

To send tracing data to `Datadog <https://docs.datadoghq.com/getting_started/tracing/>`_:

1. **Configure OpenTelemetry Collector**: Set up the collector to export traces to Datadog.

   Collector configuration (``otel-collector-config.yaml``):

   .. code-block:: yaml

      receivers:
        otlp:
          protocols:
            grpc:

      processors:
        batch:

      exporters:
        datadog:
          api:
            key: "${DD_API_KEY}"
          site: "${DD_SITE}"

      service:
        pipelines:
          traces:
            receivers: [otlp]
            processors: [batch]
            exporters: [datadog]

2. **Set Environment Variables**: Provide your Datadog API key and site.

   .. code-block:: bash

      export DD_API_KEY=your_datadog_api_key
      export DD_SITE=datadoghq.com  # Or datadoghq.eu

3. **Deploy the Collector**: Run the collector in your environment.
4. **Verify Traces**: Access the Datadog APM dashboard to view your traces.


Best Practices
--------------

- **Consistent Instrumentation**: Ensure all services propagate the ``traceparent`` header.
- **Secure Configuration**: Protect sensitive data and secure communication between services.
- **Performance Monitoring**: Be mindful of the performance impact and adjust sampling rates accordingly.
- **Error Handling**: Implement proper error handling to prevent tracing issues from affecting your application.

Conclusion
----------

By leveraging the ``traceparent`` header for trace context propagation, Arch enables developers to implement 
tracing efficiently. This approach simplifies the process of collecting and analyzing tracing data in common 
tools like AWS X-Ray and Datadog, enhancing observability and facilitating faster debugging and optimization.

Additional Resources
--------------------

- **OpenTelemetry Documentation**: https://opentelemetry.io/docs/
- **W3C Trace Context Specification**: https://www.w3.org/TR/trace-context/
- **AWS X-Ray Exporter**: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/awsxrayexporter
- **Datadog Exporter**: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/datadogexporter

.. Note::
   Replace placeholders like ``your-aws-region``, and ``DD_API_KEY`` with your actual configurations.

  
