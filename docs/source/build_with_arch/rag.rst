.. _arch_rag_guide:

RAG Apps
========

The following section describes how Arch can help you build faster, smarter and more accurate
Retrieval-Augmented Generation (RAG) applications, including fast and accurate RAG in multi-turn
converational scenarios.

What is Retrieval-Augmented Generation (RAG)?
---------------------------------------------
RAG applications combine retrieval-based methods with generative AI models to provide more accurate,
contextually relevant, and reliable outputs. These applications leverage external data sources to augment
the capabilities of Large Language Models (LLMs), enabling them to retrieve and integrate specific information
rather than relying solely on the LLM's internal knowledge.

Parameter Extraction for RAG
----------------------------

To build RAG (Retrieval Augmented Generation) applications, you can configure prompt targets with parameters,
enabling Arch to retrieve critical information in a structured way for processing. This approach improves the
retrieval quality and speed of your application. By extracting parameters from the conversation, you can pull
the appropriate chunks from a vector database or SQL-like data store to enhance accuracy. With Arch, you can
streamline data retrieval and processing to build more efficient and precise RAG applications.

Step 1: Define Prompt Targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: includes/rag/prompt_targets.yaml
    :language: yaml
    :caption: Prompt Targets
    :linenos:

Step 2: Process Request Parameters in Flask
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the prompt targets are configured as above, handling those parameters is

.. literalinclude:: includes/rag/parameter_handling.py
    :language: python
    :caption: Parameter handling with Flask
    :linenos:

Multi-Turn RAG (Follow-up Questions)
-------------------------------------
Developers often `struggle <https://www.reddit.com/r/LocalLLaMA/comments/18mqwg6/best_practice_for_rag_with_followup_chat/>`_ to efficiently handle
``follow-up`` or ``clarification`` questions. Specifically, when users ask for changes or additions to previous responses, it requires developers to
re-write prompts using LLMs with precise prompt engineering techniques. This process is slow, manual, error prone and adds signifcant latency to the
user experience. Arch

Arch is highly capable of accurately detecting and processing prompts in a multi-turn scenarios so that you can buil fast and accurate RAG apps in
minutes. For additional details on how to build multi-turn RAG applications please refer to our :ref:`multi-turn <arch_multi_turn_guide>` docs.
