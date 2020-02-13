FROM quay.io/pypa/manylinux2014_x86_64
LABEL description="garnet"

RUN yum install -y \
    # Halide-to-Hardware
    llvm7.0-7.0.1-4.el7.x86_64 llvm7.0-devel-7.0.1-4.el7.x86_64 \
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
    pip install cmake==3.15.3 autoenv

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

ENV PATH="/root/miniconda/bin:${PATH}"
ENV OA_UNSUPPORTED_PLAT=linux_rhel60
ENV USER=docker
