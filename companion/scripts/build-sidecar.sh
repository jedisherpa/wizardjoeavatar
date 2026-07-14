#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPANION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPOSITORY_ROOT="$(cd "$COMPANION_DIR/.." && pwd)"
TAURI_DIR="$COMPANION_DIR/src-tauri"
BUILD_ROOT="${WIZARD_SIDECAR_BUILD_DIR:-${TMPDIR:-/tmp}/wizard-joe-companion-sidecar-build}"
VENV_DIR="$BUILD_ROOT/packaging-venv"
DIST_DIR="$BUILD_ROOT/dist"
WORK_DIR="$BUILD_ROOT/work"
LOCK_FILE="$SCRIPT_DIR/sidecar-requirements.lock"
SPEC_FILE="$SCRIPT_DIR/wizard-joe-engine.spec"
EXPECTED_PYTHON_VERSION="3.12.10"
EXPECTED_UV_VERSION="0.11.7"

TARGET_TRIPLE="$(rustc --print host-tuple)"
RESOURCE_DEST="$TAURI_DIR/resources/sidecar/$TARGET_TRIPLE/wizard-joe-engine"

rm -rf "$BUILD_ROOT" "$RESOURCE_DEST"
mkdir -p "$BUILD_ROOT" "$DIST_DIR" "$WORK_DIR" "$(dirname "$RESOURCE_DEST")"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  command -v uv >/dev/null 2>&1 || {
    printf 'uv %s is required to provision CPython %s.\n' \
      "$EXPECTED_UV_VERSION" "$EXPECTED_PYTHON_VERSION" >&2
    exit 1
  }
  ACTUAL_UV_VERSION="$(uv --version | awk '{print $2}')"
  if [[ "$ACTUAL_UV_VERSION" != "$EXPECTED_UV_VERSION" ]]; then
    printf 'Expected uv %s, found %s.\n' "$EXPECTED_UV_VERSION" "$ACTUAL_UV_VERSION" >&2
    exit 1
  fi
  UV_PYTHON_INSTALL_DIR="$BUILD_ROOT/python" uv python install "$EXPECTED_PYTHON_VERSION"
  PYTHON_BIN="$(UV_PYTHON_INSTALL_DIR="$BUILD_ROOT/python" uv python find "$EXPECTED_PYTHON_VERSION")"
else
  ACTUAL_UV_VERSION="not-used"
fi

ACTUAL_PYTHON_VERSION="$($PYTHON_BIN -c 'import platform; print(platform.python_version())')"
if [[ "$ACTUAL_PYTHON_VERSION" != "$EXPECTED_PYTHON_VERSION" ]]; then
  printf 'Expected CPython %s, found %s at %s\n' \
    "$EXPECTED_PYTHON_VERSION" "$ACTUAL_PYTHON_VERSION" "$PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install \
  --disable-pip-version-check \
  --no-input \
  --requirement "$LOCK_FILE"

export MACOSX_DEPLOYMENT_TARGET=12.0
export PYTHONHASHSEED=0
export WIZARD_REPOSITORY_ROOT="$REPOSITORY_ROOT"
"$VENV_DIR/bin/pyinstaller" \
  --clean \
  --noconfirm \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  "$SPEC_FILE"

INCOMPATIBLE_MACHO=""
while IFS= read -r file; do
  MINIMUM_VERSION="$(otool -l "$file" 2>/dev/null | awk '
    /LC_BUILD_VERSION/ { build = 1; next }
    build && /minos/ { print $2; exit }
    /LC_VERSION_MIN_MACOSX/ { legacy = 1; next }
    legacy && /version/ { print $2; exit }
  ')"
  if [[ -n "$MINIMUM_VERSION" ]] && (( ${MINIMUM_VERSION%%.*} > 12 )); then
    INCOMPATIBLE_MACHO="$file requires macOS $MINIMUM_VERSION"
    break
  fi
done < <(find "$DIST_DIR/wizard-joe-engine" -type f -print)
if [[ -n "$INCOMPATIBLE_MACHO" ]]; then
  printf 'Sidecar is not compatible with macOS 12: %s\n' "$INCOMPATIBLE_MACHO" >&2
  exit 1
fi

cp -R "$DIST_DIR/wizard-joe-engine" "$RESOURCE_DEST"
chmod 755 "$RESOURCE_DEST/wizard-joe-engine"

LOCK_SHA256="$(shasum -a 256 "$LOCK_FILE" | awk '{print $1}')"
SIDECAR_SHA256="$(shasum -a 256 "$RESOURCE_DEST/wizard-joe-engine" | awk '{print $1}')"
PAYLOAD_SHA256="$({ find "$RESOURCE_DEST" -type f -exec shasum -a 256 {} \;; } | LC_ALL=C sort -k 2 | shasum -a 256 | awk '{print $1}')"
SOURCE_COMMIT="$(git -C "$REPOSITORY_ROOT" rev-parse HEAD 2>/dev/null || printf unknown)"
if git -C "$REPOSITORY_ROOT" diff --quiet --ignore-submodules HEAD -- 2>/dev/null; then
  SOURCE_DIRTY=false
else
  SOURCE_DIRTY=true
fi
PYINSTALLER_VERSION="$($VENV_DIR/bin/pyinstaller --version)"

cat > "$RESOURCE_DEST/build-provenance.json" <<EOF
{
  "schemaVersion": 1,
  "targetTriple": "$TARGET_TRIPLE",
  "macosDeploymentTarget": "12.0",
  "pythonVersion": "$ACTUAL_PYTHON_VERSION",
  "uvVersion": "$ACTUAL_UV_VERSION",
  "pyinstallerVersion": "$PYINSTALLER_VERSION",
  "requirementsLockSha256": "$LOCK_SHA256",
  "sourceCommit": "$SOURCE_COMMIT",
  "sourceDirty": $SOURCE_DIRTY,
  "sidecarExecutableSha256": "$SIDECAR_SHA256",
  "payloadSha256BeforeManifest": "$PAYLOAD_SHA256",
  "signingState": "unsigned"
}
EOF

printf 'Sidecar resource ready: %s\n' "$RESOURCE_DEST"
printf 'Executable SHA-256: %s\n' "$SIDECAR_SHA256"
