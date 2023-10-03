#!/bin/bash

# What does this script do?

# To save space (400M!), Dockerfile deletes halide bin and lib "distrib" files.
# When the user first launches a container in the resulting image, this script
# restores them from a compressed tar file that conveniently already exists(!)

# 2. Dockerfile also deletes 400M worth of "Halide.h.gch" header files, which
# I'm not sure if anyone needs or uses. This script, on first container launch,
# tells how to quickly restore them (takes about a minute).

# (This script is designed to be run from the aha docker container's ".bashrc")

echo "--- Restore /aha/Halide-to-Hardware/distrib/{bin,lib}"
f=/tmp/restore_once
d=/aha/Halide-to-Hardware/distrib
if test -e $f; then
    cd $d;
    tar xvf halide.tgz halide/bin; mv halide/bin bin
    tar xvf halide.tgz halide/lib; mv halide/lib lib
    rm $f
    echo "halide/distrib restored."
    echo ""
    echo "If you want pre-compiled Halide 'gch' headers:"
    echo "    cd /aha/Halide-to-Hardware"
    echo "    rm include/Halide.h"
    echo "    make include/Halide.h"
else
    echo "Already restored, nothing to do."
fi
ls -lh /aha/Halide-to-Hardware/distrib/{bin,lib}/*
echo ""
