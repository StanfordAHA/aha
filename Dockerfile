FROM ubuntu:rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git make cmake gcc g++ \
        python3 python3-pip python3-setuptools \
        # Halide-to-Hardware
        imagemagick csh \
        clang-7 llvm-7 llvm-7-dev libz-dev libpng-dev libjpeg-dev \
        # hwtypes
        libgmp-dev libmpfr-dev libmpc-dev \
        # cgra_pnr
        libigraph-dev \
        # kratos
        libpython3-dev  \
        # EDA Tools
        tclsh tcl \
        && \
    ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 100 \
                        --slave   /usr/bin/pip    pip    /usr/bin/pip3 && \
    update-alternatives --install /usr/bin/clang       clang       /usr/bin/clang-7 100 && \
    update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-7 100

# CoreIR - Halide-to-Hardware
COPY ./coreir-apps /aha/coreir-apps
WORKDIR /aha/coreir-apps/build
RUN cmake .. && make

# Lake
COPY ./BufferMapping /aha/BufferMapping
WORKDIR /aha/BufferMapping/cfunc
RUN export COREIR_DIR=/aha/coreir-apps && make lib

# Halide-to-Hardware
COPY ./halide-to-hardware /aha/halide-to-hardware
WORKDIR /aha/halide-to-hardware
RUN export COREIR_DIR=/aha/coreir-apps && make && make distrib

# CoreIR
COPY ./coreir /aha/coreir
WORKDIR /aha/coreir/build
RUN cmake .. && make && make install
# TODO: switch with following after RPATH fixes land in master
# RUN cd /aha/coreir/build && cmake .. && make && make install && rm -rf *

# Install AHA Tools
COPY . /aha
WORKDIR /aha
RUN pip install -e .
