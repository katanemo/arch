Life of a Request
=================

Below we describe the events in the life of a request passing through an Arch Gateway. We first
describe how Arch fits into the request path and then the internal events that take place following 
the arrival of a request at the Arch Gateway from upstream clients. We follow the request
until the corresponding dispatch downstream and the response path.

Terminology
-----------

Arch uses the following terms through its codebase and documentation:

* *LLM Providers*: a set of upstream LLMs that Arch routes/forwards calls to.
* *Upstream*: an entity connecting to Arch. This may be a local application (in a sidecar model) or
  a network node. In non-sidecar models, this is a remote client.
* *Endpoints*: A set of hosts that can recieve traffic from Arch
* *Listeners*: Arch module responsible for binding to an IP/port, accepting new TCP connections (or
  UDP datagrams) and orchestrating the downstream facing aspects of request processing.
* *Downstream*: an endpoint (network node) that Arch connects to when forwarding requests for a
  service. This may be a local application (in a sidecar model) or a network node. 

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

In practice, Arch can be deployed on the edge and as an internal load balancer between AI agents. A request path may traverse multiple Archs:

.. image:: /_static/img/network-topology-agent.jpg
   :width: 100%
   :align: center

We assume a static bootstrap configuration file for simplicity:

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
