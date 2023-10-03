#!/bin/bash
set -x
echo "--- Restore /aha/Halide-to-Hardware/distrib/{bin,lib}"
f=/tmp/restore_once
d=/aha/Halide-to-Hardware/distrib
if test -e $f; then
    cd $d;
    tar xvf halide.tgz halide/bin; mv halide/bin bin
    tar xvf halide.tgz halide/lib; mv halide/lib lib
    rm $f
else
    echo "Already restored, nothing to do"
fi
ls -lh /aha/Halide-to-Hardware/distrib/{bin,lib}/*
echo ""
