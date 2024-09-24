What is Arch
============

Arch is an intelligent Layer 7 gateway designed for generative AI apps, agents, and Co-pilots that work
with prompts. Written in `Rust <https://www.rust-lang.org/>`_, and engineered with purpose-built
:ref:`LLMs <llms_in_arch>`, Arch handles all the critical but undifferentiated tasks related to handling and
processing prompts, including rejecting `jailbreak <https://github.com/verazuo/jailbreak_llms>`_ attempts,
intelligently calling “backend” APIs to fulfill a user's request represented in a prompt, routing/disaster
recovery between upstream LLMs, and managing the observability of prompts and LLM interactions in a centralized way.

The project was born out of the belief that:

  *prompts are nuanced and opaque user requests that need the same capabilities as network requests
  in modern (cloud-native) applications, including secure handling, intelligent routing, robust observability,
  and integration with backend (API) systems for personalization.*

In practice, achieving the above goal is incredibly difficult. Arch attempts to do so by providing the
following high level features:

**Out of process archtiecture, built on Envoy:** Arch is takes a dependency on `Envoy <http://envoyproxy.io/>`_
and is a self-contained process that is designed to run alongside your application servers. Arch uses
Envoy's HTTP connection management subsystem and HTTP L7 filtering capabilities to extend its' proxying
functionality. This gives Arch several advantages:

* Arch builds on Envoy's success. Envoy is used at masssive sacle by the leading technology companies of
  our time including `AirBnB <https://www.airbnb.com>`_, `Dropbox <https://www.dropbox.com>`_,
  `Google <https://www.google.com>`_, `Reddit <https://www.reddit.com>`_, `Stripe <https://www.stripe.com>`_,
  etc. Its battle tested and scales linearly with usage and enables developers to focus on what really matters:
  application and business logic.

* Arch works with any application language. A single Arch deployment can act as gateway for AI applications
  written in Python, Java, C++, Go, Php, etc.

* As anyone that has worked with a modern application architecture knows, deploying library upgrades
  can be incredibly painful. Arch can be deployed and upgraded quickly across your infrastructure
  transparently.

**Engineered with LLMs:** Arch is engineered with specialized LLMs that are desgined for fast, cost-effective
and acurrate handling of prompts. These (sub-billion parameter) :ref:`LLMs <llms_in_arch>` are designed to be
best-in-class for critcal but undifferentiated prompt-related tasks like 1) applying guardrails for jailbreak
attempts 2) extracting critical information from prompts (like follow-on, clarifying questions, etc.) so that
you can improve the speed and accuracy of retrieval, and be able to convert prompts into API sematics when necessary
to build text-to-action (or agentic) applications. The focus for Arch is to make prompt processing indistiguishable
from the processing of a traditional HTTP request before forwarding it to an application server. With our focus on
speed and cost, Arch uses purpose-built LLMs and will continue to invest in those to lower latency (and cost) while
maintaining exceptional baseline performance with frontier LLMs like `OpenAI <https:openai.com>`_, and
`Anthropic <https:www.anthropic.com>`_.

**Prompt Guardrails:** Arch helps you apply prompt guardrails in a centralized way for better governance
hygiene. With prompt guardrails you can prevent `jailbreak <https://github.com/verazuo/jailbreak_llms>`_
attempts or toxicity present in user's prompts without having to write a single line of code. To learn more about
how to configure guardrails available in Arch, read :ref:`more <llms_in_arch>`.

**Function Calling:** Arch helps you personalize GenAI apps by enabling calls to application-specific (API)
operations using prompts. This involves any predefined functions or APIs you want to expose to users to
perform tasks, gather information, or manipulate data. With function calling, you have flexibilityto support
agentic workflows tailored to specific use cases - from updating insurance claims to creating ad campaigns.
Arch analyzes prompts, extracts critical information from prompts, engages in lightweight conversation with the
user to gather any missing parameters and makes API calls so that you can focus on writing business logic.

**Best-In Class Monitoring & Traffic Management:** Arch offers several monitoring metrics that help you
understand three critical aspects of your application: latency, token usage, and error rates by LLM provider.
Latency measures the speed at which your application is responding to users, which includes metrics like time
to first token (TFT), time per output token (TOT) metrics, and the total latency as perceived by users. In
addition, Arch offers several capabilities for calls originating from your applications to upstream LLMs,
including a vendor-agnostic SDK to make LLM calls, smart retries on errors from upstream LLMs, and automatic
cutover to other LLMs configured for continuous availability and disaster recovery scenarios.

**Front/edge proxy support:** There is substantial benefit in using the same software at the edge (observability,
prompt management, load balancing algorithms, etc.) as it is . Arch has a feature set that makes it well suited
as an edge proxy for most modern web application use cases. This includes TLS termination, HTTP/1.1 HTTP/2 and
HTTP/3 support and prompt-based routing.
