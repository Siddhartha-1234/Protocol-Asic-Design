#!/usr/bin/env bash
# verify_setup.sh - checks the Tiny Tapeout IHP toolchain installed by install_ttsetup.sh.
#   bash verify_setup.sh             quick checks: versions + lint + sim + cocotb + formal + synth + docker
#   bash verify_setup.sh --harden    also runs the full RTL-to-GDS flow and the gate-level test
#   bash verify_setup.sh --versions  only prints the version report (to compare two laptops)
# A report is saved to ~/asic/verify_report.txt. Exit code 0 means no FAIL.
set -uo pipefail

MODE="${1:-quick}"
WORK="$HOME/asic"
SMOKE="$WORK/tt-smoke"
TMPD="$WORK/verify_tmp"
REPORT="$WORK/verify_report.txt"
TEMPLATE_URL="https://github.com/TinyTapeout/ttihp-verilog-template"
mkdir -p "$WORK"
: > "$REPORT"

PASS=0; FAIL=0; WARN=0
log()  { echo "$*" | tee -a "$REPORT"; }
pass() { PASS=$((PASS+1)); log "  [PASS] $*"; }
fail() { FAIL=$((FAIL+1)); log "  [FAIL] $*"; }
warn() { WARN=$((WARN+1)); log "  [WARN] $*"; }
head1(){ log ""; log "== $* =="; }
ver()  { "$@" 2>&1 | grep -v '^\s*$' | head -1; }

# --- load the environment if the user forgot 'ttenv' ---
if [ -z "${VIRTUAL_ENV:-}" ] || [ -z "${PDK:-}" ]; then
  if [ -f "$HOME/ttsetup/env.sh" ]; then source "$HOME/ttsetup/env.sh"; fi
fi

versions() {
  head1 "Version report ($(date '+%Y-%m-%d %H:%M'), host $(hostname))"
  log "  os         : $(. /etc/os-release; echo "$PRETTY_NAME") / kernel $(uname -r)"
  log "  python     : $(python --version 2>&1)  ($(command -v python))"
  for p in librelane cocotb pytest ciel klayout numpy; do
    log "  $(printf '%-11s' "$p"): $(python -m pip show "$p" 2>/dev/null | awk '/^Version: /{print $2; exit}')"
  done
  log "  iverilog   : $(ver iverilog -V)  ($(command -v iverilog))"
  log "  verilator  : $(ver verilator --version)"
  log "  yosys      : $(ver yosys -V)"
  log "  sby        : $(ver sby --version)"
  log "  yices      : $(ver yices-smt2 --version)"
  log "  z3         : $(ver z3 --version)"
  log "  bitwuzla   : $(ver bitwuzla --version)"
  log "  boolector  : $(ver boolector --version)"
  log "  eqy        : $(ver eqy --version)"
  log "  docker     : $(ver docker --version)"
  log "  git        : $(ver git --version)"
  log "  tt-tools   : $(git -C "$HOME/ttsetup/tt-support-tools" log -1 --format='%h %cs' 2>/dev/null)"
  log "  oss-cad    : $(cat "$HOME/oss-cad-suite/VERSION" 2>/dev/null || echo missing)"
  log "  PDK        : ${PDK:-unset}  PDK_ROOT=${PDK_ROOT:-unset}  LIBRELANE_TAG=${LIBRELANE_TAG:-unset}"
  log "  PDK enabled: $(ls "${PDK_ROOT:-/nonexistent}" 2>/dev/null | tr '\n' ' ')"
}

versions
[ "$MODE" = "--versions" ] && exit 0

