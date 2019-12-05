FROM ubuntu:rolling
RUN apt update && \
    # apt install -y --no-install-recommends \
    apt install -y \
        git make cmake gcc g++ \
        python3 python3-pip \
        # Halide-to-Hardware
        clang-7 llvm-7 \
        && \
    apt clean && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 100 \
                        --slave   /usr/bin/pip    pip    /usr/bin/pip3 && \
    update-alternatives --install /usr/bin/clang       clang       /usr/bin/clang-7 100 && \
    update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-7 100

# CoreIR
COPY coreir /coreir
RUN cd /coreir/build && cmake .. && make && make install
# TODO: switch with following after RPATH fixes land in master
# RUN cd /coreir/build && cmake .. && make && make install && rm -rf *

# Lake
COPY BufferMapping /BufferMapping
RUN export COREIR_DIR=/usr/local && cd /BufferMapping/cfunc && make lib

# Halide-to-Hardware
COPY halide-to-hardware /halide-to-hardware
RUN cd /halide-to-hardware && make