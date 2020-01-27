FROM ubuntu:rolling
RUN apt update && \
    # apt install -y --no-install-recommends \
    apt install -y \
        git make cmake gcc g++ \
        python3 python3-pip \
        # Halide-to-Hardware
        clang-7 llvm-7 \
        # hwtypes
        libgmp-dev libmpfr-dev libmpc-dev \
        # cgra_pnr
        libigraph-dev \
        && \
    apt clean && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 100 \
                        --slave   /usr/bin/pip    pip    /usr/bin/pip3 && \
    update-alternatives --install /usr/bin/clang       clang       /usr/bin/clang-7 100 && \
    update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-7 100

COPY . /aha

# CoreIR
RUN cd /aha/coreir/build && cmake .. && make && make install
# TODO: switch with following after RPATH fixes land in master
# RUN cd /aha/coreir/build && cmake .. && make && make install && rm -rf *

# CoreIR - Halide-to-Hardware
RUN cd /aha/coreir-apps/build && cmake .. && make

# Lake
RUN export COREIR_DIR=/aha/coreir-apps && cd /aha/BufferMapping/cfunc && make lib

# Halide-to-Hardware
RUN export COREIR_DIR=/aha/coreir-apps && cd /aha/halide-to-hardware && make && make distrib

RUN cd /aha && pip install -e .
