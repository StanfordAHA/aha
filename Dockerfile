FROM docker.io/ubuntu:20.04
LABEL description="garnet"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        build-essential software-properties-common && \
    add-apt-repository -y ppa:ubuntu-toolchain-r/test && \
    add-apt-repository -y ppa:zeehio/libxp && \
    dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
        wget \
        git make gcc-9 g++-9 \
        python3 python3-dev python3-pip python3-venv \
        # Garnet
        default-jre \
        # Halide-to-Hardware
        imagemagick csh \
        libz-dev libpng-dev libjpeg-dev \
        libtinfo-dev libncurses-dev \
        # clockwork
        curl \
        # hwtypes
        libgmp-dev libmpfr-dev libmpc-dev \
        # cgra_pnr
        libigraph-dev \
        # clang
        xz-utils \
        # EDA Tools
        ksh tcsh tcl \
        dc libelf1 binutils \
        libxp6 libxi6 libxrandr2 libtiff5 libmng2 \ 
        libjpeg62 libxft2 libxmu6 libglu1-mesa libxss1 \
        libxcb-render0 libglib2.0-0 \
        libc6-i386 \
        && \
    ln -s /usr/lib/x86_64-linux-gnu/libtiff.so.5 /usr/lib/x86_64-linux-gnu/libtiff.so.3 && \
    ln -s /usr/lib/x86_64-linux-gnu/libmng.so.2 /usr/lib/x86_64-linux-gnu/libmng.so.1 && \
    ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 100 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 100 && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 100 \
                        --slave   /usr/bin/g++ g++ /usr/bin/g++-9 && \
    pip install cmake && \
    wget -nv -O ~/clang7.tar.xz http://releases.llvm.org/7.0.1/clang+llvm-7.0.1-x86_64-linux-gnu-ubuntu-18.04.tar.xz && \
    tar -xvf ~/clang7.tar.xz --strip-components=1 -C /usr/ && \
    rm -rf ~/clang7.tar.xz

# Switch shell to bash
SHELL ["/bin/bash", "--login", "-c"]

RUN apt update && apt install -y libncurses5 libxml2-dev

# CoreIR
COPY ./coreir /aha/coreir
WORKDIR /aha/coreir/build
RUN cmake .. && make && make install

# Lake
COPY ./BufferMapping /aha/BufferMapping
WORKDIR /aha/BufferMapping/cfunc
RUN export COREIR_DIR=/aha/coreir && make lib

# mflowgen
ENV GARNET_HOME=/aha/garnet
ENV MFLOWGEN=/aha/mflowgen

# clockwork
COPY clockwork /aha/clockwork
WORKDIR /aha/clockwork
ENV COREIR_PATH=/aha/coreir
ENV LAKE_PATH=/aha/lake
RUN ./misc/install_deps_ahaflow.sh && \
    source user_settings/aha_settings.sh && \
    make all -j4 && \
    rm -rf ntl*

# Halide-to-Hardware
COPY ./Halide-to-Hardware /aha/Halide-to-Hardware
WORKDIR /aha/Halide-to-Hardware
RUN export COREIR_DIR=/aha/coreir && make -j2 && make distrib && \
    rm -rf lib/*

# Install AHA Tools
COPY . /aha
WORKDIR /aha
RUN python -m venv . && source bin/activate && pip install wheel six && pip install systemrdl-compiler peakrdl-html && pip install -e . && aha deps install

WORKDIR /aha

ENV OA_UNSUPPORTED_PLAT=linux_rhel60
ENV USER=docker

RUN echo "source /aha/bin/activate" >> /root/.bashrc && \
    echo "source /cad/modules/tcl/init/sh" >> /root/.bashrc
