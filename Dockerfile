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

# Install AHA Tools
COPY . /aha
WORKDIR /aha
RUN \
  echo foo && \
  du -sh /aha/* | egrep '^[0-9.]*[GM] ' | sort -rn && \
  ls -lhd /aha/clockwork/soda_codes                && \
  /bin/rm -rf /aha/clockwork                       && \
  du -sh /aha/* | egrep '^[0-9.]*[GM] ' | sort -rn && \
  echo DONE
RUN python -m venv .

# Pono
COPY ./pono /aha/pono
COPY ./aha/bin/setup-smt-switch.sh /aha/pono/contrib/
WORKDIR /aha/pono
# FIXME why are we building flex and bison from scratch? Shouldn't this be an apt install??
RUN \
  : SETUP && \
      source /aha/bin/activate && \
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
      echo '# btortools is small (1.5M)' && \
     ./contrib/setup-btor2tools.sh && \
  : PIP INSTALL && \
      cd /aha/pono && ./configure.sh --python && \
      cd /aha/pono/build && make -j4 && pip install -e ./python && \
      cd /aha && \
        pip install -e ./pono/deps/smt-switch/build/python && \
        pip install -e pono/build/python/

# CoreIR
WORKDIR /aha
COPY ./coreir /aha/coreir
WORKDIR /aha/coreir/build
RUN cmake .. && make && make install && \
  echo "coreir cleanup: 200M build/{src,bin,tests}"      && \
  echo -n "BEFORE CLEANUP: " && du -hs /aha/coreir/build && \
  /bin/rm -rf src bin tests                              && \
  echo -n "AFTER  CLEANUP: " && du -hs /aha/coreir/build

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
    rm -rf ntl* && \
    echo -n "BEFORE CLEANUP: " && du -hs /aha/clockwork && \
    echo "# cleanup: 440M removed with barvinok 'make clean'" && \
    (cd /aha/clockwork/barvinok-0.41; make clean) && \
    echo "# cleanup: removing 140M soda_codes?" && \
    /bin/rm -rf /aha/clockwork/soda_codes/ && \
    echo -n "AFTER  CLEANUP: " && du -hs /aha/clockwork && \
    echo DONE

# AFTER  CLEANUP: 970M	/aha/clockwork


# Halide-to-Hardware
COPY ./Halide-to-Hardware /aha/Halide-to-Hardware
WORKDIR /aha/Halide-to-Hardware
RUN export COREIR_DIR=/aha/coreir && make -j2 && make distrib && \
    rm -rf lib/*

# Sam
WORKDIR /aha/sam
RUN make sam
RUN source /aha/bin/activate && pip install scipy numpy pytest && pip install -e .

# Install torch (need big tmp folder)
WORKDIR /aha
RUN mkdir -p /aha/tmp/torch_install/
# Save (and later restore) existing value for TMPDIR, if any
ENV TMPTMPDIR=$TMPDIR
ENV TMPDIR=/aha/tmp/torch_install/
RUN source /aha/bin/activate && \
  pip install --cache-dir=$TMPDIR --build=$TMPDIR torch==1.7.1+cpu -f https://download.pytorch.org/whl/torch_stable.html && \
  echo -n "BEFORE CLEANUP: " && du -hs /aha && \
  /bin/rm -rf $TMPDIR && \
  echo -n "AFTER  CLEANUP: " && du -hs /aha
# Restore original value of TMPDIR
ENV TMPDIR=$TMPTMPDIR

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

RUN echo "source /aha/bin/activate" >> /root/.bashrc && \
    echo "mkdir -p /root/.modules" >> /root/.bashrc && \
    echo "source /cad/modules/tcl/init/sh" >> /root/.bashrc

# Cleanup / image-size-reduction notes:
# 
# - cannot delete `clockwork/barvinok` directory entirely because
#   regression tests use e.g. `barvinok-0.41/isl/isl_ast_build_expr.h`
# 
# - if you don't delete files in the same layer (RUN command) where
#   they were created, you don't get any space savings in the image.
#
# - cannot do "make delete" in `/aha/pono/deps/smt-switch/build`,
#   because it deletes `smt-switch/build/python`, which is where
#   smt-switch is pip-installed :(
#   This should probably be an issue or a FIXME in pono or something.
