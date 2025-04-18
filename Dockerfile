# 10/17/2023
# If we put most-likely-to change submodules LAST in Dockerfile, we can
# maximize cache usage and minimize average build time.  A histogram of
# most-recent 256 submodule changes came up with this list.
#
#       ..<others w lower frequency occluded>..
#       6 kratos <kratos was responsible for 6 of the last 256 changes>
#       8 gemstone
#       8 Halide-to-Hardware
#       8 MetaMapper
#      16 canal
#      16 clockwork
#      16 sam
#      35 lake
#      36 archipelago
#      85 garnet
#      ..<garnet is the submodule that changed the most>..

FROM docker.io/ubuntu:20.04
LABEL description="garnet"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    cat /etc/resolv.conf && \
    apt-get install -y build-essential software-properties-common && \
    # add-apt-repository -y ppa:ubuntu-toolchain-r/test && \
    # add-apt-repository -y ppa:zeehio/libxp && \
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
        # sam
        graphviz \
        xxd \
        # pono
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
    pip install cmake==3.28.1 && \
    echo DONE

# Switch shell to bash
SHELL ["/bin/bash", "--login", "-c"]