# ---------------------------------------------------------------- 1. machine
head1 "1. Machine"
MEM_GB=$(awk '/MemTotal/{printf "%d", $2/1024/1024}' /proc/meminfo)
if [ "$MEM_GB" -ge 11 ]; then pass "RAM visible to Linux: ${MEM_GB} GB"
elif [ "$MEM_GB" -ge 7 ]; then warn "RAM visible to Linux is ${MEM_GB} GB. Small designs are fine; for 8x4 raise it with .wslconfig (guide step 3)."
else fail "RAM visible to Linux is only ${MEM_GB} GB"; fi
DISK_GB=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
if [ "$DISK_GB" -ge 40 ]; then pass "Free disk in home: ${DISK_GB} GB"; else warn "Only ${DISK_GB} GB free; the Docker image + PDK need ~15 GB, runs need more."; fi
case "$PWD" in /mnt/[a-z]/*) warn "You are running from a Windows drive ($PWD). Work in ~/asic instead; it is much faster.";; *) pass "Working on the Linux disk";; esac
[ "$(nproc)" -ge 4 ] && pass "CPU threads: $(nproc)" || warn "Only $(nproc) CPU threads; harden will be slow"

# ---------------------------------------------------------------- 2. environment
head1 "2. Environment (ttenv)"
[ "${VIRTUAL_ENV:-}" = "$HOME/ttsetup/venv" ] && pass "venv active: $VIRTUAL_ENV" || fail "venv not active. Run: ttenv"
python -c 'import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)' && pass "Python is 3.12" || fail "Python is $(python --version 2>&1), expected 3.12"
[ "${PDK:-}" = "ihp-sg13cmos5l" ] && pass "PDK=$PDK" || fail "PDK is '${PDK:-}', expected ihp-sg13cmos5l"
[ -n "${PDK_ROOT:-}" ] && pass "PDK_ROOT=$PDK_ROOT" || fail "PDK_ROOT not set"
chk_pkg() { v=$(python -m pip show "$1" 2>/dev/null | awk '/^Version: /{print $2; exit}'); [ "$v" = "$2" ] && pass "$1 $v" || fail "$1 is '${v:-missing}', expected $2"; }
chk_pkg librelane 3.1.0.dev4
chk_pkg cocotb 2.0.1
chk_pkg pytest 8.4.2
python -c 'import gdstk, klayout, yaml, cairosvg' 2>/dev/null && pass "tt-support-tools Python deps import" || fail "tt-support-tools deps missing (pip install -r ~/ttsetup/tt-support-tools/requirements.txt)"
iverilog -V 2>/dev/null | head -1 | grep -q 'version 13.0' && pass "Icarus 13.0 ($(command -v iverilog))" || fail "iverilog is not TT's 13.0: $(command -v iverilog)"
case "$(command -v iverilog)" in "$HOME/ttsetup/bin/"*) pass "TT Icarus is first on PATH";; *) fail "wrong iverilog first on PATH: $(command -v iverilog)";; esac
for t in verilator yosys sby yices-smt2 z3 bitwuzla boolector eqy gtkwave git make docker; do
  command -v "$t" >/dev/null && pass "$t found" || fail "$t not found"
done
if command -v surfer >/dev/null && surfer --version >/dev/null 2>&1; then pass "surfer runs"
else warn "surfer does not start here (on Ubuntu 24.04 its glibc is too old). Use gtkwave or https://surfer-project.org/"; fi

# ---------------------------------------------------------------- 3. small design tests
head1 "3. Small design: lint, simulation, synthesis, formal"
rm -rf "$TMPD"; mkdir -p "$TMPD"; cd "$TMPD"
cat > counter.v <<'V'
`default_nettype none
module counter (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    output reg  [3:0] q
);
    always @(posedge clk) begin
        if (rst)     q <= 4'd0;
        else if (en) q <= (q == 4'd9) ? 4'd0 : q + 4'd1;
    end
`ifdef FORMAL
    reg past_ok = 1'b0;
    always @(posedge clk) past_ok <= 1'b1;
    always @(*) assume (rst == !past_ok);
    always @(posedge clk) begin
        if (past_ok) assert (q <= 4'd9);
        cover (q == 4'd9);
    end
`endif
endmodule
V
cat > tb_counter.v <<'V'
`timescale 1ns/1ps
module tb_counter;
    reg clk = 0, rst = 1, en = 0;
    wire [3:0] q;
    counter dut (.clk(clk), .rst(rst), .en(en), .q(q));
    always #5 clk = ~clk;
    integer i;
    initial begin
        #12 rst = 0; en = 1;
        for (i = 0; i < 25; i = i + 1) @(posedge clk);
        #1;
        if (q == 4'd5) $display("SIM_PASS q=%0d", q); else $display("SIM_FAIL q=%0d", q);
        $finish;
    end
endmodule
V
cat > counter.sby <<'S'
[tasks]
prove
cover

[options]
prove: mode prove
cover: mode cover
depth 20

[engines]
smtbmc yices

[script]
read -formal counter.v
prep -top counter

[files]
counter.v
S
if verilator --lint-only -Wall counter.v > lint.log 2>&1; then pass "Verilator lint: clean"; else fail "Verilator lint (see $TMPD/lint.log)"; fi
if iverilog -g2012 -o sim.vvp counter.v tb_counter.v > iv.log 2>&1 && vvp sim.vvp 2>&1 | tee -a iv.log | grep -q SIM_PASS; then pass "Icarus simulation"; else fail "Icarus simulation (see $TMPD/iv.log)"; fi
if yosys -q -p "read_verilog counter.v; synth -top counter; tee -o synth.txt stat" > ys.log 2>&1 && grep -q 'cells' synth.txt; then
  pass "Yosys synthesis ($(grep -m1 -E '^ +[0-9]+ +cells|Number of cells' synth.txt | tr -s ' '))"; else fail "Yosys synthesis (see $TMPD/ys.log)"; fi
if timeout 300 sby -f counter.sby > sby.log 2>&1 && grep -q 'counter_prove.*PASS\|DONE (PASS' sby.log && [ "$(grep -c 'DONE (PASS' sby.log)" -ge 2 ]; then
  pass "SymbiYosys prove + cover (yices)"; else fail "SymbiYosys (see $TMPD/sby.log)"; fi

# ---------------------------------------------------------------- 4. Tiny Tapeout template, cocotb
head1 "4. Tiny Tapeout template: cocotb RTL test"
if [ ! -d "$SMOKE/.git" ]; then
  git clone -q "$TEMPLATE_URL" "$SMOKE" || fail "could not clone $TEMPLATE_URL"
fi
if [ -d "$SMOKE" ]; then
  cd "$SMOKE"
  [ -e tt ] || ln -s "$HOME/ttsetup/tt-support-tools" tt
  # The tools refuse to run with an empty title/author/description.
  sed -i -E 's/^(  title: +)""/\1"Setup smoke test"/; s/^(  author: +)""/\1"'"$USER"'"/; s/^(  description: +)""/\1"Template adder used to check the toolchain"/' info.yaml
  cd test
  if make -B > make_rtl.log 2>&1 && python -m cocotb_tools.check_results results.xml >> make_rtl.log 2>&1; then
    pass "cocotb + Icarus RTL test on the template"
  else fail "cocotb RTL test (see $SMOKE/test/make_rtl.log)"; fi
  cd "$SMOKE"
  if ./tt/tt_tool.py --pdk "$PDK" --create-user-config > cfg.log 2>&1; then pass "tt_tool.py --create-user-config"; else fail "tt_tool.py --create-user-config (see $SMOKE/cfg.log)"; fi
fi

# ---------------------------------------------------------------- 5. Docker
head1 "5. Docker"
if docker info > /dev/null 2>&1; then pass "Docker daemon reachable without sudo"
  if docker run --rm hello-world > "$TMPD/docker.log" 2>&1; then pass "docker run hello-world"; else fail "docker run hello-world (see $TMPD/docker.log)"; fi
else fail "Docker not reachable. Start Docker Desktop (WSL integration on) or the docker service; see the guide."; fi

# ---------------------------------------------------------------- 6. full harden (optional)
if [ "$MODE" = "--harden" ]; then
  head1 "6. Full flow: harden with LibreLane in Docker (first run downloads ~8 GB)"
  cd "$SMOKE"
  PDK_HASH=89d42ee6d2fd9b50b86a1aada6fee6673c3e6008   # LibreLane 3.1.0.dev4 pdk_hashes.yaml (ihp-sg13) = precheck pin
  if [ ! -d "$PDK_ROOT/$PDK/libs.ref" ]; then
    log "  Downloading and enabling the IHP PDK ($PDK_HASH) with ciel..."
    ciel enable --pdk-family "$PDK" "$PDK_HASH" >> "$REPORT" 2>&1
  fi
  [ -d "$PDK_ROOT/$PDK/libs.ref" ] && pass "IHP PDK present in $PDK_ROOT/$PDK" || fail "IHP PDK download failed (see report)"
  log "  Pulling the LibreLane image (7.6 GB the first time)..."
  if docker pull "ghcr.io/librelane/librelane:$LIBRELANE_TAG" > "$TMPD/pull.log" 2>&1; then pass "LibreLane image ghcr.io/librelane/librelane:$LIBRELANE_TAG"
  else fail "docker pull of the LibreLane image failed (see $TMPD/pull.log)"; fi
  START=$(date +%s)
  if docker image inspect "ghcr.io/librelane/librelane:$LIBRELANE_TAG" > /dev/null 2>&1; then
    ./tt/tt_tool.py --pdk "$PDK" --harden 2>&1 | tee harden.log | tail -5
  else log "  Skipping harden: the LibreLane image is not available."; fi
  if [ -f runs/wokwi/final/metrics.json ] && ls runs/wokwi/final/gds/*.gds > /dev/null 2>&1; then
    pass "harden finished in $(( ($(date +%s)-START)/60 )) min, GDS written"
    python - <<'PY' | tee -a "$REPORT"
import json
m = json.load(open("runs/wokwi/final/metrics.json"))
def g(k): return m.get(k, "n/a")
print("    cells (synth)     :", g("design__instance__count__stdcell") if "design__instance__count__stdcell" in m else g("design__instance__count"))
print("    setup WNS (ns)    :", g("timing__setup__ws"))
print("    hold WNS (ns)     :", g("timing__hold__ws"))
print("    route DRC errors  :", g("route__drc_errors"))
print("    Magic DRC errors  :", g("magic__drc_error__count"))
print("    LVS errors        :", g("design__lvs_error__count"))
PY
    ./tt/tt_tool.py --pdk "$PDK" --print-warnings > warnings.log 2>&1 && pass "print-warnings (see $SMOKE/warnings.log)"
    head1 "7. Gate-level cocotb test"
    TOP=$(./tt/tt_tool.py --pdk "$PDK" --print-top-module)
    LIBREF="$PDK_ROOT/$PDK/libs.ref"
    if [ ! -d "$LIBREF" ]; then
      ciel enable --pdk-family "$PDK" "$PDK_HASH" > /dev/null 2>&1 && warn "PDK was downloaded but not enabled; enabled $PDK_HASH (known first-run quirk)"
    fi
    cp "runs/wokwi/final/nl/$TOP.nl.v" test/gate_level_netlist.v
    cd test
    if make -B GATES=yes > make_gl.log 2>&1 && python -m cocotb_tools.check_results results.xml >> make_gl.log 2>&1; then
      pass "gate-level test on the hardened netlist"; else fail "gate-level test (see $SMOKE/test/make_gl.log)"; fi
  else
    fail "harden failed (see $SMOKE/harden.log and runs/wokwi/*/ logs)"
  fi
fi

# ---------------------------------------------------------------- summary
head1 "Summary"
log "  PASS: $PASS   WARN: $WARN   FAIL: $FAIL"
[ "$MODE" != "--harden" ] && log "  (Full flow not run. When this is all PASS, run: bash verify_setup.sh --harden)"
log "  Report saved to $REPORT"
[ "$FAIL" -eq 0 ]
