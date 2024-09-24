Configuration Reference
============================

The following is a complete reference of the prompt-conifg.yml that controls the behavior of an Arch gateway. 
We've kept things simple (less than 100 lines) and held off on exposing additional functionality (for e.g. suppporting 
push observability stats, managing prompt-endpoints as virtual cluster, expose more load balancing options to endpoints, 
etc). Our focus has been to choose the best defaults for developers, so that they can spend more of their time in building 
features unique to their AI experience. 

.. literalinclude:: /_config/prompt-config-full-reference.yml
    :language: yaml
    :linenos:
    :caption: :download:`prompt-config-full-reference-beta-1-0.yml </_config/prompt-config-full-reference.yml>`