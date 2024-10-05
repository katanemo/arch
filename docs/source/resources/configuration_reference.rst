Configuration Reference
============================

The following is a complete reference of the ``prompt-conifg.yml`` that controls the behavior of a single instance of
the Arch gateway. We've kept things simple (less than 80 lines) and held off on exposing additional functionality (for
e.g. suppporting push observability stats, managing prompt-endpoints as virtual cluster, exposing more load balancing
options, etc). Our belief that the simple things, should be simple. So we offert good defaults for developers, so
that they can spend more of their time in building features unique to their AI experience.

.. literalinclude:: includes/arch_config_full_reference.yaml
    :language: yaml
    :linenos:
    :caption: :download:`Arch Configuration - Full Reference <includes/arch_config_full_reference.yaml>`
