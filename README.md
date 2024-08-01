A open source project for developers to build and secure faster, more personalized generative AI apps. Katanemo is a high performance gateway designed with state of the art (SOTA) fast LLMs to process, route and evaluate prompts.

# Demos
## Complete
* [Weather Forecast](https://github.com/katanemo/intelligent-prompt-gateway/blob/main/demos/weather-forecast/README.md)
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
➜  intelligent-prompt-gateway git:(main) ✗ pre-commit install
pre-commit installed at .git/hooks/pre-commit
```
