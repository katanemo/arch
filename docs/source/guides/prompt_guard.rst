.. _prompt_guard:

Prompt Guard
================

**Prompt guard** is a security and validation layer designed to protect prompt-based systems by filtering and analyzing inputs before they reach the core processing stages.
In applications where prompts generate responses or execute specific actions based on user inputs, prompt guard minimizes risks like malicious inputs, unexpected errors, or misaligned outputs.
By adding a layer of input scrutiny, prompt guard ensures safer, more reliable, and accurate interactions in prompt-driven environments.

Why Prompt Guard
----------------

.. vale Vale.Spelling = NO

- **Input Validation**
    - **Type Enforcement**: Ensures that inputs are of the expected data types, such as integers, strings, lists, or specific formats, reducing errors from unexpected data.
    - **Value Constraints**: Restricts inputs to valid ranges, lengths, or patterns to avoid unusual or incorrect responses.

- **Prompt Sanitization**
    - **Jailbreak Prevention**: Detects and filters inputs that might attempt jailbreak attacks, like alternating LLM intended behavior, exposing the system prompt, or bypassing ethnics safety.

- **Intent Detection**
    - **Behavioral Analysis**: Analyzes prompt intent to detect if the input aligns with the function’s intended use. This can help prevent unwanted behavior, such as attempts to bypass limitations or misuse system functions.
    - **Sentiment and Tone Checking**: Examines the tone of prompts to ensure they align with application guidelines, useful in conversational systems and customer support interactions.

- **Dynamic Error Handling**
    - **Automatic Correction**: Applies error-handling techniques to suggest corrections for minor input errors, such as typos or misformatted data.
    - **Feedback Mechanism**: Provides informative error messages to users, helping them understand how to correct input mistakes or adhere to guidelines.

- **Policy Enforcement**
    - **Role-Based Filtering**: Customizes input validation based on user roles or permissions, allowing more flexibility or stricter enforcement depending on user access.
    - **Compliance Checks**: Ensures inputs meet compliance or regulatory standards, especially in fields like finance or healthcare, where prompt outputs must align with strict guidelines.


Arch-Guard
----------
In the evolving landscape of LLM-powered applications, safeguarding against prompt attacks is crucial.
These attacks involve malicious prompts crafted to manipulate the intended behavior of the model, potentially leading to undesirable outcomes.
Arch-Guard is designed to address this challenge.

What Is Arch-Guard
~~~~~~~~~~~~~~~~~~
`Arch-Guard <https://huggingface.co/collections/katanemolabs/arch-guard-6702bdc08b889e4bce8f446d>`_ is a robust classifier model specifically trained on a diverse corpus of prompt attacks.
It excels at detecting explicitly malicious prompts and assessing toxic content, providing an essential layer of security for LLM applications.

By embedding Arch-Guard within the Arch architecture, we empower developers to build robust, LLM-powered applications while prioritizing security and safety. With Arch-Guard, you can navigate the complexities of prompt management with confidence, knowing you have a reliable defense against malicious input.


Example Configuration
~~~~~~~~~~~~~~~~~~~~~
Here is an example of using Arch-Guard in Arch:

.. literalinclude:: includes/arch_config.yaml
    :language: yaml
    :linenos:
    :lines: 22-26
    :caption: Arch-Guard Example Configuration

How Arch-Guard Works
----------------------

#. **Pre-Processing Stage**

    As a request or prompt is received, Prompt Guard first performs validation, applying any type, format, or constraint checks. If any violations are detected, the input is flagged, and a tailored error message may be returned.

#. **Sanitization Stage**

    The prompt is analyzed for potentially harmful or inappropriate content, and necessary filters are applied to clean the input.

#. **Behavior Analysis**

    Next, the system assesses the intent and context of the prompt, verifying that it aligns with predefined function requirements. If the prompt raises any red flags, it can be modified or flagged for review.

#. **Error Handling and Feedback**

    If the prompt contains errors or does not meet certain criteria, the user receives immediate feedback or correction suggestions, enhancing usability and reducing the chance of repeated input mistakes.

#. **Output Control**

    After input validation and filtering, the prompt is allowed to proceed to the main processing phase. The output can also undergo a final check to ensure compliance with content guidelines or role-based policies.


Benefits of Using Prompt Guard
------------------------------

- **Enhanced Security**: Protects against injection attacks, harmful content, and misuse, securing both system and user data.

- **Increased Accuracy**: Filters out inappropriate or misaligned inputs, leading to more accurate and intended outputs.

- **Better User Experience**: Clear feedback and error correction improve user interactions by guiding them to correct input formats and constraints.

- **Regulatory Compliance**: Ensures that prompts adhere to necessary guidelines, especially for sensitive fields, minimizing the risk of regulatory breaches.


Summary
-------

Prompt guard is an essential tool for any prompt-based system that values security, accuracy, and compliance.
By implementing Prompt Guard, developers can provide a robust layer of input validation and security, leading to better-performing, reliable, and safer applications.
