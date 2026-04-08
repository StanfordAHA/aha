FROM docker.io/ubuntu:20.04
LABEL description="garnet"

# Prevents e.g. "Please select geographic area" during "apt-git install build-essential"
ENV DEBIAN_FRONTEND=noninteractive

# Switch shell to bash
SHELL ["/bin/bash", "--login", "-c"]

WORKDIR /
RUN mkdir -p /aha && cd /aha && echo echo actifoo > bin/activate
