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
        libncurses5 libxml2-dev \
        graphviz \
        xxd \
        time \ 
        m4 \
        && \
    ln -s /usr/lib/x86_64-linux-gnu/libtiff.so.5 /usr/lib/x86_64-linux-gnu/libtiff.so.3 && \
    ln -s /usr/lib/x86_64-linux-gnu/libmng.so.2 /usr/lib/x86_64-linux-gnu/libmng.so.1 && \
    ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    echo "dash dash/sh boolean false" | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive dpkg-reconfigure dash && \
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

# Pono
COPY ./pono /aha/pono
COPY ./aha/bin/setup-smt-switch.sh /aha/pono/contrib/
WORKDIR /aha/pono
RUN pip install Cython==0.29 pytest toml scikit-build==0.13.0
RUN ./contrib/setup-bison.sh && ./contrib/setup-flex.sh && ./contrib/setup-smt-switch.sh --python && ./contrib/setup-btor2tools.sh
RUN ./configure.sh --python
WORKDIR /aha/pono/build
RUN make -j4 && pip install -e ./python
WORKDIR /aha

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
    source misc/copy_cgralib.sh && \
    rm -rf ntl*

# Halide-to-Hardware
COPY ./Halide-to-Hardware /aha/Halide-to-Hardware
WORKDIR /aha/Halide-to-Hardware
RUN export COREIR_DIR=/aha/coreir && make -j2 && make distrib && \
    rm -rf lib/*

# Install AHA Tools
COPY . /aha
WORKDIR /aha
RUN python -m venv .

# Sam
WORKDIR /aha/sam
RUN make sam
RUN source /aha/bin/activate && pip install scipy numpy pytest && pip install -e .

# Install torch (need big tmp folder)
WORKDIR /aha
RUN mkdir -p /aha/tmp/torch_install/
ENV TMPDIR=/aha/tmp/torch_install/
RUN source /aha/bin/activate && pip install --cache-dir=$TMPDIR --build=$TMPDIR torch==1.7.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

WORKDIR /aha
RUN source bin/activate && pip install urllib3==1.26.15 && pip install wheel six && pip install systemrdl-compiler peakrdl-html && pip install -e . && pip install packaging && pip install -e ./pono/deps/smt-switch/build/python && pip install -e pono/build/python/ && aha deps install

WORKDIR /aha

ENV OA_UNSUPPORTED_PLAT=linux_rhel60
ENV USER=docker

RUN echo "source /aha/bin/activate" >> /root/.bashrc && \
    echo "source /cad/modules/tcl/init/sh" >> /root/.bashrc
