.. _arch_overview_prompt_handling:

Prompts
-------

Arch's primary design point is to securely accept, process and handle prompts. To do that effectively, 
Arch relies on Envoy's HTTP `connection management <https://www.envoyproxy.io/docs/envoy/v1.31.2/intro/arch_overview/http/http_connection_management>`_, 
subsystem and its prompt-handler subsystem engineered with purpose-built :ref:`LLMs <llms_in_arch>` to 
implement critical functionality on behalf of developers so that you can stay focused on business logic.

Messages
--------

Arch accepts messages directly from the body of the HTTP request in a format that follows the `Hugging Face Messages API <https://huggingface.co/docs/text-generation-inference/en/messages_api>`_. 
This design allows developers to pass a list of messages, where each message is represented as a dictionary 
containing two key-value pairs:

    - **Role**: Defines the role of the message sender, such as "user" or "assistant".
    - **Content**: Contains the actual text of the message.


Prompt Guardrails
-----------------

Arch is engineered with :ref:`Arch-Guard <llms_in_arch>`, an industry leading safety layer, powered by a 
compact and high-performimg LLM that monitors incoming prompts to detect and reject jailbreak attempts and 
several safety related concerns, ensuring that unauthorized or harmful behaviors are intercepted early in 
the process. Arch-Guard is a composite model combining work from the industry leading Meta LLama models and 
purposely-tuned models that offer exceptional overall performance. 

To add prompt guardrails, see example below: 

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
    :linenos:
    :emphasize-lines: 24-27
    :caption: :download:`arch-getting-started.yml </_config/getting-started.yml>`

.. Note::
   As a roadmap item, Arch will expose the ability for developers to define custom guardrails via Arch-Guard-v2, 
   which would enforce instructions defined by the application developer to control conversational flow. To
   offer feedback on our roadmap, please visit our `github page <https://github.com/orgs/katanemo/projects/1>`_


Prompt Targets
--------------

Once a prompt passes any configured guardrail checks, Arch processes the contents of the incoming conversation 
and identifies where to forwad the conversation to via its essential ``prompt_targets`` primitve. Prompt targets 
are endpoints that receive prompts that are processed by Arch. For example, Arch enriches incoming prompts with 
metadata like knowing when a user's intent has changed so that you can build faster, more accurate RAG apps.

Configuring ``prompt_targets`` is simple. See example below:

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
    :linenos:
    :emphasize-lines: 29-38
    :caption: :download:`arch-getting-started.yml </_config/getting-started.yml>`


Intent Detection and Prompt Matching:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arch uses fast Natural Language Inference (NLI) and embedding approaches to first detect the intent of each 
incoming prompt. This intent detection phase analyzes the prompt's content and matches it against predefined 
prompt targets, ensuring that each prompt is forwarded to the most appropriate endpoint. Arch’s intent 
detection framework considers both the name and description of each prompt target, and uses a composite matching
score between an NLI and cosine similarity to enchance accuracy in forwarding decisions.

- **Embeddings**: By embedding the prompt and comparing it to known target vectors, Arch effectively identifies 
  the closest match, ensuring that the prompt is handled by the correct downstream service.

- **NLI**: NLI techniques further refine the matching process by evaluating the semantic alignment between the 
  prompt and potential targets.

Agentic Apps via Prompt Targets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To support agentic apps, like scheduling travel plans or sharing comments on a document - via prompts, Arch uses 
its function calling abilities to extract critical information from the incoming prompt (or a set of prompts) 
needed by a downstream backend API or function call before calling it directly. For more details on how you can
build agentic applications using Arch, see our full guide :ref:`here <arch_function_calling_agentic_guide>`:

.. Note::
   Arch :ref:`Arch-FC <llms_in_arch>` is the dedicated agentic model engineered in Arch to extract information from 
   a (set of) prompts and executes necessary backend API calls. This allows for efficient handling of agentic tasks, 
   such as scheduling data retrieval, by dynamically interacting with backend services. Arch-FC is a flagship 1.3 
   billion parameter model that matches performance  with frontier models like Claude Sonnet 3.5 ang GPT-4, while 
   being 100x cheaper ($0.05M/token hosted) and 10x faster (p50 latencies of 200ms).

Prompting LLMs
--------------
Arch is a single piece of software that is designed to manage both ingress and egress prompt traffic, drawing its 
distributed proxy nature from the robust `Envoy <https://envoyproxy.io>`_. This makes it extremely efficient and capable 
of handling upstream connections to LLMs. If your application is originating code to an API-based LLM, simply use 
Arch's Python or JavaScript client SDK to send traffic to the desired LLM of choice. By sending traffic through Arch, 
you can propagate traces, manage and monitor traffic, apply rate limits, and utilize a large set of traffic management 
capabilities in a central place.

.. Attention:: 
   When you start Arch, it automatically creates a listener port for egress calls to upstream LLMs. This is based on the 
   ``llm_providers`` configuration section in the ``prompt_config.yml`` file. Arch binds itself to a local address such as 
   127.0.0.1:9000/v1  or a DNS-based address like arch.local:9000/v1 for outgoing traffic.
   
Example: Using the Arch Python SDK
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Example: Using OpenAI Client with Arch as an Egress Gateway
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python 

   import openai

   # Set the OpenAI API base URL to the Arch gateway endpoint
   openai.api_base = "http://127.0.0.1:9000/v1"

   # No need to set openai.api_key since it's configured in Arch's gateway

   # Use the OpenAI client as usual
   response = openai.Completion.create(
      model="text-davinci-003",
      prompt="What is the capital of France?"
   )

   print("OpenAI Response:", response.choices[0].text.strip())

In these examples:

    The ArchClient is used to send traffic directly through the Arch egress proxy to the LLM of your choice, such as OpenAI.
    The OpenAI client is configured to route traffic via Arch by setting the proxy to 127.0.0.1:9000, assuming Arch is 
    running locally and bound to that address and port.

This setup allows you to take advantage of Arch's advanced traffic management features while interacting with LLM APIs like OpenAI.