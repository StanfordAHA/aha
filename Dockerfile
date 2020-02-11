FROM ubuntu:14.04
LABEL description="garnet"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        build-essential software-properties-common && \
    add-apt-repository -y ppa:ubuntu-toolchain-r/test && \
    apt-get update && \
    apt-get install -y \
        wget \
        git make gcc-9 g++-9 \
        # Halide-to-Hardware
        imagemagick csh \
        libz-dev libpng-dev libjpeg-dev \
        # hwtypes
        libgmp-dev libmpfr-dev libmpc-dev \
        # cgra_pnr
        libigraph-dev \
        # kratos
        libpython3-dev \
        # clang
        xz-utils \
        # EDA Tools
        ksh tcsh tcl \
        libjpeg62 libxft2 libxp6 libxmu6 libglu1-mesa libxss1 \
        libxcb-render0 libglib2.0-0 \
        && \
    ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    bash ~/miniconda.sh -b -p $HOME/miniconda && \
    update-alternatives --install /usr/bin/python python /root/miniconda/bin/python 100 \
                        --slave   /usr/bin/pip    pip    /root/miniconda/bin/pip && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 100 \
                        --slave   /usr/bin/g++ g++ /usr/bin/g++-9 && \
    pip install cmake && \
    update-alternatives --install /usr/bin/cmake cmake /root/miniconda/bin/cmake 100 && \
    wget https://github.com/llvm/llvm-project/releases/download/llvmorg-7.1.0/clang+llvm-7.1.0-x86_64-linux-gnu-ubuntu-14.04.tar.xz -O ~/clang7.tar.xz && \
    tar -xvf ~/clang7.tar.xz --strip-components=1 -C /usr/


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
RUN pip install wheel && pip install -e .
