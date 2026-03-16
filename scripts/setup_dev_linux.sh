#!/usr/bin/env bash
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLENDER_MIN_VERSION="5.0"
BLENDER_INSTALL_DIR="/opt/blender"
BLENDER_SYMLINK="/usr/local/bin/blender"
BLENDER_ARCHIVE_URL="https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz"
BLENDER_ARCHIVE_NAME="blender-5.0.1-linux-x64.tar.xz"
BLENDER_EXTRACTED_DIR="blender-5.0.1-linux-x64"
TMP_DIR="$(mktemp -d)"
PIP_INSTALL_ARGS=(--user)

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

export PATH="/usr/local/bin:$PATH"

log() {
  echo "==> $1"
}

require_blender_version() {
  local output version_line version_number
  if ! output=$(blender --version 2>&1); then
    return 1
  fi

  version_line=$(printf "%s" "$output" | head -n 1)
  version_number=$(printf "%s" "$version_line" | awk '{print $2}')

  if [[ -z "$version_number" ]]; then
    echo "Unable to parse Blender version from: $version_line" >&2
    return 1
  fi

  log "Blender version info: $version_line"

  if ! python3 - <<PY
from distutils.version import LooseVersion
import sys
current = "${version_number}"
target = "${BLENDER_MIN_VERSION}"
if LooseVersion(current) < LooseVersion(target):
    print(f"Blender {current} is older than required {target}", file=sys.stderr)
    sys.exit(1)
PY
  then
    return 1
  fi

  return 0
}

install_blender_with_apt() {
  log "Installing Blender via apt"
  if ! sudo apt-get update -y; then
    log "apt-get update failed"
    return 1
  fi

  if ! sudo apt-get install -y blender; then
    log "apt-get install blender failed"
    return 1
  fi

  return 0
}

download_blender_archive() {
  local archive="$TMP_DIR/$BLENDER_ARCHIVE_NAME"
  if [[ -f "$archive" ]]; then
    log "Using cached Blender archive"
    return 0
  fi

  log "Downloading Blender archive from $BLENDER_ARCHIVE_URL"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$archive" "$BLENDER_ARCHIVE_URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$archive" "$BLENDER_ARCHIVE_URL"
  else
    echo "curl or wget is required to download Blender" >&2
    return 1
  fi

  return 0
}

install_blender_from_archive() {
  log "Installing Blender from archive"
  if ! download_blender_archive; then
    return 1
  fi

  local archive="$TMP_DIR/$BLENDER_ARCHIVE_NAME"
  local extracted_target="/opt/$BLENDER_EXTRACTED_DIR"

  sudo mkdir -p /opt
  sudo rm -rf "$BLENDER_INSTALL_DIR"
  sudo rm -rf "$extracted_target"
  sudo tar -xf "$archive" -C /opt

  if [[ ! -d "$extracted_target" ]]; then
    echo "Blender archive did not extract to $extracted_target" >&2
    return 1
  fi

  sudo mv "$extracted_target" "$BLENDER_INSTALL_DIR"
  sudo ln -sf "$BLENDER_INSTALL_DIR/blender" "$BLENDER_SYMLINK"
  export PATH="/usr/local/bin:$PATH"
}

determine_pip_install_args() {
  local in_venv
  in_venv=$(python3 - <<PY
import sys
is_venv = hasattr(sys, "real_prefix") or sys.prefix != getattr(sys, "base_prefix", sys.prefix)
print("1" if is_venv else "0")
PY
  )

  if [[ "$in_venv" == "1" ]]; then
    PIP_INSTALL_ARGS=()
    log "Detected Python virtual environment; installing packages inside the interpreter"
  else
    PIP_INSTALL_ARGS=(--user)
    log "Installing Python packages into user site-packages"
  fi
}

install_python_dependencies() {
  local requirements="$REPO_ROOT/requirements.txt"
  local sanitized="$TMP_DIR/requirements_without_bpy.txt"

  determine_pip_install_args

  if [[ -f "$requirements" ]]; then
    python3 - "$requirements" "$sanitized" <<'PY'
import sys
from pathlib import Path
req_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
with req_path.open() as source, out_path.open("w") as dest:
    for raw in source:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("bpy"):
            continue
        dest.write(stripped + "\n")
PY
    if [[ -s "$sanitized" ]]; then
      python3 -m pip install "${PIP_INSTALL_ARGS[@]}" -r "$sanitized"
    else
      log "No installable requirements in $requirements after skipping bpy"
    fi
  else
    log "Requirements file not found: $requirements"
  fi

  log "Skipping bpy installation because Blender provides the module"
  python3 -m pip install "${PIP_INSTALL_ARGS[@]}" pytest
}

cd "$REPO_ROOT"
log "Repository root: $REPO_ROOT"

if ! command -v blender >/dev/null 2>&1; then
  log "Blender not found on PATH"
  if ! install_blender_with_apt; then
    log "Falling back to manual Blender installation"
    install_blender_from_archive
  fi
fi

if ! require_blender_version; then
  log "System Blender does not satisfy version requirements"
  install_blender_from_archive
  if ! require_blender_version; then
    echo "Unable to verify Blender version after manual install" >&2
    exit 1
  fi
fi

log "Ensuring Blender's bundled Python has pip"
blender --background --python-expr "import ensurepip; ensurepip.bootstrap()"

log "Installing Python dependencies"
install_python_dependencies

log "Creating required directories"
mkdir -p "$REPO_ROOT/assets" "$REPO_ROOT/output"

log "Validating scene generation"
timeout 120 blender --background --python "$REPO_ROOT/scripts/generate_tree_scene.py"

echo "Dev environment ready"
