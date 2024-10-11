.. _prompt_target:

Prompt Target
==============

**Prompt Targets** are a fundamental component of Arch, enabling developers to define how different types of user prompts are processed and routed within their generative AI applications.
This section provides an in-depth look at prompt targets, including their purpose, configuration, usage, and best practices to help you effectively leverage this feature in your projects.

What Are Prompt Targets?
------------------------
Prompt targets are predefined endpoints within Arch that handle specific types of user prompts.
They act as the bridge between user inputs and your backend services or APIs, enabling Arch to route, process, and manage prompts efficiently.
By defining prompt targets, you can separate your application's business logic from the complexities of prompt processing, ensuring a cleaner and more maintainable codebase.


.. table::
    :width: 100%

    ====================    ============================================
    **Capability**          **Description**
    ====================    ============================================
    Intent Recognition      Identify the purpose of a user prompt.
    Parameter Extraction    Extract necessary data from the prompt.
    API Invocation          Call relevant backend services or functions.
    Response Handling       Process and return responses to the user.
    ====================    ============================================

Key Features
~~~~~~~~~~~~

Below are the key features of prompt targets that empower developers to build efficient, scalable, and personalized GenAI solutions:

- **Modular Design**: Define multiple prompt targets to handle diverse functionalities.
- **Parameter Management**: Specify required and optional parameters for each target.
- **Function Integration**: Seamlessly connect prompts to backend APIs or functions.
- **Error Handling**: Direct errors to designated handlers for streamlined troubleshooting.
- **Metadata Enrichment**: Attach additional context to prompts for enhanced processing.

Configuring Prompt Targets
--------------------------
Configuring prompt targets involves defining them in Arch's configuration file.
Each Prompt target specifies how a particular type of prompt should be handled, including the endpoint to invoke and any parameters required.

Basic Configuration
~~~~~~~~~~~~~~~~~~~

A prompt target configuration includes the following elements:

.. vale Vale.Spelling = NO

- ``name``: A unique identifier for the prompt target.
- ``description``: A brief explanation of what the prompt target does.
- ``endpoint``: The API endpoint or function that handles the prompt.
- ``parameters`` (Optional): A list of parameters to extract from the prompt.

Defining Parameters
~~~~~~~~~~~~~~~~~~~
Parameters are the pieces of information that Arch needs to extract from the user's prompt to perform the desired action.
Each parameter can be marked as required or optional.
Here is a full list of parameter attributes that Arch can support:

.. table::
    :width: 100%

    ====================      ============================================================================
    **Attribute**             **Description**
    ====================      ============================================================================
    ``name``                  Specifies identifier of parameters
    ``type``                  Specifies the data type of the parameter.
    ``description``           Provides a human-readable explanation of the parameter's purpose.
    ``required``              Indicates whether the parameter is mandatory or optional
    ``default``               Specifies a default value for the parameter if not provided by the user.
    ``items``                 Used in the context of arrays to define the schema of items within an array.
    ``format``                Specifies a format for the parameter value, e.g., date and email
    ``enum``                  Lists the allowable values for the parameter.
    ``minimum``               Defines the minimum acceptable value for numeric parameters.
    ``maximum``               Specifies the maximum acceptable value for numeric parameters.
    ====================      ============================================================================

Example Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    prompt_targets:
      - name: get_weather
        description: Get the current weather for a location
        parameters:
          - name: location
            description: The city and state, e.g. San Francisco, New York
            type: str
            required: true
          - name: unit
            description: The unit of temperature
            type: str
            default: fahrenheit
            enum: [celsius, fahrenheit]
        endpoint:
          name: api_server
          path: /weather


Routing Logic
-------------
Prompt targets determine where and how user prompts are processed.
Arch uses intelligent routing logic to ensure that prompts are directed to the appropriate targets based on their intent and context.

Default Targets
~~~~~~~~~~~~~~~
For general-purpose prompts that do not match any specific prompt target, Arch routes them to a designated default target.
This is useful for handling open-ended queries like document summarization or information extraction.

Intent Matching
~~~~~~~~~~~~~~~
Arch analyzes the user's prompt to determine its intent and matches it with the most suitable prompt target based on the name and description defined in the configuration.

For example:

.. code-block:: bash

  Prompt: "Can you reboot the router?"
  Matching Target: reboot_device (based on description matching "reboot devices")


Summary
--------
Prompt targets are essential for defining how user prompts are handled within your generative AI applications using Arch.
By carefully configuring prompt targets, you can ensure that prompts are accurately routed, necessary parameters are extracted, and backend services are invoked seamlessly.
This modular approach not only simplifies your application's architecture but also enhances scalability, maintainability, and overall user experience.
