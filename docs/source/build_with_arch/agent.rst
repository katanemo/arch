.. _arch_agent_guide:

Agentic Workflow
==============================

Arch helps you easily personalize your applications by calling application-specific (API) functions
via user prompts. This involves any predefined functions or APIs you want to expose to users to perform tasks,
gather information, or manipulate data. This capability is generally referred to as **function calling**, where
you have the flexibility to support “agentic” apps tailored to specific use cases - from updating insurance
claims to creating ad campaigns - via prompts.

Arch analyzes prompts, extracts critical information from prompts, engages in lightweight conversation with
the user to gather any missing parameters and makes API calls so that you can focus on writing business logic.
Arch does this via its purpose-built :ref:`Arch-Function <function_calling>` - the fastest (200ms p90 - 10x faser than GPT-4o)
and cheapest (100x than GPT-40) function-calling LLM that matches performance with frontier models.

.. image:: includes/agent/function-calling-flow.jpg
   :width: 100%
   :align: center


Single Function Call
--------------------
In the most common scenario, users will request a single action via prompts, and Arch efficiently processes the
request by extracting relevant parameters, validating the input, and calling the designated function or API. Here
is how you would go about enabling this scenario with Arch:

Step 1: Define Prompt Targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: includes/agent/function-calling-agent.yaml
    :language: yaml
    :linenos:
    :emphasize-lines: 21-34
    :caption: Prompt Target Example Configuration

Step 2: Process Request Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the prompt targets are configured as above, handling those parameters is

.. literalinclude:: includes/agent/parameter_handling.py
    :language: python
    :linenos:
    :caption: Parameter handling with Flask

Parallel & Multiple Function Calling
------------------------------------
In more complex use cases, users may request multiple actions or need multiple APIs/functions to be called
simultaneously or sequentially. With Arch, you can handle these scenarios efficiently using parallel or multiple
function calling. This allows your application to engage in a broader range of interactions, such as updating
different datasets, triggering events across systems, or collecting results from multiple services in one prompt.

Arch-FC1B is built to manage these parallel tasks efficiently, ensuring low latency and high throughput, even
when multiple functions are invoked. It provides two mechanisms to handle these cases:

Step 1: Define Prompt Targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When enabling multiple function calling, define the prompt targets in a way that supports multiple functions or
API calls based on the user's prompt. These targets can be triggered in parallel or sequentially, depending on
the user's intent.

Example of Multiple Prompt Targets in YAML:

.. literalinclude:: includes/agent/function-calling-agent.yaml
    :language: yaml
    :linenos:
    :emphasize-lines: 21-34
    :caption: Prompt Target Example Configuration
