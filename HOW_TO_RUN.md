# How to run each tool (WSL)

Installed on 22 Nov 2026. Everything sits in your home folder, so nothing needed `sudo` and your existing Yosys and FPGA tools are untouched.

## Smoke test results (22 Nov 2026, unmodified IHP template, 1x1 tile)
| Check | Result |
|---|---|
| RTL cocotb test (Icarus 13 + cocotb 2.0.1) | PASS (1/1) |
| Harden with LibreLane 3.1.0.dev4, PDK `ihp-sg13cmos5l` | completed in 11.5 min, including the first-time downloads (Docker image 7.6 GB, plus the PDK) |
| Size | 87 standard cells, 2.8% utilisation |
| Timing | worst setup slack +10.3 ns, worst hold slack +7.9 ns (all 3 corners positive) |
| DRC (Magic), routing DRC, LVS, antenna | 0 errors |
| Gate-level cocotb test | PASS |
| Formal (`sby`, prove + cover, yices) | PASS, proof by k-induction |

The CTS warnings "No clock nets have been found" are expected here, because the template's example design is a pure adder with no flip-flops. On your own design with registers, that warning would be a real problem.

## 0. Open a terminal and load the environment (every time)

Open **Ubuntu** (WSL) and type:
```bash
ttenv
```
`ttenv` is an alias added to `~/.bashrc`. It runs `source ~/ttsetup/env.sh`, which does four things:
- turns on the Python 3.12 environment (`~/ttsetup/venv`) holding LibreLane, cocotb, pytest and the Tiny Tapeout tool dependencies
- puts **Icarus Verilog 13.0** first on your PATH. This is the same build Tiny Tapeout's gate-level CI uses, and it lives in `~/ttsetup/bin` as wrappers around `~/ttsetup/iverilog13`.
- adds **OSS CAD Suite** (`~/oss-cad-suite`, release 2026-11-21) for Verilator, GTKWave, Surfer, SymbiYosys, the solvers (yices, boolector, bitwuzla, z3), eqy and Yosys 0.71
- sets `PDK_ROOT=~/ttsetup/pdk`, `PDK=ihp-sg13cmos5l` and `LIBRELANE_TAG=3.1.0.dev4`

Without `ttenv`, your old setup is unchanged: Yosys 0.69 in `/usr/local/bin`, nextpnr and IceStorm.

Check that it worked:
```bash
which python iverilog verilator sby librelane   # should point into ~/ttsetup or ~/oss-cad-suite
iverilog -V | head -1                            # Icarus Verilog version 13.0
```

> **Work inside WSL's own disk** (for example `~/asic/...`), not `/mnt/c/...`. Builds on the Windows drive are much slower. To open WSL files from Windows Explorer, go to `\\wsl$\Ubuntu\home\hpomen\asic`.

---

## 1. Start your project from the template (once)

1. On GitHub, open https://github.com/TinyTapeout/ttihp-verilog-template and click **Use this template**. You can make the repo private for now.
2. In WSL:
```bash
ttenv
cd ~/asic
git clone https://github.com/<your-user>/<your-repo>.git
cd <your-repo>
git clone https://github.com/TinyTapeout/tt-support-tools tt   # the Tiny Tapeout helper, as the official guide says
```
3. Edit `info.yaml`. `title`, `author` and `description` must not be empty, or the tools refuse to run. Set `tiles: "8x4"`, set `top_module` to a name starting with `tt_um_`, and list your files under `source_files`. If you add files, also update `PROJECT_SOURCES` in `test/Makefile`.

A ready-made copy of the template is already in `~/asic/tt-smoke`. That's where I tested everything below, and you can practise on it.

---

## 2. Lint your Verilog (Verilator)
```bash
verilator --lint-only -Wall -Isrc src/*.v
```
Catches width mismatches, latches, unused or undriven signals. Aim for zero warnings you can't explain. The hardening flow runs the same lint, and GitHub shows its warnings.

## 3. RTL simulation with cocotb (Icarus)
```bash
cd test
make -B                                          # runs test.py against your RTL
python -m cocotb_tools.check_results results.xml # make passes even when tests fail, so this is the real check
```
- Results: `test/results.xml`
- Waveform: `test/tb.fst`

## 4. View waveforms
```bash
gtkwave test/tb.fst &      # classic viewer
surfer test/tb.fst &       # newer viewer, same file
```
Both open as windows on your Windows desktop through WSLg. Surfer also runs in a browser at https://surfer-project.org/ if you'd rather drag the file in there.

## 5. Harden: RTL to GDS (LibreLane in Docker)

