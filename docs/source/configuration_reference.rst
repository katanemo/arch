Configuration Reference
============================

The following is a complete reference of the prompt-conifg.yml that controls the behavior of an Arch gateway. 
We've kept things simple (less than 100 lines) and avoided exposing additional functionality (for e.g. suppporting 
push observability stats, managing prompt-target endpoints as cluster, expose more load balancing options, etc). The 
focus of Arch is to choose the best defaults for developers, so that they can spend more of their time in the 
application logic of their generative AI applications.

.. literalinclude:: /_config/prompt-config-full-reference.yml
    :language: yaml
    :caption: :download:`prompt-config-full-reference-beta-1-0.yml </_config/prompt-config-full-reference.yml>`