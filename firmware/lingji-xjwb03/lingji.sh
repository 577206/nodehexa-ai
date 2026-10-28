#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK="$ROOT/sdk"
TOOLS="$ROOT/.espressif"
APP="$SDK/apps"

usage() {
  cat <<'EOF'
Usage: ./lingji.sh setup
       ./lingji.sh build
       ./lingji.sh flash /dev/cu.usbmodem...
       ./lingji.sh flash-app /dev/cu.usbmodem...
       ./lingji.sh monitor /dev/cu.usbmodem...
       ./lingji.sh capture /dev/cu.usbmodem...
       ./lingji.sh preview /dev/cu.usbmodem...

The flash command requires an explicit Lingji port, verifies ESP32-S3/16 MB,
backs up the entire flash to the ignored backups/ directory, then flashes
all images in the current ESP-IDF build configuration.
Use flash-app only after a full flash when the partition table and model
partition have not changed.
EOF
}

check_project_identity() {
  if grep -Eq '^#define[[:space:]]+CONFIG_NODEHEXA_VOICE_SELFTEST[[:space:]]+1([[:space:]]|$)' \
    "$APP/main/qm_config/qm_config.h"; then
    echo 'Profile: local VB701N voice self-test (cloud disabled)'
  else
    if [[ ! -f "$ROOT/project_identity.local.h" ]]; then
      echo 'Cloud profile needs project_identity.local.h with your own PID/SECRET.' >&2
      exit 1
    fi
    if grep -Eq '^#define[[:space:]]+CONFIG_XJIANG_CLOUD_PID[[:space:]]+0([[:space:]]|$)|^#define[[:space:]]+CONFIG_XJIANG_CLOUD_SECERT[[:space:]]+""([[:space:]]|$)|REPLACE_WITH_YOUR_OWN_PRODUCT_SECRET' \
      "$ROOT/project_identity.local.h"; then
      echo 'Cloud identity still contains placeholder values; refusing to build.' >&2
      exit 1
    fi
    echo 'Profile: project cloud identity loaded from ignored local header'
  fi
}

activate_idf() {
  export IDF_TOOLS_PATH="$TOOLS"
  local env_dir
  env_dir="$(find "$TOOLS/python_env" -maxdepth 1 -type d -name 'idf5.4_py*_env' -print -quit 2>/dev/null)"
  if [[ -z "$env_dir" ]]; then
    echo 'ESP-IDF environment missing. Run ./lingji.sh setup first.' >&2
    exit 1
  fi
  export IDF_PYTHON_ENV_PATH="$env_dir"
  export PATH="$env_dir/bin:$PATH"
  # The official export script sets ADF_PATH and IDF_PATH and applies its IDF patches.
  source "$SDK/export.sh"
}

idf() {
  "$IDF_PYTHON_ENV_PATH/bin/python" "$IDF_PATH/tools/idf.py" -C "$APP" "$@"
}

check_port() {
  local port="$1"
  if [[ "$port" != /dev/cu.* ]]; then
    echo 'Pass an explicit macOS /dev/cu.* serial port.' >&2
    exit 1
  fi
  "$IDF_PYTHON_ENV_PATH/bin/python" - "$port" <<'PY'
import sys
from serial.tools import list_ports
port = sys.argv[1]
match = next((p for p in list_ports.comports() if p.device == port), None)
if match is None or (match.vid, match.pid) != (0x1A86, 0x55D3):
    raise SystemExit('Port does not match the observed Lingji USB bridge (1A86:55D3); aborting.')
print(f'Lingji USB bridge: {port} (1A86:55D3)')
PY
  local info
  info="$("$IDF_PYTHON_ENV_PATH/bin/python" -m esptool --chip esp32s3 --port "$port" --baud 115200 flash_id)"
  if [[ "$info" != *'Chip is ESP32-S3'* || "$info" != *'Detected flash size: 16MB'* ]]; then
    echo 'Chip or flash capacity does not match XJWB03; aborting.' >&2
    exit 1
  fi
  echo 'ESP32-S3 and 16 MB Flash verified.'
}

command="${1:-}"
case "$command" in
  setup)
    export IDF_TOOLS_PATH="$TOOLS"
    export IDF_PATH="$SDK/esp-idf"
    bash "$IDF_PATH/install.sh" esp32s3
    ;;
  build)
    check_project_identity
    activate_idf
    idf build
    test -f "$APP/build/flash_args"
    echo "Flash image list: $APP/build/flash_args"
    ;;
  flash)
    port="${2:-}"
    if [[ -z "$port" ]]; then usage; exit 2; fi
    check_project_identity
    activate_idf
    idf build
    test -f "$APP/build/flash_args"
    check_port "$port"
    mkdir -p "$ROOT/backups"
    chmod 700 "$ROOT/backups"
    backup="$ROOT/backups/xjwb03-$(date -u +%Y%m%dT%H%M%SZ).bin"
    umask 077
    echo "Backing up current 16 MB flash to $backup"
    "$IDF_PYTHON_ENV_PATH/bin/python" -m esptool --chip esp32s3 --port "$port" --baud 460800 read_flash 0x0 0x1000000 "$backup"
    "$IDF_PYTHON_ENV_PATH/bin/python" - "$backup" <<'PY'
import os, sys
if os.path.getsize(sys.argv[1]) != 0x1000000:
    raise SystemExit('Flash backup length is not 16 MB; aborting before write.')
PY
    echo 'Backup complete; flashing build image set.'
    idf -p "$port" flash
    ;;
  flash-app)
    port="${2:-}"
    if [[ -z "$port" ]]; then usage; exit 2; fi
    check_project_identity
    activate_idf
    idf build
    check_port "$port"
    "$IDF_PYTHON_ENV_PATH/bin/python" - "$ROOT/backups" <<'PY'
from pathlib import Path
import sys
backups = Path(sys.argv[1])
if not any(p.is_file() and p.stat().st_size == 0x1000000
           for p in backups.glob('xjwb03-*.bin')):
    raise SystemExit('No complete 16 MB pre-flash backup found; use flash instead.')
PY
    idf -p "$port" app-flash
    ;;
  monitor)
    port="${2:-}"
    if [[ -z "$port" ]]; then usage; exit 2; fi
    activate_idf
    check_port "$port"
    idf -p "$port" monitor
    ;;
  capture)
    port="${2:-}"
    if [[ -z "$port" ]]; then usage; exit 2; fi
    activate_idf
    "$IDF_PYTHON_ENV_PATH/bin/python" "$ROOT/capture_camera.py" "$port"
    ;;
  preview)
    port="${2:-}"
    if [[ -z "$port" ]]; then usage; exit 2; fi
    activate_idf
    "$IDF_PYTHON_ENV_PATH/bin/python" "$ROOT/camera_web.py" "$port"
    ;;
  *)
    usage
    exit 2
    ;;
esac
