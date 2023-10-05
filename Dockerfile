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

# Bring in aha repo, prepare python environment
WORKDIR /
RUN mkdir /aha && cd /aha && python -m venv .

# Pono
COPY ./pono /aha/pono
COPY ./aha/bin/setup-smt-switch.sh /aha/pono/contrib/
WORKDIR /aha/pono
RUN \
  : SETUP && \
      pip install Cython==0.29 pytest toml scikit-build==0.13.0 && \
  : FLEX && \
      apt-get update && apt-get install -y flex && \
  : BISON && \
      echo "# Cannot use standard dist bison 3.5, must have 3.7 or better :(" && \
      ./contrib/setup-bison.sh                                     && \
      echo "# bison cleanup /aha/pono 77M => 48M"                  && \
      (cd /aha/pono/deps/bison; make clean; /bin/rm -rf src tests) && \
  : SMT-SWITCH && \
      ./contrib/setup-smt-switch.sh --python && \
      :                                                 && \
      echo "# cleanup: 1.3GB smt-switch build tests"    && \
      /bin/rm -rf /aha/pono/deps/smt-switch/build/tests && \
      :                                                           && \
      echo "# cleanup: 700M smt-switch deps (cvc5,bitwuzla,btor)" && \
      /bin/rm -rf /aha/pono/deps/smt-switch/deps                  && \
      :                                                                 && \
      echo "# cleanup: 200M intermediate builds of cvc5,bitwuzla,btor"  && \
      /bin/rm -rf //aha/pono/deps/smt-switch/build/{cvc5,bitwuzla,btor} && \
  : BTOR2TOOLS && \
     ./contrib/setup-btor2tools.sh && \
  : PIP INSTALL && \
      cd /aha/pono && ./configure.sh --python && \
      cd /aha/pono/build && make -j4 && pip install -e ./python && \
      cd /aha && \
        source /aha/bin/activate && \
        pip install -e ./pono/deps/smt-switch/build/python && \
        pip install -e pono/build/python/

# CoreIR
WORKDIR /aha
COPY ./coreir /aha/coreir
WORKDIR /aha/coreir/build
RUN cmake .. && make && make install && /bin/rm -rf src bin tests

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
    echo "Cleanup: ntl, 440M barvinok, 390M dot-o files" && \
      rm -rf ntl* && \
      (cd /aha/clockwork/barvinok-0.41; make clean) && \
      rm -rf /aha/clockwork/*.o /aha/clockwork/bin/*.o && \
    echo DONE

# Halide-to-Hardware
COPY ./Halide-to-Hardware /aha/Halide-to-Hardware
WORKDIR /aha/Halide-to-Hardware
RUN export COREIR_DIR=/aha/coreir && make -j2 && make distrib && \
    echo "Cleanup: 200M lib, 400M gch, 200M distrib, 100M llvm" && \
      rm -rf lib/* && \
      rm -rf /aha/Halide-to-Hardware/include/Halide.h.gch/  && \
      rm -rf /aha/Halide-to-Hardware/distrib/{bin,lib}      && \
      rm -rf /aha/Halide-to-Hardware/bin/build/llvm_objects && \
    echo DONE    

# Sam
WORKDIR /aha/sam
RUN make sam
RUN source /aha/bin/activate && pip install scipy numpy pytest && pip install -e .

# Install torch (need big tmp folder)
WORKDIR /aha
RUN source /aha/bin/activate && \
  export TMPDIR=/aha/tmp/torch_install && mkdir -p $TMPDIR && \
  pip install --cache-dir=$TMPDIR --build=$TMPDIR torch==1.7.1+cpu -f https://download.pytorch.org/whl/torch_stable.html && \
  echo "# Remove 700M tmp files created during install" && \
  rm -rf $TMPDIR

# Final pip installs: AHA Tools etc.
WORKDIR /aha
RUN source bin/activate && \
  pip install urllib3==1.26.15 && \
  pip install wheel six && \
  pip install systemrdl-compiler peakrdl-html && \
  pip install -e . && \
  pip install packaging==21.3 && \
  aha deps install

WORKDIR /aha

ENV OA_UNSUPPORTED_PLAT=linux_rhel60
ENV USER=docker

# Create a /root/.modules so as to avoid this warning on startup:
#     "+(0):WARN:0: Directory '/root/.modules' not found"

RUN echo "source /aha/bin/activate"               >> /root/.bashrc && \
    echo "mkdir -p /root/.modules"                >> /root/.bashrc && \
    echo "source /cad/modules/tcl/init/sh"        >> /root/.bashrc && \
    echo 'echo ""                                      ' >> /root/.bashrc && \
    echo 'echo "For pre-compiled Halide 'gch' headers:"' >> /root/.bashrc && \
    echo 'echo "    cd /aha/Halide-to-Hardware"        ' >> /root/.bashrc && \
    echo 'echo "    rm include/Halide.h"               ' >> /root/.bashrc && \
    echo 'echo "    make include/Halide.h"             ' >> /root/.bashrc && \
    echo 'echo ""                                      ' >> /root/.bashrc && \
    echo DONE

# Restore halide distrib files on every container startup
ENTRYPOINT [ "/aha/aha/bin/restore-halide-distrib.sh" ]


# Cleanup / image-size-reduction notes:
# 
# - cannot delete `clockwork/barvinok` directory entirely because
#   regression tests use e.g. `barvinok-0.41/isl/isl_ast_build_expr.h`
# 
# - if you don't delete files in the same layer (RUN command) where
#   they were created, you don't get any space savings in the image.
#
# - cannot do "make clean" in `/aha/pono/deps/smt-switch/build`,
#   because it deletes `smt-switch/build/python`, which is where
#   smt-switch is pip-installed :(
#   This should probably be an issue or a FIXME in pono or something.
