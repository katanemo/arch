![Arch Gateway](/docs/source/_static/img/arch-logo-small.png "Arch Gateway Logo")

**Build fast, robust, and personalized generative AI agents/co-pilots/assitants**

Arch is an intelligent [Layer 7](https://www.cloudflare.com/learning/ddos/what-is-layer-7/) gateway designed for generative AI apps, AI agents, and co-pilots that work with prompts. Engineered with purpose-built LLMs, Arch handles the critical but undifferentiated tasks related to the handling and processing of prompts, including detecting and rejecting [jailbreak](https://github.com/verazuo/jailbreak_llms) attempts, intelligently calling "backend" APIs to fulfill the user's request represented in a prompt, routing to and offering disaster recovery between upstream LLMs, and managing the observability of prompts and LLM interactions in a centralized way.

**The project was born out of the belief that:**

*Prompts are nuanced and opaque user requests, which require the same capabilities as traditional HTTP requests including secure handling, intelligent routing, robust observability, and integration with backend (API) systems for personalization – all outside business logic.*


# Demos
## Complete
* [Weather Forecast](demos/function-calling/README.md)
  * Showing function calling cabaility
## In progress
* Network Co-pilot
## Not Started
* Show routing between different prompt targets (keyword search vs. top-k semantic search).
* Show routing between different prompt-resolver vs RAG-based resolver targets.
* Text Summarization Based on Lightweight vs. Thoughtful Dialogue using OpenAI
* Show conversational and system observability metrics. This includes topic/intent detection
* Show how we can help developers implement safeguards customized to their application requirements and responsible AI policies.

# Dev setup

## Pre-commit
Use instructions at [pre-commit.com](https://pre-commit.com/#install) to set it up for your machine. Once installed make sure github hooks are setup, so that when you upstream your change pre-commit hooks can run and validate your change. Follow command below to setup github hooks,

```sh
$ brew install pre-commit
$ pre-commit install
pre-commit installed at .git/hooks/pre-commit
```
