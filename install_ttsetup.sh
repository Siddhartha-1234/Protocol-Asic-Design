#!/usr/bin/env bash
# install_ttsetup.sh - installs the Tiny Tapeout IHP toolchain inside Ubuntu (WSL2 or native Linux).
# Mirrors Siddhartha's working setup of 22 Nov 2026 (see HOW_TO_RUN.md).
# Run as your normal user (NOT with sudo). It asks for your password once, for apt.
# Safe to run again: finished steps are skipped.
set -euo pipefail

# ---- Pinned versions: keep these identical on both laptops ----------------
PY_VERSION="3.12"
LIBRELANE_TAG="3.1.0.dev4"          # what tt-gds-action@ttihp27a uses for ihp-sg13cmos5l
COCOTB_VERSION="2.0.1"              # template test/requirements.txt
PYTEST_VERSION="8.4.2"              # template test/requirements.txt
IVERILOG_DEB_URL="https://github.com/TinyTapeout/iverilog/releases/download/v13.0/iverilog_13.0-1_amd64.deb"
OSS_CAD_TAG="2026-11-21"            # OSS CAD Suite release Siddhartha installed
OSS_CAD_FILE="oss-cad-suite-linux-x64-${OSS_CAD_TAG//-/}.tgz"
OSS_CAD_URL="https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${OSS_CAD_TAG}/${OSS_CAD_FILE}"
TT_TOOLS_REPO="https://github.com/TinyTapeout/tt-support-tools"
# ----------------------------------------------------------------------------

TT="$HOME/ttsetup"
DL="$TT/downloads"
say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[32mOK\033[0m  %s\n' "$*"; }
die()  { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*"; exit 1; }

[ "$(id -u)" -eq 0 ] && die "Run this as your normal user, not root/sudo."
[ "$(uname -m)" = "x86_64" ] || die "This script is for x86_64 (Intel/AMD). See the macOS/ARM notes in the guide."
case "$PWD" in /mnt/[a-z]/*) echo "Note: you are in a Windows folder ($PWD). The install goes to $TT on the Linux disk, which is what we want.";; esac
mkdir -p "$TT/bin" "$DL" "$HOME/asic"

say "1/7  System packages (apt, asks for your password)"
sudo apt-get update -y
sudo apt-get install -y git curl wget ca-certificates make build-essential \
     tar xz-utils jq libcairo2 librsvg2-bin pngquant x11-xserver-utils
ok "apt packages"

say "2/7  uv (Python manager)"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version

say "3/7  Python $PY_VERSION virtual environment at $TT/venv"
if [ ! -x "$TT/venv/bin/python" ]; then
  uv venv --seed --managed-python --python "$PY_VERSION" "$TT/venv"
fi
# shellcheck disable=SC1091
source "$TT/venv/bin/activate"
python --version

say "4/7  tt-support-tools, LibreLane $LIBRELANE_TAG, cocotb $COCOTB_VERSION"
if [ ! -d "$TT/tt-support-tools/.git" ]; then
  git clone "$TT_TOOLS_REPO" "$TT/tt-support-tools"
else
  git -C "$TT/tt-support-tools" pull --ff-only || true
fi
python -m pip install --upgrade pip
python -m pip install -r "$TT/tt-support-tools/requirements.txt"
python -m pip install "librelane==$LIBRELANE_TAG" "cocotb==$COCOTB_VERSION" "pytest==$PYTEST_VERSION"
ok "python packages"

say "5/7  Icarus Verilog 13.0 (Tiny Tapeout's build, unpacked into $TT/iverilog13)"
if [ ! -x "$TT/iverilog13/usr/bin/iverilog" ]; then
  wget -q --show-progress -O "$DL/iverilog13.deb" "$IVERILOG_DEB_URL"
  rm -rf "$TT/iverilog13" && dpkg-deb -x "$DL/iverilog13.deb" "$TT/iverilog13"
fi
IV="$TT/iverilog13/usr"
cat > "$TT/bin/iverilog" <<W
#!/bin/sh
exec "$IV/bin/iverilog" -B "$IV/lib/ivl" "\$@"
W
cat > "$TT/bin/vvp" <<W
#!/bin/sh
exec "$IV/bin/vvp" -M "$IV/lib/ivl" "\$@"
W
for t in iverilog-vpi; do
  [ -x "$IV/bin/$t" ] && ln -sf "$IV/bin/$t" "$TT/bin/$t"
done
chmod +x "$TT/bin/iverilog" "$TT/bin/vvp"
"$TT/bin/iverilog" -V 2>/dev/null | head -1

say "6/7  OSS CAD Suite $OSS_CAD_TAG (Verilator, Yosys, sby, solvers, GTKWave, Surfer) into ~/oss-cad-suite"
if [ ! -x "$HOME/oss-cad-suite/bin/yosys" ]; then
  wget -q --show-progress -O "$DL/$OSS_CAD_FILE" "$OSS_CAD_URL"
  tar -xzf "$DL/$OSS_CAD_FILE" -C "$HOME"
fi
"$HOME/oss-cad-suite/bin/yosys" -V

say "7/7  Environment script $TT/env.sh and the 'ttenv' command"
cat > "$TT/env.sh" <<'ENV'
# Tiny Tapeout IHP environment. Load it with:  ttenv
# Order matters: venv python first, then TT's Icarus 13, then OSS CAD Suite.
export PATH="$HOME/oss-cad-suite/bin:$PATH"
export PATH="$HOME/ttsetup/bin:$PATH"
source "$HOME/ttsetup/venv/bin/activate"
export PDK_ROOT="$HOME/ttsetup/pdk"
export PDK=ihp-sg13cmos5l
export LIBRELANE_TAG=3.1.0.dev4
mkdir -p "$PDK_ROOT"
ENV
grep -q "alias ttenv=" "$HOME/.bashrc" 2>/dev/null || \
  echo "alias ttenv='source ~/ttsetup/env.sh'" >> "$HOME/.bashrc"
grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || \
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
ok "env.sh written, alias added to ~/.bashrc"

say "Done. Next:"
cat <<MSG
  1. Close this terminal and open Ubuntu again (so 'ttenv' exists).
  2. Run:  ttenv
  3. Run:  bash verify_setup.sh            (quick checks, about 2-5 minutes)
  4. Run:  bash verify_setup.sh --harden   (full RTL-to-GDS run; first time 10-30 min, downloads ~8 GB)
MSG
