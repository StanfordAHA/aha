FROM docker.io/ubuntu:20.04
LABEL description="garnet"
SHELL ["/bin/bash", "--login", "-c"]
WORKDIR /
RUN mkdir -p /aha/bin && echo echo actifoo > /aha/bin/activate
CMD ["/bin/echo", "foo"]
