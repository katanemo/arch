.. _arch_overview_prompt_handling:

Prompts
=======

Arch's primary design point is to securely accept, process and handle prompts. To do that effectively, 
Arch heavily relies on Envoy's HTTP `connection management <https://www.envoyproxy.io/docs/envoy/v1.31.2/intro/arch_overview/http/http_connection_management>`_, 
HTTP `filters <https://www.envoyproxy.io/docs/envoy/v1.31.2/intro/arch_overview/http/http_filters>`_,  
and HTTP `routing <https://www.envoyproxy.io/docs/envoy/v1.31.2/intro/arch_overview/http/http_routing>`_ 
subsystems and utilizes its prompt handler subsystem engineered with purpose-built :ref:`LLMs <llms_in_arch>` 
to implement critical functionality on behalf of developers so that they can stay focused on the business 
logic of their generative AI applications.

Prompt Guardrails
-----------------

Arch is engineered with Arch-Guard, an industry leading security layer powered by a compact and 
high-performimg LLM that monitors incoming prompts to detect and reject jailbreak attempts and toxicity, 
ensuring that unauthorized or harmful behaviors are intercepted early in the process. Arch-Guard is the 
leading model in the industry for jailbreak and toxicity detection. Configuring guardrails is super simple. 
See example below:

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
    :linenos:
    :emphasize-lines: 24-27
    :caption: :download:`arch-getting-started.yml </_config/getting-started.yml>`

.. Note::
   As a roadmap item, Arch will expose the ability for developers to define custom guardrails via Arch-Guard-v2, 
   which woulld map set of instructions defined by the application developer to control conversational flow. To
   offer feedback on our roadmap, please


Prompt Targets
--------------

Once a prompt passes any configured guardrail checks, Arch processes the contents of the incoming conversation 
and identifies where to forwad the conversation to via its novel ``prompt targets`` primitve. Prompt targets are 
endpoints that receive prompts that are processed by Arch. For example, Arch enriches incoming prompts with 
metadata like knowing when a user's intent has changed so that you can build faster, more accurate RAG apps. 
To support agentic apps, like scheduling travel plans or sharing comments on a document - via prompts, Arch uses 
its function calling abilities to extract critical information from the incoming prompt (or a set of prompts) 
needed by a downstream backend API or function call before calling it directly. 

.. Note::
   Arch :ref:`Agent-1B <llms_in_arch>` is the dedicated agenet engineered in Arch, that extracts information from 
   a (set of) prompts and executes necessary backend API calls. This allows for efficient handling of agentic tasks, 
   such as scheduling data retrieval, by dynamically interacting with backend services. Arch-Agent-1B is the 1.3 
   billion parameter model that matches performance  with frontier models like Claude Sonnet 3.5, while being 100x 
   cheaper ($0.05M/token hosted) and 10x faster (p50 latencies of 200ms).

.. image:: /_static/img/function-calling-network-flow.jpg
   :width: 100%
   :align: center

And configuring ``prompt_targets`` is simple. See example below:

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
    :linenos:
    :emphasize-lines: 29-38
    :caption: :download:`arch-getting-started.yml </_config/getting-started.yml>`


Intent Detection and Prompt Matching:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Arch uses Natural Language Inference (NLI) and embedding-based approaches to first detect the intent of each 
incoming prompt. This intent detection phase analyzes the prompt's content and matches it against predefined 
prompt targets, ensuring that each prompt is forwarded to the most appropriate endpoint. Arch’s intent 
detection framework considers both the name and description of each prompt target, enhancing accuracy in 
forwarding decisions.

- **NLI Integration**: Natural Language Inference techniques further refine the matching process by evaluating 
  the semantic alignment between the prompt and potential targets.

- **Embedding**: By embedding the prompt and comparing it to known target vectors, Arch effectively 
  identifies the closest match, ensuring that the prompt is handled by the correct downstream service.


Prompting LLMs
--------------
Arch is designed as front/edge gateway, but the same software is used to proxy outbound LLM calls