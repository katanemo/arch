![alt text](docs/source/_static/img/arch-logo.png)
<a href="https://www.producthunt.com/posts/arch-3?embed=true&utm_source=badge-top-post-badge&utm_medium=badge&utm_souce=badge-arch&#0045;3" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/top-post-badge.svg?post_id=565761&theme=light&period=daily" alt="Arch - Build&#0032;fast&#0044;&#0032;hyper&#0045;personalized&#0032;agents&#0032;with&#0032;intelligent&#0032;infra | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>


[![pre-commit](https://github.com/katanemo/arch/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/katanemo/arch/actions/workflows/pre-commit.yml)
[![rust tests (prompt and llm gateway)](https://github.com/katanemo/arch/actions/workflows/rust_tests.yml/badge.svg)](https://github.com/katanemo/arch/actions/workflows/rust_tests.yml)
[![e2e tests](https://github.com/katanemo/arch/actions/workflows/e2e_tests.yml/badge.svg)](https://github.com/katanemo/arch/actions/workflows/e2e_tests.yml)
[![Build and Deploy Documentation](https://github.com/katanemo/arch/actions/workflows/static.yml/badge.svg)](https://github.com/katanemo/arch/actions/workflows/static.yml)

## Build fast, observable, and personalized AI agents.

Arch is an intelligent [Layer 7](https://www.cloudflare.com/learning/ddos/what-is-layer-7/) gateway designed to protect, observe, and personalize AI agents with your APIs.

Engineered with purpose-built LLMs, Arch handles the critical but undifferentiated tasks related to the handling and processing of prompts, including detecting and rejecting [jailbreak](https://github.com/verazuo/jailbreak_llms) attempts, intelligently calling "backend" APIs to fulfill the user's request represented in a prompt, routing to and offering disaster recovery between upstream LLMs, and managing the observability of prompts and LLM API calls in a centralized way.

 Arch is built on (and by the core contributors of) [Envoy Proxy](https://www.envoyproxy.io/) with the belief that:

>Prompts are nuanced and opaque user requests, which require the same capabilities as traditional HTTP requests including secure handling, intelligent routing, robust observability, and integration with backend (API) systems for personalization – all outside business logic.*

**Core Features**:
  - Built on [Envoy](https://envoyproxy.io): Arch runs alongside application servers as a separate containerized process, and builds on top of Envoy's proven HTTP management and scalability features to handle ingress and egress traffic related to prompts and LLMs.
  - Function Calling for fast Agents and RAG apps. Engineered with purpose-built [LLMs](https://huggingface.co/collections/katanemo/arch-function-66f209a693ea8df14317ad68) to handle fast, cost-effective, and accurate prompt-based tasks like function/API calling, and parameter extraction from prompts.
  - Prompt [Guard](https://huggingface.co/collections/katanemo/arch-guard-6702bdc08b889e4bce8f446d): Arch centralizes guardrails to prevent jailbreak attempts and ensure safe user interactions without writing a single line of code.
  - Routing & Traffic Management: Arch manages LLM calls, offering smart retries, automatic cutover, and resilient upstream connections for continuous availability.
  - Observability: Arch uses the W3C Trace Context standard to enable complete request tracing across applications, ensuring compatibility with observability tools, and provides metrics to monitor latency, token usage, and error rates, helping optimize AI application performance.

**Jump to our [docs](https://docs.archgw.com)** to learn how you can use Arch to improve the speed, security and personalization of your GenAI apps.

> [!IMPORTANT]
> Today, the function calling LLM (Arch-Function) designed for the agentic and RAG scenarios is hosted free of charge in the US-central region. To offer consistent latencies and throughput, and to manage our expenses, we will enable access to the hosted version via developers keys soon, and give you the option to run that LLM locally. For more details see this issue [#258](https://github.com/katanemo/archgw/issues/258)

## Contact
To get in touch with us, please join our [discord server](https://discord.gg/pGZf2gcwEc). We will be monitoring that actively and offering support there.

## Demos
* [Weather Forecast](demos/weather_forecast/README.md) - Walk through of the core function calling capabilities of of arch gateway using weather forecasting service
* [Insurance Agent](demos/insurance_agent/README.md) - Build a full insurance agent with Arch
* [Network Agent](demos/network_agent/README.md) - Build a networking co-pilot/agent agent with Arch

## Quickstart

Follow this guide to learn how to quickly set up Arch and integrate it into your generative AI applications.

### Prerequisites

Before you begin, ensure you have the following:

- `Docker` & `Python` installed on your system
- `API Keys` for LLM providers (if using external LLMs)


### Step 1: Install Arch

Arch's CLI allows you to manage and interact with the Arch gateway efficiently. To install the CLI, simply run the following command:
Tip: We recommend that developers create a new Python virtual environment to isolate dependencies before installing Arch. This ensures that archgw and its dependencies do not interfere with other packages on your system.

Make sure you have following utilities installed before proceeding further,

1. [Docker System](https://docs.docker.com/get-started/get-docker/) (v24)
2. [Docker compose](https://docs.docker.com/compose/install/) (v2.29)
3. [Python](https://www.python.org/downloads/) (v3.12)
4. [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) (v1.8.3. *Note: only needed for local development*)


```console
$ python -m venv venv
$ source venv/bin/activate   # On Windows, use: venv\Scripts\activate
$ pip install archgw
```

### Step 2: Configure Arch with your application

Arch operates based on a configuration file where you can define LLM providers, prompt targets, guardrails, etc.
Below is an example configuration to get you started:

```yaml
version: v0.1
listener:
  address: 127.0.0.1
  port: 8080 #If you configure port 443, you'll need to update the listener with tls_certificates
  message_format: huggingface

# Centralized way to manage LLMs, manage keys, retry logic, failover and limits in a central way
llm_providers:
  - name: OpenAI
    provider: openai
    access_key: $OPENAI_API_KEY
    model: gpt-3.5-turbo
    default: true

# default system prompt used by all prompt targets
system_prompt: |
  You are a network assistant that helps operators with a better understanding of network traffic flow and perform actions on networking operations. No advice on manufacturers or purchasing decisions.

prompt_targets:
    - name: device_summary
      description: Retrieve network statistics for specific devices within a time range
      endpoint:
        name: app_server
        path: /agent/device_summary
      parameters:
        - name: device_ids
          type: list
          description: A list of device identifiers (IDs) to retrieve statistics for.
          required: true  # device_ids are required to get device statistics
        - name: days
          type: int
          description: The number of days for which to gather device statistics.
          default: "7"

# Arch creates a round-robin load balancing between different endpoints, managed via the cluster subsystem.
endpoints:
  app_server:
    # value could be ip address or a hostname with port
    # this could also be a list of endpoints for load balancing
    # for example endpoint: [ ip1:port, ip2:port ]
    endpoint: host.docker.internal:18083
    # max time to wait for a connection to be established
    connect_timeout: 0.005s
```
### Step 3: Using OpenAI Client with Arch as an Egress Gateway

Make outbound calls via Arch

```python
from openai import OpenAI

# Use the OpenAI client as usual
client = OpenAI(
  # No need to set a specific openai.api_key since it's configured in Arch's gateway
  api_key = '--',
  # Set the OpenAI API base URL to the Arch gateway endpoint
  base_url = "http://127.0.0.1:12000/v1"
)

response = client.chat.completions.create(
    # we select model from arch_config file
    model="--",
    messages=[{"role": "user", "content": "What is the capital of France?"}],
)

print("OpenAI Response:", response.choices[0].message.content)

```

### [Observability](https://docs.archgw.com/guides/observability/observability.html)
Arch is designed to support best-in class observability by supporting open standards. Please read our [docs](https://docs.archgw.com/guides/observability/observability.html) on observability for more details on tracing, metrics, and logs. The screenshot below is from our integration with Signoz (among others)

![alt text](docs/source/_static/img/tracing.png)

### Contribution
We would love feedback on our [Roadmap](https://github.com/orgs/katanemo/projects/1) and we welcome contributions to **Arch**!
Whether you're fixing bugs, adding new features, improving documentation, or creating tutorials, your help is much appreciated.
Please visit our [Contribution Guide](CONTRIBUTING.md) for more details
