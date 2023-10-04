#!/bin/bash

# What does this script do?

# To save space (400M!), Dockerfile deletes halide bin and lib
# "distrib" files before building the final docker image.  When
# someone uses the image to launch a container, this script restores
# them from a compressed tar file that conveniently already exists(!)

# 2. Dockerfile also deletes 400M worth of "Halide.h.gch" header files, which
# I'm not sure if anyone needs or uses. This script, on first container launch,
# tells how to quickly restore them (takes about a minute).

# This script is designed to be run as the docker image's "ENTRYPOINT",
# i.e. it should run exactly *once* whenever a container is launched.

echo "--- Restore /aha/Halide-to-Hardware/distrib/{bin,lib}"
(
    cd /aha/Halide-to-Hardware/distrib
    tar xvf halide.tgz halide/bin; mv halide/bin bin
    tar xvf halide.tgz halide/lib; mv halide/lib lib
    rm $f
)
echo "halide/distrib restored:"
ls -lh /aha/Halide-to-Hardware/distrib/{bin,lib}/*
echo ""

# When this script runs as a Dockerfile ENTRYPOINT, this next line
# runs whatever commands get passed via e.g. "docker run"
exec "$@"
