.. _arch_terminology:

Terminology
============

A few definitions before we dive into the main architecture documentation. Arch borrows from Envoy's terminology
to keep things consistent in logs, traces and in code.

**Downstream(Ingress)**: An downstream client (web application, etc.) connects to Arch, sends prompts, and receives responses.

**Upstream(Egress)**: An upstream host that receives connections and prompts from Arch, and returns context or responses for a prompt

.. image:: /_static/img/network-topology-ingress-egress.jpg
   :width: 100%
   :align: center

