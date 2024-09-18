Prompt Processing
=================

Arch's model serving process is designed to securely handle incoming prompts by detecting jailbreak attempts,
processing the prompts, and routing them to appropriate functions or prompt targets based on intent detection. 
The serving workflow integrates several key components, each playing a crucial role in managing generative AI interactions:

1. **Detecting and Rejection of Jailbreak Attempts (Arch-Guard)**:
   
   Arch employs Arch-Guard, a security layer that monitors incoming prompts to detect and reject jailbreak attempts, 
   ensuring that unauthorized or harmful behaviors are intercepted early in the process. Arch-Guard is the leading model
   in the industry for jailbreak and toxicity detection.

2. **Prompt Processing and Function Calls (Arch-FC1B)**:
   
   Once a prompt passes the security checks, Arch processes the content and identifies if any specific functions need to be called. 
   Arch-FC1B, a dedicated function calling module, extracts critical information from the prompt and executes the necessary 
   backend API calls or internal functions. This capability allows for efficient handling of agentic tasks, such as scheduling or 
   data retrieval, by dynamically interacting with backend services.

.. image:: /_static/img/function-calling-network-flow.jpg
   :width: 100%
   :align: center

3. **Intent Detection and Prompt Target Matching**:
   
   Arch uses Natural Language Inference (NLI) and embedding-based approaches to detect the intent of each incoming prompt. 
   This intent detection phase analyzes the prompt's content and matches it against predefined prompt targets, ensuring that each prompt 
   is forwarded to the most appropriate endpoint. Arch’s intent detection framework considers both the name and description of each prompt target, 
   enhancing accuracy in routing decisions.

   - **Embedding Approaches**: By embedding the prompt and comparing it to known target vectors, Arch effectively identifies the closest match, 
     ensuring that the prompt is handled by the correct downstream service.
   
   - **NLI Integration**: Natural Language Inference techniques further refine the matching process by evaluating the semantic alignment 
     between the prompt and potential targets.

4. **Forwarding Prompts to Downstream Targets**:
   
   After determining the correct target, Arch forwards the prompt to the designated endpoint, such as an LLM host or API service. 
   This seamless routing mechanism integrates with Arch's broader ecosystem, enabling efficient communication and response generation tailored to the user's intent.

Arch's model serving process combines robust security measures with advanced intent detection and function calling capabilities, creating a reliable and adaptable environment for managing generative AI workflows. This approach not only enhances the accuracy and relevance of responses but also safeguards against malicious usage patterns, aligning with best practices in AI governance.
