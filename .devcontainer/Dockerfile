ARG UV_VERSION=0.5.6
ARG DEBIAN_VERSION=bookworm

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv
FROM mcr.microsoft.com/vscode/devcontainers/base:$DEBIAN_VERSION

COPY --from=uv --chown=vscode: /uv /uvx /bin/
