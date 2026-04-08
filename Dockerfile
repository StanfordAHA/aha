FROM docker.io/ubuntu:20.04
LABEL description="garnet"

# Switch shell to bash
SHELL ["/bin/bash", "--login", "-c"]

RUN mkdir -p /aha && cd /aha && python -m venv . && source bin/activate
