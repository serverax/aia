#!/usr/bin/env bash
# Build every WASM tool in tools/, copy the artifact + signature into each
# tool's dist/ subdir, and (optionally) sign each one with cosign.
#
# Modes:
#   1. Production (default): COSIGN_KEY must point at a Vault-issued key,
#      e.g. COSIGN_KEY=vault://cosign/prod. Real cosign binary required.
#   2. Test mode: COSIGN_TEST_MODE=1 generates an ephemeral local ECDSA
#      keypair under tools/.cosign-test/ and signs with it. Useful for
#      local dev and CI that just needs valid signatures.
#   3. Unsigned: COSIGN_SKIP_SIGN=1 builds but does not sign. Registry
#      will warn-but-allow if signature file is absent (Sprint 6 Day 3
#      soft check); Day 5 admission policy makes this fatal in production.
#
# Outputs:
#   tools/<name>/dist/<name>.wasm       (the compiled artifact)
#   tools/<name>/dist/<name>.wasm.sig   (base64 ECDSA-P256-SHA256 sig)
#   tools/dist/registry-index.json      (manifest of all built tools)
#
# Exit 0 on full success; non-zero on any build or sign failure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/tools"
TARGET_DIR="${TOOLS_DIR}/target/wasm32-wasip1/release"
REGISTRY_INDEX="${TOOLS_DIR}/dist/registry-index.json"

cd "${TOOLS_DIR}"

# ---------------- preflight ----------------

if ! command -v cargo >/dev/null 2>&1; then
    echo "ERROR: cargo not found. Install Rust 1.81+ (https://rustup.rs)." >&2
    exit 1
fi

if ! rustup target list --installed 2>/dev/null | grep -q '^wasm32-wasip1$'; then
    echo "wasm32-wasip1 target missing. Installing..."
    rustup target add wasm32-wasip1
fi

# Discover tool directories: anything under tools/ that has a tool.yaml,
# excluding the workspace root and the sdk crate.
mapfile -t TOOL_DIRS < <(find "${TOOLS_DIR}" -mindepth 2 -maxdepth 2 -name tool.yaml -printf '%h\n' | sort)

if [[ "${#TOOL_DIRS[@]}" -eq 0 ]]; then
    echo "ERROR: no tools found in ${TOOLS_DIR} (looked for */tool.yaml)" >&2
    exit 1
fi

echo "Found ${#TOOL_DIRS[@]} tool(s):"
printf '  %s\n' "${TOOL_DIRS[@]}"

# ---------------- signing setup ----------------

SIGN_MODE="prod"
if [[ "${COSIGN_SKIP_SIGN:-0}" == "1" ]]; then
    SIGN_MODE="skip"
elif [[ "${COSIGN_TEST_MODE:-0}" == "1" ]]; then
    SIGN_MODE="test"
fi

case "${SIGN_MODE}" in
    prod)
        if ! command -v cosign >/dev/null 2>&1; then
            echo "ERROR: cosign not found and COSIGN_TEST_MODE!=1. Install cosign or set COSIGN_TEST_MODE=1 for local dev." >&2
            exit 1
        fi
        if [[ -z "${COSIGN_KEY:-}" ]]; then
            echo "ERROR: COSIGN_KEY not set. Expected e.g. COSIGN_KEY=vault://cosign/prod" >&2
            exit 1
        fi
        echo "Signing with cosign key: ${COSIGN_KEY}"
        ;;
    test)
        TEST_KEY_DIR="${TOOLS_DIR}/.cosign-test"
        TEST_PRIV="${TEST_KEY_DIR}/cosign.key"
        TEST_PUB="${TEST_KEY_DIR}/cosign.pub"
        if [[ ! -f "${TEST_PRIV}" ]]; then
            echo "Generating test cosign keypair at ${TEST_KEY_DIR}..."
            mkdir -p "${TEST_KEY_DIR}"
            python3 -c "
from services.tool_sandbox.verifier import generate_test_keypair
priv, pub = generate_test_keypair()
import pathlib
pathlib.Path('${TEST_PRIV}').write_bytes(priv)
pathlib.Path('${TEST_PUB}').write_bytes(pub)
pathlib.Path('${TEST_PRIV}').chmod(0o600)
" || { echo "ERROR: failed to generate test keypair (needs Python + cryptography)" >&2; exit 1; }
        fi
        echo "Signing with TEST keypair: ${TEST_PRIV}"
        ;;
    skip)
        echo "WARNING: signature step skipped (COSIGN_SKIP_SIGN=1). Production registry will reject these artifacts."
        ;;
esac

# ---------------- build ----------------

echo
echo "Building workspace (release, wasm32-wasip1)..."
cargo build --release --target wasm32-wasip1 --workspace

# ---------------- per-tool: copy + sign ----------------

mkdir -p "${TOOLS_DIR}/dist"
INDEX_ENTRIES=()

for tool_dir in "${TOOL_DIRS[@]}"; do
    tool_name="$(basename "${tool_dir}")"
    # Skip the sdk library crate (it's an rlib, not a bin).
    if [[ "${tool_name}" == "sdk" ]]; then
        continue
    fi

    src_wasm="${TARGET_DIR}/${tool_name}.wasm"
    if [[ ! -f "${src_wasm}" ]]; then
        echo "ERROR: expected ${src_wasm} but cargo didn't produce it" >&2
        exit 1
    fi

    dist_dir="${tool_dir}/dist"
    mkdir -p "${dist_dir}"
    dst_wasm="${dist_dir}/${tool_name}.wasm"
    cp -f "${src_wasm}" "${dst_wasm}"
    size=$(wc -c < "${dst_wasm}")
    echo "  built  ${tool_name}.wasm  (${size} bytes)"

    case "${SIGN_MODE}" in
        prod)
            cosign sign-blob \
                --key "${COSIGN_KEY}" \
                --output-signature "${dst_wasm}.sig" \
                --yes \
                "${dst_wasm}" >/dev/null
            echo "  signed ${tool_name}.wasm.sig (cosign)"
            ;;
        test)
            python3 -c "
import base64, pathlib
from services.tool_sandbox.verifier import sign_blob_for_testing
blob = pathlib.Path('${dst_wasm}').read_bytes()
priv = pathlib.Path('${TEST_PRIV}').read_bytes()
sig = sign_blob_for_testing(blob, priv)
pathlib.Path('${dst_wasm}.sig').write_text(sig)
" || { echo "ERROR: test signing failed" >&2; exit 1; }
            echo "  signed ${tool_name}.wasm.sig (test key)"
            ;;
        skip)
            ;;
    esac

    sha256="$(python3 -c "
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path('${dst_wasm}').read_bytes()).hexdigest())
")"
    INDEX_ENTRIES+=("    {\"name\":\"${tool_name}\",\"path\":\"${tool_dir#${REPO_ROOT}/}/dist/${tool_name}.wasm\",\"sha256\":\"${sha256}\",\"size\":${size}}")
done

# ---------------- registry index ----------------

{
    echo "{"
    echo "  \"generated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"sign_mode\": \"${SIGN_MODE}\","
    echo "  \"tools\": ["
    IFS=$'\n'
    echo "${INDEX_ENTRIES[*]}" | sed '$!s/$/,/'
    unset IFS
    echo "  ]"
    echo "}"
} > "${REGISTRY_INDEX}"

echo
echo "Index written to ${REGISTRY_INDEX}"
echo "Done."
