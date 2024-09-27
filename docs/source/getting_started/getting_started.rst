.. _getting_started:

Getting Started
================

.. sidebar:: Pre-requisites
    
    In order for you to get started, please make sure that `Docker <https://www.docker.com/get-started>`_ 
    and `Python <https://www.python.org/downloads/>`_ are installed locally.

    As the examples use the pre-built `Arch Docker images <https://hub.docker.com/r/katanemo/arch>`_, 
    they should work on the following architectures:

        - x86_64
        - ARM 64


This section gets you started with a very simple configuration and provides some example configurations.


The fastest way to get started using Arch is installing `pre-built binaries <https://hub.docker.com/r/katanemo/arch>`_.
You can also build it from source.

Step 1: Install the Arch CLI
----------------------------
Arch's CLI allows you to manage and interact with the Arch gateway efficiently. To install the CLI, simply 
run the following command:

.. code-block:: bash 
    
    pip install archgw

This will install the archgw command-line tool globally on your system.

Step 2: Start Arch Gateway
--------------------------

.. code-block:: bash 
    
    archgw up --quick-start

Configuration
-------------

Today, only support a static bootstrap configuration file for simplicity today:

.. literalinclude:: /_config/getting-started.yml
    :language: yaml
