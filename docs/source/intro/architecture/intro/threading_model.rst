.. _architecture_threading:

Threading model
===============

Arch uses a single process with multiple threads architecture.

A single *primary* thread controls various sporadic coordination tasks while some number of *worker*
threads perform filtering, and forwarding.

Once a connection is accepted, the connection spends the rest of its lifetime bound to a single worker 
thread. This allows the majority of Arch to be largely single threaded (embarrassingly parallel) with a 
small amount of more complex code handling coordination between the worker threads.

Generally Arch is written to be 100% non-blocking.

.. tip::

   For most workloads we recommend configuring the number of worker threads to be equal to the number of
   hardware threads on the machine.