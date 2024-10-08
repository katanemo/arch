.. _quickstart:

Quickstart
================

Follow this guide to learn how to quickly set up Arch and integrate it into your generative AI applications.


Prerequisites
----------------------------

Before you begin, ensure you have the following:

.. vale Vale.Spelling = NO

- ``Docker`` & ``Python`` installed on your system
- ``API Keys`` for LLM providers (if using external LLMs)

The fastest way to get started using Arch is to use `katanemo/arch <https://hub.docker.com/r/katanemo/arch>`_ pre-built binaries.
You can also build it from source.


Step 1: Install Arch
----------------------------
Arch's CLI allows you to manage and interact with the Arch gateway efficiently. To install the CLI, simply
run the following command:

.. code-block:: console

    $ pip install archgw

This will install the archgw command-line tool globally on your system.

.. tip::
   We recommend that developers create a new Python virtual environment to isolate dependencies before installing Arch.
   This ensures that `archgw` and its dependencies do not interfere with other packages on your system.

   To create and activate a virtual environment, you can run the following commands:

   .. code-block:: console

      $ python -m venv venv
      $ source venv/bin/activate   # On Windows, use: venv\Scripts\activate
      $ pip install archgw


Step 2: Config Arch
-------------------

Arch operates based on a configuration file where you can define LLM providers, prompt targets, and guardrails, etc.
Below is an example configuration to get you started, including:

.. vale Vale.Spelling = NO

- ``endpoints``: Specifies where Arch listens for incoming prompts.
- ``system_prompts``: Defines predefined prompts to set the context for interactions.
- ``llm_providers``: Lists the LLM providers Arch can route prompts to.
- ``prompt_guards``: Sets up rules to detect and reject undesirable prompts.
- ``prompt_targets``: Defines endpoints that handle specific types of prompts.
- ``error_target``: Specifies where to route errors for handling.

.. literalinclude:: includes/quickstart.yaml
    :language: yaml


Step 3: Start Arch Gateway
--------------------------

.. code-block:: console

    $ archgw up [path_to_config]



Next Steps
-------------------

Congratulations! You've successfully set up Arch and made your first prompt-based request. To further enhance your GenAI applications, explore the following resources:

- :ref:`Full Documentation <overview>`: Comprehensive guides and references.
- `GitHub Repository <https://github.com/katanemo/arch>`_: Access the source code, contribute, and track updates.
- `Support <https://github.com/katanemo/arch#contact>`_: Get help and connect with the Arch community .

With Arch, building scalable, fast, and personalized GenAI applications has never been easier. Dive deeper into Arch's capabilities and start creating innovative AI-driven experiences today!
