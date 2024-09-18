What is Arch
============

Arch is an intelligent Layer 7 gateway for generative AI apps, AI agents, and Co-pilots that use prompts. 
Written in `Rust <https://www.rust-lang.org/>`_, and engineered with purpose-built LLMs, Arch handles 
all the undifferentiated tasks related to accepting and processing prompts, including rejecting 
`jailbreak <https://github.com/verazuo/jailbreak_llms>`_ attempts, intelligently calling “backend” business 
APIs to fulfill a request in a prompt, routing and disaster recovery between upstream LLMs, and managing the 
observability of prompts and LLM interactions in a centralized way.

The project was born out of the belief that:

  *prompts are nuanced and opaque user requests that need the same capabilities as network requests 
  in cloud-native applications, including secure handling, intelligent routing, robust observability, 
  and integration with backend (API) systems for personalization.*

In practice, achieving the above goal is incredibly difficult. Arch attempts to do so by providing the 
following high level features:

**Out of process archtiecture, built on Envoy:** Arch is takes a dependency on `Envoy <http://envoyproxy.io/>`_ 
and is a self contained process that is designed to run alongside your application servers. Arch uses 
Envoy's HTTP connection management subsystem and HTTP L7 filtering capabilities to extend its' proxy 
functionality. This gives Arch several advantages:

* Arch builds on Envoy's success. Envoy is used at masssive sacle by the leading technology companies of 
  our time including `AirBnB <https://www.airbnb.com>`_, `Dropbox <https://www.dropbox.com>`_, 
  `Google <https://www.google.com>`_, `Reddit <https://www.reddit.com>`_, `Stripe <https://www.stripe.com>`_, 
  etc. Its battle tested and scales linearly with usage and enables developers to focus on what really matters: 
  application logic.

* Arch works with any application language. A single Arch deployment can act as gateway for applications 
  written in Python, Java, C++, Go, Php, etc. 

* As anyone that has worked with a modern application architecture knows, deploying library upgrades 
  can be incredibly painful. Arch can be deployed and upgraded quickly across your infrastructure 
  transparently.

**Industry-leading specalized LLMs:**  Arch offers industry-leading speed and accuracy for the handling and 
processing of undifferentiated tasks related to prompts. To do this, Arch is engineered with purpose-built 
sub-billion parameters :ref:`llms_in_arch` that are best-in-class for several natural language tasks like 
function calling, detecting and applying prompt guardrails. Arc helps you stay focused on the business logic 
of your GenAI application and manages the complex processing, handling, and governance of prompts in a central way, 
at any scale. 

**Function Calling:** Arch helps you personalize GenAI apps by enabling calls to application-specific operations 
various user prompts. This involves any predefined functions or APIs you want to expose to users to perform tasks, 
gather information, or manipulate data - via prompts. With function calling, you have flexibility to support agentic
workflows tailored to specific use cases - from updating insurance claims to creating ad campaigns. Arch analyzes prompts, 
extracts critical information from prompts, engages in lightweight conversation with the user to gather any missing 
parameters and makes API calls so that you can focus on writing business logic.

**Prompt Guardrails:** Arch helps you apply prompt guardrails in a centralized way for better governance 
hygiene. With prompt guardrails you can prevent `jailbreak <https://github.com/verazuo/jailbreak_llms>`_ 
attempts or toxic scenarios without having to write a single line of code. To learn more about how to configure 
guardrails available in Arch, read :ref:`more <llms_in_arch>`. 

**Best-In Class Monitoring & Traffic Management:** Arch offers several monitoring metrics that help you 
understand three critical aspects of your application: latency, token usage, and error rates by LLM provider. 
Latency measures the speed at which your application is responding to users, which includes metrics like time 
to first token (TFT), time per output token (TOT) metrics, and the total latency as perceived by users. In 
addition, Arch offers several capabilities for calls originating from your applications to LLMs, including a 
vendor-agnostic SDK to make LLM calls, smart retries on errors from upstream LLMs, and automatic cutover to other 
LLMs configured for continuous availability and disaster recovery scenarios.

**Front/edge proxy support:** There is substantial benefit in using the same software at the edge (observability, 
management, load balancing algorithms, etc.). Envoy has a feature set that makes it well suited as an edge proxy 
for most modern web application use cases. This includes TLS termination, HTTP/1.1 HTTP/2 and HTTP/3 support, 
as well as HTTP L7 routing.