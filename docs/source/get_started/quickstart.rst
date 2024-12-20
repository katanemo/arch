.. _quickstart:

Quickstart
================

Follow this guide to learn how to quickly set up Arch and integrate it into your generative AI applications.


Prerequisites
-------------

Before you begin, ensure you have the following:

1. `Docker System <https://docs.docker.com/get-started/get-docker/>`_ (v24)
2. `Docker compose <https://docs.docker.com/compose/install/>`_ (v2.29)
3. `Python <https://www.python.org/downloads/>`_ (v3.12)

Arch's CLI allows you to manage and interact with the Arch gateway efficiently. To install the CLI, simply run the following command:

.. tip::

   We recommend that developers create a new Python virtual environment to isolate dependencies before installing Arch. This ensures that ``archgw`` and its dependencies do not interfere with other packages on your system.

.. code-block:: console

   $ python -m venv venv
   $ source venv/bin/activate   # On Windows, use: venv\Scripts\activate
   $ pip install archgw==0.1.7


Build AI Agent with Arch Gateway
--------------------------------

In the following quickstart, we will show you how easy it is to build an AI agent with the Arch gateway. We will build a currency exchange agent using the following simple steps. For this demo, we will use `https://api.frankfurter.dev/` to fetch the latest prices for currencies and assume USD as the base currency.

Step 1. Create arch config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``arch_config.yaml`` file with the following content:

.. code-block:: yaml

   version: v0.1

   listener:
     address: 0.0.0.0
     port: 10000
     message_format: huggingface
     connect_timeout: 0.005s

   llm_providers:
     - name: gpt-4o
       access_key: $OPENAI_API_KEY
       provider: openai
       model: gpt-4o

   system_prompt: |
     You are a helpful assistant.

   prompt_guards:
     input_guards:
       jailbreak:
         on_exception:
           message: Looks like you're curious about my abilities, but I can only provide assistance for currency exchange.

   prompt_targets:
     - name: currency_exchange
       description: Get currency exchange rate from USD to other currencies
       parameters:
         - name: currency_symbol
           description: the currency that needs conversion
           required: true
           type: str
           in_path: true
       endpoint:
         name: frankfurther_api
         path: /v1/latest?base=USD&symbols={currency_symbol}
       system_prompt: |
         You are a helpful assistant. Show me the currency symbol you want to convert from USD.

     - name: get_supported_currencies
       description: Get list of supported currencies for conversion
       endpoint:
         name: frankfurther_api
         path: /v1/currencies

   endpoints:
     frankfurther_api:
       endpoint: api.frankfurter.dev:443
       protocol: https

Step 2. Start arch gateway with currency conversion config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sh

   $ archgw up arch_config.yaml
   2024-12-05 16:56:27,979 - cli.main - INFO - Starting archgw cli version: 0.1.5
   ...
   2024-12-05 16:56:28,485 - cli.utils - INFO - Schema validation successful!
   2024-12-05 16:56:28,485 - cli.main - INFO - Starting arch model server and arch gateway
   ...
   2024-12-05 16:56:51,647 - cli.core - INFO - Container is healthy!

Once the gateway is up, you can start interacting with it at port 10000 using the OpenAI chat completion API.

Some sample queries you can ask include: ``what is currency rate for gbp?`` or ``show me list of currencies for conversion``.

Step 3. Interacting with gateway using curl command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is a sample curl command you can use to interact:

.. code-block:: bash

   $ curl --header 'Content-Type: application/json' \
     --data '{"messages": [{"role": "user","content": "what is exchange rate for gbp"}]}' \
     http://localhost:10000/v1/chat/completions | jq ".choices[0].message.content"

   "As of the date provided in your context, December 5, 2024, the exchange rate for GBP (British Pound) from USD (United States Dollar) is 0.78558. This means that 1 USD is equivalent to 0.78558 GBP."

And to get the list of supported currencies:

.. code-block:: bash

   $ curl --header 'Content-Type: application/json' \
     --data '{"messages": [{"role": "user","content": "show me list of currencies that are supported for conversion"}]}' \
     http://localhost:10000/v1/chat/completions | jq ".choices[0].message.content"

   "Here is a list of the currencies that are supported for conversion from USD, along with their symbols:\n\n1. AUD - Australian Dollar\n2. BGN - Bulgarian Lev\n3. BRL - Brazilian Real\n4. CAD - Canadian Dollar\n5. CHF - Swiss Franc\n6. CNY - Chinese Renminbi Yuan\n7. CZK - Czech Koruna\n8. DKK - Danish Krone\n9. EUR - Euro\n10. GBP - British Pound\n11. HKD - Hong Kong Dollar\n12. HUF - Hungarian Forint\n13. IDR - Indonesian Rupiah\n14. ILS - Israeli New Sheqel\n15. INR - Indian Rupee\n16. ISK - Icelandic Króna\n17. JPY - Japanese Yen\n18. KRW - South Korean Won\n19. MXN - Mexican Peso\n20. MYR - Malaysian Ringgit\n21. NOK - Norwegian Krone\n22. NZD - New Zealand Dollar\n23. PHP - Philippine Peso\n24. PLN - Polish Złoty\n25. RON - Romanian Leu\n26. SEK - Swedish Krona\n27. SGD - Singapore Dollar\n28. THB - Thai Baht\n29. TRY - Turkish Lira\n30. USD - United States Dollar\n31. ZAR - South African Rand\n\nIf you want to convert USD to any of these currencies, you can select the one you are interested in."


