Terminology
============

A few definitions before we dive into the main architecture documentation. 

**Ingress**: An upstream client (web application) connects to Arch, sends requests, and receives responses.

**Egress**: An downstream host receives connections and prompts from Arch, and returns context or responses for a prompt

**Listener**: A listener is a named network location (e.g., port, address, path etc.) that Arch listens on to process prompts. 
Arch exposes one listener for simplicity that upstream clients can connect to

**System Prompt**: An initial text or message that is  provided by the developer that Arch can use to call an downstream LLM in order to generate 
a response from the LLM model. The system prompt can be thought of as the input or query that the model uses to generate its response. 
The quality and specificity of the system prompt can have a significant impact on the relevance and accuracy of the model's response. 
Therefore, it is important to provide a clear and concise system prompt that accurately conveys the user's intended message or question. 

**Prompt Targets**: Bolt offers a primitive called “prompt targets” to help separate business logic from undifferentiated 
work in building generative AI apps. Prompt targets are endpoints that receive prompts that are processed by Bolt. 
For example, Bolt enriches incoming prompts with metadata like knowing when a request is a follow-up or clarifying prompt 
so that you can build faster, more accurate RAG apps. To support agentic apps, like scheduling travel plans or sharing comments 
on a document - via prompts, Bolt uses its function calling abilities to extract critical information from the incoming prompt 
(or a set of prompts) needed by a downstream backend API or function call before calling it directly.

**Instance**: An Arch Gateway instance is a single out of (application) process that is designed to handled upstream and downstream connections
