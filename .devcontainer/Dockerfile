ARG UV_VERSION=0.5.6
ARG DEBIAN_VERSION=bookworm

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv
FROM mcr.microsoft.com/vscode/devcontainers/base:$DEBIAN_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential=12.9 \
  cmake=3.25.1-1 \
  git=1:2.39.5-0+deb12u1 \
  bison=2:3.8.2+dfsg-1+b1 \
  flex=2.6.4-8.2 \
  libboost-all-dev=1.74.0.3 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/staq
RUN git clone https://github.com/softwareQinc/staq.git . \
  && mkdir build

WORKDIR /tmp/staq/build
RUN cmake .. \
  && make -j8 \
  && make install \
  && rm -rf /tmp/staq

COPY --from=uv --chown=vscode: /uv /uvx /bin/
