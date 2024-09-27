.. _llm_providers:

LLM Provider
------------

``llm_provider`` is a top-level primitive in Arch, helping developers centrally define, secure, observe, 
and manage the usage of of their LLMs. Arch builds on Envoy's reliable `cluster subsystem <https://www.envoyproxy.io/docs/envoy/v1.31.2/intro/arch_overview/upstream/cluster_manager>`_ 
to manage egress traffic to LLMs, which includes intelligent routing, retry and fail-over mechanisms, 
ensuring high availability and fault tolerance. This abstraction also enables developers to seamlessly switching between LLM providers or upgrade LLM versions, simplifying the integration and scaling of LLMs across 
applications.


Below is an example of how you can configure ``llm_providers`` with an instance of an Arch gateway.

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
    :linenos:
    :lines: 1-20
    :emphasize-lines: 11-18
    :caption: :download:`arch-getting-started.yml </_config/getting-started.yml>`

.. Note::
    When you start Arch, it creates a listener port for egress traffic based on the presence of ``llm_providers`` 
    configuration section in the ``prompt_config.yml`` file. Arch binds itself to a local address such as 
    ``127.0.0.1:9000/v1`` or a DNS-based address like ``arch.local:9000/v1`` for egress traffic. 

Arch also offers vendor-agnostic SDKs and libraries to make LLM calls to API-based LLM providers (like OpenAI, 
Anthropic, Mistral, Cohere, etc.) and supports calls to OSS LLMs that are hosted on your infrastructure. Arch 
abstracts the complexities of integrating with different LLM providers, providing a unified interface for making 
calls, handling retries, managing rate limits, and ensuring seamless integration with cloud-based and on-premise 
LLMs. Simply configure the details of the LLMs your application will use, and Arch offers a unified interface to 
make outbound LLM calls. 

Example: Using the Arch Python SDK
----------------------------------

.. code-block:: python

   from arch_client import ArchClient

   # Initialize the Arch client
   client = ArchClient(base_url="http://127.0.0.1:9000/v1")

   # Define your LLM provider and prompt
   model_id = "openai"
   prompt = "What is the capital of France?"

   # Send the prompt to the LLM through Arch
   response = client.completions.create(llm_provider=llm_provider, prompt=prompt)

   # Print the response
   print("LLM Response:", response)