Docker must be running. `docker ps` should print a header and no error.
```bash
cd ~/asic/<your-repo>
./tt/tt_tool.py --pdk $PDK --create-user-config   # rerun whenever info.yaml changes (tiles, files, clock)
./tt/tt_tool.py --pdk $PDK --harden               # full flow: synthesis, place, CTS, route, STA, DRC, LVS
./tt/tt_tool.py --pdk $PDK --print-warnings       # synthesis and clock warnings worth reading
```
Outputs land in `runs/wokwi/`. Useful places:
- `runs/wokwi/final/gds/`: the layout
- `runs/wokwi/final/nl/<top>.nl.v`: the gate-level netlist
- `runs/wokwi/final/metrics.json`: area, utilisation, timing slack and similar numbers
- each step's folder (`*-yosys-synthesis`, `*-openroad-*`, `*-klayout-drc`, ...): logs and reports

The first run is slow because it downloads the IHP PDK into `~/ttsetup/pdk` and pulls the LibreLane Docker image.

## 6. Gate-level simulation
```bash
cd test
TOP_MODULE=$(cd .. && ./tt/tt_tool.py --pdk $PDK --print-top-module)
cp ../runs/wokwi/final/nl/$TOP_MODULE.nl.v gate_level_netlist.v
make -B GATES=yes
python -m cocotb_tools.check_results results.xml
```
IHP uses the **unpowered** netlist (`nl`), per the official guide.

If this fails with `No rule to make target .../ihp-sg13cmos5l/libs.ref/...`, the PDK was downloaded but not "enabled". This happened to me once on the first run. Fix it like this:
```bash
ciel ls --pdk-family ihp-sg13cmos5l                    # copy the 40-character hash it prints
ciel enable --pdk-family ihp-sg13cmos5l <hash>
```

## 7. Look at the layout
```bash
./tt/tt_tool.py --pdk $PDK --open-in-klayout
./tt/tt_tool.py --pdk $PDK --open-in-openroad
```
If you see `could not connect to display`, run `xhost +local:docker` first.

## 8. Formal verification (SymbiYosys)
A working example is in `~/asic/formal-smoke`:
```bash
cd ~/asic/formal-smoke
sby -f counter.sby            # runs both tasks: prove and cover
sby -f counter.sby prove      # just one task
```
Read `counter.v` and `counter.sby`. The pattern is:
- properties go inside `` `ifdef FORMAL ``
- `assume` constrains inputs
- `assert` is what must always hold
- `cover` shows something can happen

After a failing proof, open the counterexample with `gtkwave counter_prove/engine_0/trace.vcd`.

## 9. Quick synthesis and area estimate (no full harden)
```bash
yosys -p "read_verilog src/*.v; synth -top <top_module>; stat"
```
This is a generic synthesis that's good for comparing blocks against each other. The real IHP cell count comes from the harden's synthesis report.

## 10. GitHub Actions (the official check)
Push to GitHub. The template runs `test`, `gds`, `precheck`, `gl_test` and `viewer`. All must be green before you submit. For the viewer job, enable GitHub Pages as described in https://tinytapeout.com/faq/.

---

## What's where
| Path | What |
|---|---|
| `~/ttsetup/env.sh` | the environment script (`ttenv`) |
| `~/ttsetup/venv` | Python 3.12: librelane 3.1.0.dev4, cocotb 2.0.1, pytest 8.4.2, ciel 3.3.0 |
| `~/ttsetup/bin` | Icarus 13 wrappers (`iverilog`, `vvp`) |
| `~/ttsetup/iverilog13` | Tiny Tapeout's Icarus 13.0 build, unpacked |
| `~/ttsetup/pdk` | IHP PDK (downloaded on first harden) |
| `~/ttsetup/tt-support-tools` | shared copy of the Tiny Tapeout tools (`tt` in the smoke test links here) |
| `~/oss-cad-suite` | Verilator, GTKWave, Surfer, sby, solvers, eqy, Yosys 0.71 |
| `~/asic/tt-smoke` | template copy used for the smoke test |
| `~/asic/formal-smoke` | formal example |

## Not done, needs you
- **More RAM for WSL (recommended before big 8x4 runs).** Create `C:\Users\siddh\.wslconfig` containing the lines below, then run `wsl --shutdown` in PowerShell and reopen Ubuntu.
  ```
  [wsl2]
  memory=12GB
  swap=16GB
  ```
- **PNG render of the layout (optional).** Needs `sudo apt install librsvg2-bin pngquant`, which asks for your password.
- **Old files you can delete later if you want the space:** `~/OpenLane` (OpenLane 1) and `~/.ciel` (sky130 PDK, 2.1 GB). I left them alone.

### Why Icarus is a separate copy
OSS CAD Suite's Icarus forces its own bundled Python, which breaks cocotb in your venv (I hit this during testing). So `ttenv` puts Tiny Tapeout's Icarus 13 first. As a bonus, it matches their gate-level CI exactly.
