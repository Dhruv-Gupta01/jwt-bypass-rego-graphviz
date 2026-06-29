FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        curl \
        tmux \
    && rm -rf /var/lib/apt/lists/*

ARG OPA_VERSION=0.68.0
ARG OPA_SHA256=dfd5081fc6f930dfeaf2a225e31e616fc227dc0c7b43019b73d6f8fb8a1de1aa
RUN curl -fsSL "https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_amd64_static" \
    -o /usr/local/bin/opa \
    && echo "${OPA_SHA256}  /usr/local/bin/opa" | sha256sum -c - \
    && chmod +x /usr/local/bin/opa

RUN pip install --no-cache-dir \
    flask==3.1.0 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

COPY app/ /app/

WORKDIR /app
