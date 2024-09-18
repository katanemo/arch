Life of a Request
=================

Below we describe the events in the life of a request passing through an Arch gateway. We first
describe how Arch fits into the request path and then the internal events that take place following 
the arrival of a request at Arch from clients. We follow the request until the corresponding dispatch 
downstream and the response path.

Terminology
------------

Arch uses the following terms through its codebase and documentation:


* *Listeners*: Arch module responsible for binding to an IP/port, accepting new HTTP connections and orchestrating 
  the downstream facing aspects of request processing.
* *Downstream*: an entity connecting to Arch. This may be a local application (in a sidecar model) or
  a network node. In non-sidecar models, this is a remote client.
* *LLM Providers*: a set of upstream LLMs that Arch routes/forwards calls to 
* *Upstream*: A set of hosts that can recieve traffic from an instance of the Arch gateway.


Network topology
----------------

How a request flows through the components in a network (including Arch) depends on the network’s
topology. Arch can be used in a wide variety of networking topologies. We focus on the inner
operation of Arch below, but briefly we address how Arch relates to the rest of the network in
this section.

* Ingress listeners take requests from upstream clients like a web UI or clients that forward prompts to you local application
  Responses from the local application flow back through Arch to the downstream.

* Egress listeners take requests from the local application and forward them to LLMs. These receiving nodes 
  will also be typically running Arch and accepting the request via their ingress listeners.

.. image:: /_static/img/network-topology-app-server.jpg
   :width: 100%
   :align: center

In practice, Arch can be deployed on the edge and as an internal load balancer between AI agents. A request path may 
traverse multiple Arch gateways:

.. image:: /_static/img/network-topology-agent.jpg
   :width: 100%
   :align: center

Configuration
-------------

We only support a static bootstrap configuration file for simplicity today:

.. literalinclude:: /_config/getting-started.yml
    :language: yaml

    

Request Flow
-------------

Overview
^^^^^^^^
A brief outline of the life cycle of a request and response using the example configuration above:

1. **TCP Connection Establishment**:  
   A TCP connection from downstream is accepted by an Arch listener running on a worker thread. The listener filter chain provides SNI and other pre-TLS information. The transport socket, typically TLS, decrypts incoming data for processing.

2. **Prompt Guardrails Check**:  
   Arch first checks the incoming prompts for guardrails such as jailbreak attempts and toxicity. This ensures that harmful or unwanted behaviors are detected early in the request processing pipeline.

3. **Intent Matching**:  
   The decrypted data stream is deframed by the HTTP/2 codec in Arch's HTTP connection manager. Arch performs intent matching using the name and description of the defined prompt targets, determining which endpoint should handle the prompt.

4. **Parameter Gathering with Arch-FC1B**:  
   If a prompt target requires specific parameters, Arch engages Arch-FC1B to extract the necessary details from the incoming prompt(s). This process gathers the critical information needed for downstream API calls.

5. **API Call Execution**:  
   Arch routes the prompt to the appropriate backend API or function call. If an endpoint cluster is identified, load balancing is performed, circuit breakers are checked, and the request is proxied to the upstream endpoint. For more details on routing and load balancing, refer to the [Envoy routing documentation](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/intro/arch_overview).

6. **Summarization by Upstream LLM**:  
   By default, if no specific endpoint processing is needed, the prompt is sent to an upstream LLM for summarization. This ensures that responses are concise and relevant, enhancing user experience in RAG (Retrieval-Augmented Generation) and agentic applications.

7. **Error Handling and Forwarding**:  
   Errors encountered during processing, such as failed function calls or guardrail detections, are forwarded to designated error targets. Error details are communicated through specific headers to the application:
   
   - ``X-Function-Error-Code``: Code indicating the type of function call error.
   - ``X-Prompt-Guard-Error-Code``: Code specifying violations detected by prompt guardrails.
   - Additional headers carry messages and timestamps to aid in debugging and logging.

8. **Response Handling**:  
   The upstream endpoint’s TLS transport socket encrypts the response, which is then proxied back downstream. Responses pass through HTTP filters in reverse order, ensuring any necessary processing or modification before final delivery.