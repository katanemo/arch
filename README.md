<p>
  <img src="docs/source/_static/img/arch-logo.png" alt="Arch Gateway Logo" title="Arch Gateway Logo">
</p>

<h2>Build fast, robust, and personalized GenAI apps (agents, assistants, etc.)</h2>

Arch is an intelligent [Layer 7](https://www.cloudflare.com/learning/ddos/what-is-layer-7/) gateway designed for generative AI apps, AI agents, and co-pilots that work with prompts. Engineered with purpose-built LLMs, Arch handles the critical but undifferentiated tasks related to the handling and processing of prompts, including detecting and rejecting [jailbreak](https://github.com/verazuo/jailbreak_llms) attempts, intelligently calling "backend" APIs to fulfill the user's request represented in a prompt, routing to and offering disaster recovery between upstream LLMs, and managing the observability of prompts and LLM interactions in a centralized way.

 Arch is built on (and by the core contributors of) the wildly popular and robust [Envoy Proxy](https://www.envoyproxy.io/) with the belief that:

*Prompts are nuanced and opaque user requests, which require the same capabilities as traditional HTTP requests including secure handling, intelligent routing, robust observability, and integration with backend (API) systems for personalization – all outside business logic.*

# Contact
To get in touch with us, please join our [discord server](https://discord.gg/rbjqVbpa). We will be monitoring that actively.

# Quickstart

Follow this guide to learn how to quickly set up Arch and integrate it into your generative AI applications.

## Prerequisites

Before you begin, ensure you have the following:

- `Docker` & `Python` installed on your system
- `API Keys` for LLM providers (if using external LLMs)

The fastest way to get started using Arch is to use [katanemo/arch](https://hub.docker.com/r/katanemo/arch) pre-built binaries.
You can also build it from source.

## Step 1: Install Arch

Arch's CLI allows you to manage and interact with the Arch gateway efficiently. To install the CLI, simply
run the following command:

Tip: We recommend that developers create a new Python virtual environment to isolate dependencies before installing Arch. This ensures that archgw and its dependencies do not interfere with other packages on your system.

```console
$ python -m venv venv
$ source venv/bin/activate   # On Windows, use: venv\Scripts\activate
$ pip install archgw
```

## Step 2: Configure Arch with your application

Arch operates based on a configuration file where you can define LLM providers, prompt targets, guardrails, etc. Below is an example configuration to get you started, including:

- `endpoints`: Specifies where Arch listens for incoming prompts.
- `system_prompts`: Defines predefined prompts to set the context for interactions.
- `llm_providers`: Lists the LLM providers Arch can route prompts to.
- `prompt_guards`: Sets up rules to detect and reject undesirable prompts.
- `prompt_targets`: Defines endpoints that handle specific types of prompts.

```yaml
version: v0.1

listen:
  address: 0.0.0.0 # or 127.0.0.1
  port: 10000
  # Defines how Arch should parse the content from application/json or text/pain Content-type in the http request
  message_format: huggingface

# Centralized way to manage LLMs, manage keys, retry logic, failover and limits in a central way
llm_providers:
  - name: OpenAI
    provider: openai
    access_key: OPENAI_API_KEY
    model: gpt-4o
    default: true
    stream: true

# default system prompt used by all prompt targets
system_prompt: You are a network assistant that just offers facts; not advice on manufacturers or purchasing decisions.

prompt_targets:
  - name: reboot_devices
    description: Reboot specific devices or device groups

    path: /agent/device_reboot
    parameters:
      - name: device_ids
        type: list
        description: A list of device identifiers (IDs) to reboot.
        required: false
      - name: device_group
        type: str
        description: The name of the device group to reboot
        required: false

# Arch creates a round-robin load balancing between different endpoints, managed via the cluster subsystem.
endpoints:
  app_server:
    # value could be ip address or a hostname with port
    # this could also be a list of endpoints for load balancing
    # for example endpoint: [ ip1:port, ip2:port ]
    endpoint: 127.0.0.1:80
    # max time to wait for a connection to be established
    connect_timeout: 0.005s
```

# Demos
## Complete
* [Function Calling](demos/function_calling/README.md)
  * Showcases critical function calling cabaility
* [Insurance Agent](demos/insurance_agent/README.md)
  * Build a full insurance agent with arch
* [Network Agent](demos/network_agent/README.md)
  * Build a networking co-pilot/agent agent with arch

## Pre-commit
Use instructions at [pre-commit.com](https://pre-commit.com/#install) to set it up for your machine. Once installed make sure github hooks are setup, so that when you upstream your change pre-commit hooks can run and validate your change. Follow command below to setup github hooks,

```sh
$ brew install pre-commit
$ pre-commit install
pre-commit installed at .git/hooks/pre-commit
```
