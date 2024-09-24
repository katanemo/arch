Terminology
============

A few definitions before we dive into the main architecture documentation. Arch borrows from Envoy's terminology
to keep things consistent in logs, traces and in code.

**Downstream**: An downstream client (web application, etc.) connects to Arch, sends requests, and receives responses.

**Upstream**: An upstream host receives connections and prompts from Arch, and returns context or responses for a prompt

.. image:: /_static/img/network-topology-ingress-egress.jpg
   :width: 100%
   :align: center

**Listener**: A listener is a named network location (e.g., port, address, path etc.) that Arch listens on to process prompts
before forwarding them to your application server endpoints. rch enables you to configure one listener for downstream connections
(like port 80, 443) and creates a separate internal listener for calls that initiate from your application code to LLMs.

.. Note::

   When you start Arch, you specify a listener address/port that you want to bind downstream (. But Arch uses are predefined port that you
   can use for outbound calls to LLMs and other services 127.0.0.1:10000

**Instance**: An instance of the Arch gateway. When you start Arch it creates at most two processes. One to handle Layer 7
networking operations (auth, tls, observability, etc) and the second process to serve models that enable it to make smart
decisions on how to accept, handle and forward prompts. The second process is optional, as the model serving sevice could be
hosted on a different network (an API call). But these two processes are considered a single instance of Arch.

**System Prompt**: An initial text or message that is  provided by the developer that Arch can use to call an downstream LLM
in order to generate a response from the LLM model. The system prompt can be thought of as the input or query that the model
uses to generate its response. The quality and specificity of the system prompt can have a significant impact on the relevance
and accuracy of the model's response. Therefore, it is important to provide a clear and concise system prompt that accurately
conveys the user's intended message or question.

**Prompt Targets**: Arch offers a primitive called “prompt targets” to help separate business logic from undifferentiated
work in building generative AI apps. Prompt targets are endpoints that receive prompts that are processed by Bolt.
For example, Bolt enriches incoming prompts with metadata like knowing when a request is a follow-up or clarifying prompt
so that you can build faster, more accurate RAG apps. To support agentic apps, like scheduling travel plans or sharing comments
on a document - via prompts, Bolt uses its function calling abilities to extract critical information from the incoming prompt
(or a set of prompts) needed by a downstream backend API or function call before calling it directly.

**Error Targets**: Error targets are those endpoints that receive forwarded errors from Arch when issues arise,
such as failing to properly call a function/API, detecting violations of guardrails, or encountering other processing errors.
These errors are communicated to the application via headers (X-Arch-[ERROR-TYPE]), allowing it to handle the errors gracefully and take appropriate actions.