Use Arch Gateway as LLM Router
------------------------------

Step 1. Create arch config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arch operates based on a configuration file where you can define LLM providers, prompt targets, guardrails, etc. Below is an example configuration that defines OpenAI and Mistral LLM providers.

Create ``arch_config.yaml`` file with the following content:

.. code-block:: yaml

   version: v0.1

   listener:
     address: 0.0.0.0
     port: 10000
     message_format: huggingface
     connect_timeout: 0.005s

   llm_providers:
     - name: gpt-4o
       access_key: $OPENAI_API_KEY
       provider: openai
       model: gpt-4o
       default: true

     - name: ministral-3b
       access_key: $MISTRAL_API_KEY
       provider: mistral
       model: ministral-3b-latest

Step 2. Start arch gateway
~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the config file is created, ensure that you have environment variables set up for ``MISTRAL_API_KEY`` and ``OPENAI_API_KEY`` (or these are defined in a ``.env`` file).

Start the Arch gateway:

.. code-block:: console

   $ archgw up arch_config.yaml
   2024-12-05 11:24:51,288 - cli.main - INFO - Starting archgw cli version: 0.1.5
   2024-12-05 11:24:51,825 - cli.utils - INFO - Schema validation successful!
   2024-12-05 11:24:51,825 - cli.main - INFO - Starting arch model server and arch gateway
   ...
   2024-12-05 11:25:16,131 - cli.core - INFO - Container is healthy!

Step 3: Interact with LLM
~~~~~~~~~~~~~~~~~~~~~~~~~

Step 3.1: Using OpenAI Python client
++++++++++++++++++++++++++++++++++++

Make outbound calls via the Arch gateway:

.. code-block:: python

   from openai import OpenAI

   # Use the OpenAI client as usual
   client = OpenAI(
     # No need to set a specific openai.api_key since it's configured in Arch's gateway
     api_key='--',
     # Set the OpenAI API base URL to the Arch gateway endpoint
     base_url="http://127.0.0.1:12000/v1"
   )

   response = client.chat.completions.create(
       # we select model from arch_config file
       model="--",
       messages=[{"role": "user", "content": "What is the capital of France?"}],
   )

   print("OpenAI Response:", response.choices[0].message.content)

Step 3.2: Using curl command
++++++++++++++++++++++++++++

.. code-block:: bash

   $ curl --header 'Content-Type: application/json' \
     --data '{"messages": [{"role": "user","content": "What is the capital of France?"}]}' \
     http://localhost:12000/v1/chat/completions

   {
     ...
     "model": "gpt-4o-2024-08-06",
     "choices": [
       {
         ...
         "message": {
           "role": "assistant",
           "content": "The capital of France is Paris.",
         },
       }
     ],
   }

You can override model selection using the ``x-arch-llm-provider-hint`` header. For example, to use Mistral, use the following curl command:

.. code-block:: bash

   $ curl --header 'Content-Type: application/json' \
     --header 'x-arch-llm-provider-hint: ministral-3b' \
     --data '{"messages": [{"role": "user","content": "What is the capital of France?"}]}' \
     http://localhost:12000/v1/chat/completions

   {
     ...
     "model": "ministral-3b-latest",
     "choices": [
       {
         "message": {
           "role": "assistant",
           "content": "The capital of France is Paris. It is the most populous city in France and is known for its iconic landmarks such as the Eiffel Tower, the Louvre Museum, and Notre-Dame Cathedral. Paris is also a major global center for art, fashion, gastronomy, and culture.",
         },
         ...
       }
     ],
     ...
   }


Next Steps
==========

Congratulations! You've successfully set up Arch and made your first prompt-based request. To further enhance your GenAI applications, explore the following resources:

- :ref:`Full Documentation <overview>`: Comprehensive guides and references.
- `GitHub Repository <https://github.com/katanemo/arch>`_: Access the source code, contribute, and track updates.
- `Support <https://github.com/katanemo/arch#contact>`_: Get help and connect with the Arch community .

With Arch, building scalable, fast, and personalized GenAI applications has never been easier. Dive deeper into Arch's capabilities and start creating innovative AI-driven experiences today!
