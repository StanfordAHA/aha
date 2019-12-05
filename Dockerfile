FROM ubuntu:rolling
RUN apt update && \
    apt install -y --no-install-recommends \
        git make cmake gcc g++ \
        python3 python3-pip \
        && \
    apt clean && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# CoreIR
COPY coreir /coreir
RUN cd /coreir/build && cmake .. && make && make install
# TODO: switch with following after RPATH fixes land in master
# RUN cd /coreir/build && cmake .. && make && make install && rm -rf *

# Halide-to-Hardware