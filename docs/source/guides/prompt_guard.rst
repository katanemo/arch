.. _prompt_guard:

Prompt Guard
=============

**Prompt guard** is a security and validation feature offered in Arch to protect agents, by filtering and analyzing prompts before they reach your application logic.
In applications where prompts generate responses or execute specific actions based on user inputs, prompt guard minimizes risks like malicious inputs (or misaligned outputs).
By adding a layer of input scrutiny, prompt guards ensures safer, more reliable, and accurate interactions with agents.

Why Prompt Guard
----------------

.. vale Vale.Spelling = NO

- **Prompt Sanitization via Arch-Guard**
    - **Jailbreak Prevention**: Detects and filters inputs that might attempt jailbreak attacks, like alternating LLM intended behavior, exposing the system prompt, or bypassing ethnics safety.

- **Dynamic Error Handling**
    - **Automatic Correction**: Applies error-handling techniques to suggest corrections for minor input errors, such as typos or misformatted data.
    - **Feedback Mechanism**: Provides informative error messages to users, helping them understand how to correct input mistakes or adhere to guidelines.

.. Note::
    Today, Arch offers support for jailbreak via Arch-Guard. We will be adding support for additional guards in Q1, 2025 (including response guardrails)

What Is Arch-Guard
~~~~~~~~~~~~~~~~~~
`Arch-Guard <https://huggingface.co/collections/katanemo/arch-guard-6702bdc08b889e4bce8f446d>`_ is a robust classifier model specifically trained on a diverse corpus of prompt attacks.
It excels at detecting explicitly malicious prompts, providing an essential layer of security for LLM applications.

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

    As a request or prompt is received, Arch Guard first performs validation. If any violations are detected, the input is flagged, and a tailored error message may be returned.

#. **Error Handling and Feedback**

    If the prompt contains errors or does not meet certain criteria, the user receives immediate feedback or correction suggestions, enhancing usability and reducing the chance of repeated input mistakes.

Benefits of Using Arch Guard
------------------------------

- **Enhanced Security**: Protects against injection attacks, harmful content, and misuse, securing both system and user data.

- **Better User Experience**: Clear feedback and error correction improve user interactions by guiding them to correct input formats and constraints.


Summary
-------

Prompt guard is an essential tool for any prompt-based system that values security, accuracy, and compliance.
By implementing Prompt Guard, developers can provide a robust layer of input validation and security, leading to better-performing, reliable, and safer applications.
