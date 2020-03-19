.. aha documentation master file, created by
   sphinx-quickstart on Mon Mar 16 18:44:34 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Quick Start
###########

You will probably want to have docker installed first.

::

   git clone https://github.com/hofstee/aha.git
   cd aha
   pip install -e .


.. toctree::
   :maxdepth: 2
   :caption: Contents:

I want to...
############

get a working set of tools
==========================

Currently, the most robust way of getting a working set of tools is by
running inside of the `garnet docker image
<https://hub.docker.com/r/stanfordaha/garnet>`_. If you're on a
machine like ``kiwi``, then the ``aha docker`` command will
automatically mount the CAD tools in ``/cad``, and also the technology
libraries.

::

   docker pull stanfordaha/garnet
   aha docker

Afterwards, you can connect to the container using ``docker attach
<container name>`` and perform any of the remaining steps there.

If you additionally need the ADK and MemoryCompiler, then you will
want to first clone the ``tsmc-adk`` locally, and pass the paths to
both of those in ``--tsmc-adk`` and ``--mc``.


generate RTL for Garnet
=======================

The wrapper provides a shim to calling garnet from anywhere in the
system once it's installed. The arguments are the same as calling
``python garnet.py`` normally.

::

   # e.g. aha garnet --width 16 --height 4 --verilog
   aha garnet <args>


generate CoreIR from Halide
===========================

The different applications are listed in the `hardware_benchmarks
<https://github.com/StanfordAHA/Halide-to-Hardware/tree/master/apps/hardware_benchmarks>`_
directory of Halide-to-Hardware. To generate CoreIR for any of these
applications, there is an ``aha halide`` shim. You'll need to pass in
the relative path from the ``hardware_benchmarks`` directory to the
app folder.

::

   # e.g. aha halide apps/pointwise
   aha halide <app>


map CoreIR to a CGRA bitstream
==============================

You'll first need to generate CoreIR from Halide. Then you can pass in
the same relative path like when generating from Halide.

::

   # e.g. aha map apps/pointwise --width 16 --height 4
   aha map <app> <args>

.. attention:: The app name must be passed prior to the other
               arguments.


run RTL tests of a Halide application
=====================================

After mapping CoreIR to a bitstream, you can pass in the same relative
path to test the application. You will also need to have generated
garnet first.

::

   # e.g. aha test apps/pointwise
   aha test <app>

.. attention:: You'll probably want to ``module load incisive``
               first. At the time of writing, the Verilator backend
               doesn't seem to be functioning as intended.

set up physical design tools
============================

.. attention:: You'll need to be running on a machine with access to
   the TSMC tooling. To get the TSMC ADK, you might need to be on the
   restricted Arm machine. Otherwise, talk to Alex.

::

   module load <tools>
   aha pd init
