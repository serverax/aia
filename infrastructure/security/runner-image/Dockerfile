# Custom GitHub Actions runner image for Sprint 6.
# Bakes in: Rust 1.81 + wasm32-wasip1 target + cosign + vault CLI.
# Built once, pushed to GHCR, referenced by the gha-runner-scale-set Helm
# release. Job cold-start is ~0 because all toolchains are present.

FROM ghcr.io/actions/actions-runner:2.319.1

USER root

ENV DEBIAN_FRONTEND=noninteractive

# Base build deps + curl/unzip for tool installs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        git \
        jq \
        pkg-config \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# ---- Rust (system-wide install) ----
ARG RUST_VERSION=1.81.0
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSfL https://sh.rustup.rs \
        | sh -s -- -y --default-toolchain "${RUST_VERSION}" --no-modify-path \
    && rustup target add wasm32-wasip1 \
    && chmod -R a+rwx /usr/local/cargo /usr/local/rustup

# ---- Cosign ----
ARG COSIGN_VERSION=2.4.0
RUN curl -sSfL "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64" \
        -o /usr/local/bin/cosign \
    && chmod +x /usr/local/bin/cosign \
    && cosign version

# ---- Vault CLI ----
ARG VAULT_VERSION=1.18.0
RUN curl -sSfL "https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip" \
        -o /tmp/vault.zip \
    && unzip /tmp/vault.zip -d /usr/local/bin \
    && rm /tmp/vault.zip \
    && vault --version

USER runner

# Sanity-check toolchain layout (build will fail at `docker build` if anything
# misbehaves, rather than at first job dispatch).
RUN rustc --version \
    && cargo --version \
    && rustup target list --installed | grep wasm32-wasip1 \
    && cosign version \
    && vault --version
