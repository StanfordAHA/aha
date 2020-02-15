FROM quay.io/pypa/manylinux2014_x86_64
LABEL description="garnet"

RUN yum install -y \
    # Halide-to-Hardware
    llvm-toolset-7.0 llvm-toolset-7.0-llvm-static llvm-toolset-7.0-llvm-devel \
    ImageMagick csh \
    zlib-devel libpng-devel libjpeg-devel ncurses-devel \
    # hwtypes
    gmp-devel mpfr-devel libmpc-devel \
    # cgra_pnr
    igraph-devel \
    # EDA Tools
    ksh tcsh tcl \
    ## Innovus
    libpng12 libjpeg libXft libXp libXmu libGLU libXScrnSaver \
    && \
    mkdir -p aha && cd aha && \
    /opt/python/cp37-cp37m/bin/python -m venv . && \
    source bin/activate && \
    pip install cmake==3.15.3 && \
    echo "source /aha/bin/activate" >> ~/.bashrc && \
    echo "source scl_source enable llvm-toolset-7.0" >> ~/.bashrc

# CoreIR - Halide-to-Hardware
COPY ./coreir-apps /aha/coreir-apps
WORKDIR /aha/coreir-apps/build
RUN source /aha/bin/activate && cmake .. && make

# Lake
COPY ./BufferMapping /aha/BufferMapping
WORKDIR /aha/BufferMapping/cfunc
RUN source /aha/bin/activate && export COREIR_DIR=/aha/coreir-apps && make lib

# Halide-to-Hardware
COPY ./halide-to-hardware /aha/halide-to-hardware
COPY ./patches/halide-to-hardware /aha/patches/halide-to-hardware
WORKDIR /aha/halide-to-hardware
RUN patch Makefile < /aha/patches/halide-to-hardware/Makefile.patch && source scl_source enable llvm-toolset-7.0 && source /aha/bin/activate && export COREIR_DIR=/aha/coreir-apps && make && make distrib

# CoreIR
COPY ./coreir /aha/coreir
WORKDIR /aha/coreir/build
RUN source /aha/bin/activate && cmake .. && make && make install
# TODO: switch with following after RPATH fixes land in master
# RUN cd /aha/coreir/build && cmake .. && make && make install && rm -rf *

# Install AHA Tools
COPY . /aha
WORKDIR /aha
RUN source /aha/bin/activate && pip install wheel && pip install -e .

ENV PATH="/root/miniconda/bin:${PATH}"
ENV OA_UNSUPPORTED_PLAT=linux_rhel60
ENV USER=docker
