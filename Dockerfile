FROM ubuntu:rolling
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git make cmake gcc g++ \
        python3 python3-pip \
        # Halide-to-Hardware
        clang-7 llvm-7 \
        # hwtypes
        libgmp-dev libmpfr-dev libmpc-dev \
        # cgra_pnr
        libigraph-dev \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 100 \
                        --slave   /usr/bin/pip    pip    /usr/bin/pip3 && \
    update-alternatives --install /usr/bin/clang       clang       /usr/bin/clang-7 100 && \
    update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-7 100

COPY . /aha

# CoreIR
WORKDIR /aha/coreir/build
RUN cmake .. && make && make install
# TODO: switch with following after RPATH fixes land in master
# RUN cd /aha/coreir/build && cmake .. && make && make install && rm -rf *

# CoreIR - Halide-to-Hardware
WORKDIR /aha/coreir-apps/build
RUN cmake .. && make

# Lake
WORKDIR /aha/BufferMapping/cfunc
RUN export COREIR_DIR=/aha/coreir-apps && make lib

# Halide-to-Hardware
WORKDIR /aha/halide-to-hardware
RUN export COREIR_DIR=/aha/coreir-apps && make && make distrib

# Install AHA Tools
WORKDIR /aha
RUN pip install -e .
