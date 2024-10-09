<p>
  <img src="docs/source/_static/img/arch-logo.png" alt="Arch Gateway Logo" title="Arch Gateway Logo">
</p>

<h2>Build fast, robust, and personalized GenAI apps (agents, assistants, etc.)</h2>

Arch is an intelligent [Layer 7](https://www.cloudflare.com/learning/ddos/what-is-layer-7/) gateway designed for generative AI apps, AI agents, and co-pilots that work with prompts. Engineered with purpose-built LLMs, Arch handles the critical but undifferentiated tasks related to the handling and processing of prompts, including detecting and rejecting [jailbreak](https://github.com/verazuo/jailbreak_llms) attempts, intelligently calling "backend" APIs to fulfill the user's request represented in a prompt, routing to and offering disaster recovery between upstream LLMs, and managing the observability of prompts and LLM interactions in a centralized way.

 Arch is built on (and by the core contributors of) the wildly popular and robust [Envoy Proxy](https://www.envoyproxy.io/) with the belief that:

*Prompts are nuanced and opaque user requests, which require the same capabilities as traditional HTTP requests including secure handling, intelligent routing, robust observability, and integration with backend (API) systems for personalization – all outside business logic.*

**Core Features**:
  - Built on [Envoy](https://envoyproxy.io): Arch runs alongside application servers build on top of Envoy's proven HTTP management and scalability features to handle ingress and egreess prompts and LLM traffic
  - Engineered with purpose-built [(fast) LLMs](https://huggingface.co/collections/katanemo/arch-function-66f209a693ea8df14317ad68): Arch is optimized for sub-billion parameter LLMs to handle fast, cost-effective, and accurate prompt-based tasks like function/API calling.
  - Prompt [Guardrails](https://huggingface.co/collections/katanemo/arch-guard-6702bdc08b889e4bce8f446d): Arch centralizes prompt guardrails to prevent jailbreak attempts and ensure safe user interactions without writing extra code.
  - Traffic Management: Arch manages LLM calls, offering smart retries, automatic cutover, and resilient upstream connections for continuous availability.
  - Open Observability: Arch uses the W3C Trace Context standard to enable complete request tracing across applications, ensuring compatibility with observability tools, and provides metrics to monitor latency, token usage, and error rates, helping optimize AI application performance.
  - [Coming Soon] Intent-Markers: Arch helps developers detect when users shift their intent, improving response relevance, token cost, and speed.

**Jump to our [docs](https://docs.archgw.com)** to learn more about how you can use Arch to improve the speed, robustneess and personalization of your GenAI apps

# Contact
To get in touch with us, please join our [discord server](https://discord.gg/rbjqVbpa). We will be monitoring that actively and offering support there.

# Demos
* [Function Calling](demos/function_calling/README.md) -Showcases critical function calling cabaility
* [Insurance Agent](demos/insurance_agent/README.md) -Build a full insurance agent with arch
* [Network Agent](demos/network_agent/README.md) - Build a networking co-pilot/agent agent with arch

# Quickstart

Follow this guide to learn how to quickly set up Arch and integrate it into your generative AI applications.

## Prerequisites

Before you begin, ensure you have the following:

- `Docker` & `Python` installed on your system
- `API Keys` for LLM providers (if using external LLMs)

The fastest way to get started using Arch is to use [katanemo/arch](https://hub.docker.com/r/katanemo/arch) pre-built binaries.
You can also build it from source.

## Step 1: Install Arch

Arch's CLI allows you to manage and interact with the Arch gateway efficiently. To install the CLI, simply run the following command:
Tip: We recommend that developers create a new Python virtual environment to isolate dependencies before installing Arch. This ensures that archgw and its dependencies do not interfere with other packages on your system.


```console
$ python -m venv venv
$ source venv/bin/activate   # On Windows, use: venv\Scripts\activate
$ pip install archgw
```

## Step 2: Configure Arch with your application

Arch operates based on a configuration file where you can define LLM providers, prompt targets, guardrails, etc.
Below is an example configuration to get you started:

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
## Step 3: Using OpenAI Client with Arch as an Egress Gateway

Make outbound calls via Arch

```python
import openai

# Set the OpenAI API base URL to the Arch gateway endpoint
openai.api_base = "http://127.0.0.1:51001/v1"

# No need to set openai.api_key since it's configured in Arch's gateway

# Use the OpenAI client as usual
response = openai.Completion.create(
   model="text-davinci-003",
   prompt="What is the capital of France?"
)

print("OpenAI Response:", response.choices[0].text.strip())

```

## Observability


## Contribution
We would love feedback on our [Roadmap](https://github.com/orgs/katanemo/projects/1) and we welcome contributions to **Arch**!
Whether you're fixing bugs, adding new features, improving documentation, or creating tutorials, your help is much appreciated.

## How to Contribute

### 1. Fork the Repository

Fork the repository to create your own version of **Arch**:

- Navigate to the [Arch GitHub repository](https://github.com/katanemo/arch).
- Click the "Fork" button in the upper right corner.
- This will create a copy of the repository under your GitHub account.

### 2. Clone Your Fork

Once you've forked the repository, clone it to your local machine:

```bash
$ git clone https://github.com/katanemo/arch.git
$ cd arch
```

### 3. Create a branch
Use a descriptive name for your branch (e.g., fix-bug-123, add-feature-x).
```bash
$ git checkout -b <your-branch-name>
```

### 4. Make Your changes

Make your changes in the relevant files. If you're adding new features or fixing bugs, please include tests where applicable.

### 5. Test your changes
```bash
cd arch
cargo test
```

### 6. Push changes, and create a Pull request

Go back to the original Arch repository, and you should see a "Compare & pull request" button. Click that to submit a Pull Request (PR). In your PR description, clearly explain the changes you made and why they are necessary.

We will review your pull request and provide feedback. Once approved, your contribution will be merged into the main repository!

Contribution Guidelines

    Ensure that all existing tests pass.
    Write clear commit messages.
    Add tests for any new functionality.
    Follow the existing coding style.
    Update documentation as needed.

To get in touch with us, please join our [discord server](https://discord.gg/rbjqVbpa). We will be monitoring that actively and offering support there.
