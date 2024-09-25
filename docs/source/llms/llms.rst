.. _llms_in_arch:

LLMs and ML Models
==================

Arch utilizes purpose-built, industry leading, LLMs to handle the crufty and undifferentiated work around 
accepting, handling and processing prompts. The following sections talk about some of the core models that
are built-in Arch. 

Arch-Guard-v1
-------------
LLM-powered applications are susceptible to prompt attacks, which are prompts intentionally designed to 
subvert the developer’s intended behavior of the LLM. Arch-Guard-v1 is a classifier model trained on a large 
corpus of attacks, capable of detecting explicitly malicious prompts (and toxicity). 

The model is useful as a starting point for identifying and guardrailing against the most risky realistic 
inputs to LLM-powered applications. Our goal in embedding Arch-Guard in the Arch gateway is to enable developers 
to focus on their business logic and factor out security and safety outside application logic. Wth Arch-Guard-v1 
developers can take to significantly reduce prompt attack risk while maintaining control over the user experience.

Below is our test results of the strength of our model as compared to Prompt-Guard from `Meta LLama <https://huggingface.co/meta-llama/Prompt-Guard-86M>`_.

.. list-table::
   :header-rows: 1
   :widths: 15 15 10 15 15

   * - Dataset
     - Jailbreak (Yes/No)
     - Samples
     - Prompt-Guard Accuracy
     - Arch-Guard Accuracy
   * - casual_conversation
     - 0
     - 3725
     - 1.00
     - 1.00
   * - commonqa
     - 0
     - 9741
     - 1.00
     - 1.00
   * - financeqa
     - 0
     - 1585
     - 1.00
     - 1.00
   * - instruction
     - 0
     - 5000
     - 1.00
     - 1.00
   * - jailbreak_behavior_benign
     - 0
     - 100
     - 0.10
     - 0.20
   * - jailbreak_behavior_harmful
     - 1
     - 100
     - 0.30
     - 0.52
   * - jailbreak_judge
     - 1
     - 300
     - 0.33
     - 0.49
   * - jailbreak_prompts
     - 1
     - 79
     - 0.99
     - 1.00
   * - jailbreak_tweet
     - 1
     - 1282
     - 0.16
     - 0.35
   * - jailbreak_v
     - 1
     - 20000
     - 0.90
     - 0.93
   * - jailbreak_vigil
     - 1
     - 104
     - 1.00
     - 1.00
   * - mental_health
     - 0
     - 3512
     - 1.00
     - 1.00
   * - telecom
     - 0
     - 4000
     - 1.00
     - 1.00
   * - truthqa
     - 0
     - 817
     - 1.00
     - 0.98
   * - weather
     - 0
     - 3121
     - 1.00
     - 1.00

.. list-table::
   :header-rows: 1
   :widths: 15 20

   * - Statistics
     - Overall performance
   * - Overall Accuracy
     - 0.93568 (Prompt-Guard), 0.95267 (Arch-Guard)
   * - True positives rate (TPR)
     - 0.8468 (Prompt-Guard), 0.8887 (Arch-Guard)
   * - True negative rate (TNR)
     - 0.9972 (Prompt-Guard), 0.9970 (Arch-Guard)
   * - False positive rate (FPR)
     - 0.0028 (Prompt-Guard), 0.0030 (Arch-Guard)
   * - False negative rate (FNR)
     - 0.1532 (Prompt-Guard), 0.1113 (Arch-Guard)

.. list-table::
   :header-rows: 1
   :widths: 15 20

   * - Metrics
     - Values
   * - AUC
     - 0.857 (Prompt-Guard), 0.880 (Arch-Guard)
   * - Precision
     - 0.715 (Prompt-Guard), 0.761 (Arch-Guard)
   * - Recall
     - 0.999 (Prompt-Guard), 0.999 (Arch-Guard)



Arch-Agent
----------