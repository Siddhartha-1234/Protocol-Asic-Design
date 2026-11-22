# Toolchain status for the Tiny Tapeout IHP flow

Checked on 22 Nov 2026 by probing WSL (Ubuntu 26.04.1, 16 cores) and reading the current Tiny Tapeout sources:
the IHP template (`ttihp-verilog-template`, main), `tt-gds-action@ttihp27a`, and the
[local hardening guide](https://tinytapeout.com/guides/local-hardening/).

Labels: **[FACT]** = checked on your machine or in the official sources today. **[SUGGESTION]** = my recommendation. **[UNSURE]** = verify before relying on it.

**Update 22 Nov 2026: everything recommended below is now installed (no sudo needed) and smoke-tested. See `HOW_TO_RUN.md` for how to use each tool. Still open: the `.wslconfig` RAM change and the optional `librsvg2-bin pngquant` apt packages.**

---

## 1. How the official flow actually runs [FACT]

This is what the GitHub Actions in the template do, and what the local guide replicates:

| Step | Tool | Where it runs |
|---|---|---|
| RTL tests | cocotb 2.0.1 + pytest 8.4.2 + Icarus Verilog | native (`test/requirements.txt`, `test/Makefile`, `SIM ?= icarus`) |
| Config generation | `tt-support-tools` (`tt/tt_tool.py --pdk ihp-sg13cmos5l --create-user-config`) | native Python |
| Hardening (RTL to GDS) | **LibreLane 3.1.0.dev4** (pip). Internally: Yosys synthesis, OpenROAD floorplan/place/CTS/route, OpenSTA timing, Magic + KLayout DRC, Netgen LVS, Verilator lint | **Docker container** that LibreLane pulls. "Requires Docker" per the guide |
| PDK | `ihp-sg13cmos5l`, fetched by **ciel** (LibreLane 3.1 needs ciel >= 3). Precheck pins PDK commit `89d42ee6d2fd9b50b86a1aada6fee6673c3e6008` | `PDK_ROOT=~/ttsetup/pdk` |
| Gate-level sim | cocotb + Icarus with the IHP cell models, `GATES=yes make`, using the **unpowered** netlist `runs/wokwi/final/nl/<top>.nl.v` | native |
| Precheck | `tt-support-tools/precheck` run inside **Nix** | CI (can be run locally, optional) |

Key consequence: **you do not need OpenROAD, Magic, Netgen or KLayout installed natively.** LibreLane brings them in its Docker image. A native KLayout is only a convenience for looking at layouts.

---

## 2. What you have vs what you need

| Tool | Status on your WSL | Needed? | Notes |
|---|---|---|---|
| Yosys 0.69 | ✅ `/usr/local/bin/yosys` | Nice to have | Good for quick synthesis / area estimates and formal. The real flow uses LibreLane's own Yosys. [FACT] |
| yosys-smtbmc | ✅ | For formal | Needs `sby` and a solver to be useful. |
| nextpnr-ice40 / -ecp5, IceStorm, Trellis | ✅ | **No (FPGA only)** | Only useful for optional FPGA validation. Not part of the ASIC flow. [FACT] |
| Docker 29.8.2 | ✅ daemon reachable, no sudo needed | **Yes** | Only `hello-world` image so far. LibreLane will pull a multi-GB image on first harden. [FACT] |
| git, make, gcc, cmake | ✅ | Yes | |
| Python 3.14.4 (system) | ⚠️ too new | Yes, but use **3.12** | `tt-support-tools` pins `numpy==1.26.4`, which has no wheels for 3.14, and cocotb 2.0.1 lists support up to 3.13. CI uses 3.11. [FACT] Use a uv-managed Python 3.12 venv. [SUGGESTION] |
| `~/OpenLane` (OpenLane 1, `superstable` branch) | ⚠️ present but obsolete | **No** | Old Tcl-based OpenLane. Tiny Tapeout IHP uses **LibreLane** (its successor). Don't use it for this project. [FACT] |
| `~/.ciel` with sky130A/B | ⚠️ wrong PDK | No | That's the SkyWater 130 nm PDK. You need IHP `ihp-sg13cmos5l`. ciel will fetch it on first harden. [FACT] |
| OpenROAD (native) | ❌ | No | Comes inside LibreLane's container. |
| **LibreLane 3.1.0.dev4** | ❌ | **Yes** | `pip install librelane==3.1.0.dev4` in the venv. |
| **tt-support-tools** | ❌ | **Yes** | `git clone` into `tt/` inside the project repo, then `pip install -r tt/requirements.txt`. |
| **IHP SG13CMOS5L PDK** | ❌ | **Yes** | Auto-downloaded by ciel into `$PDK_ROOT`. |
| **Icarus Verilog** | ❌ | **Yes** | Required by the template tests. TT's GL-test CI installs their own build, `iverilog 13.0` (`.deb` from github.com/TinyTapeout/iverilog). [FACT] Use the same for parity. [SUGGESTION] |
| **cocotb 2.0.1 + pytest** | ❌ | **Yes** | `pip install -r test/requirements.txt`. |
| Verilator | ❌ | Recommended | Lint locally before hardening (LibreLane runs a Verilator lint step and CI shows its warnings). Also a faster simulator for long random tests. |
| Waveform viewer: Surfer or GTKWave | ❌ | Recommended | Template dumps `tb.fst`. Surfer reads FST and also runs in the browser at [surfer-project.org](https://surfer-project.org/). |
| KLayout (native) | ❌ | Optional | `tt_tool.py --open-in-klayout` works through Docker (needs `xhost +local:docker`). A native install is easier on WSLg. |
| **SymbiYosys (`sby`) + solvers** | ❌ (only smtbmc) | **Yes, for your formal plan** | Need `sby` plus at least one solver: Yices 2 (fast default for `smtbmc`), Boolector or Bitwuzla, Z3. Easiest source: OSS CAD Suite. |
| eqy (equivalence checking) | ❌ | Optional | Nice for proving RTL == gate netlist as a verification-story extra. |
| Nix | ❌ | Optional | Only to run precheck locally. CI runs it for you. |
| uv | ❌ | Recommended | Gives you Python 3.12 without touching system Python. |
| Magic, Netgen | ❌ | No | Inside LibreLane's container. |

### Machine resources [FACT + SUGGESTION]
- Windows has **15.3 GB RAM**, but WSL currently sees only **7.4 GB** (the default is half) and you have no `.wslconfig`.
- The PhD student's guideline was 16 GB. 8x4 tiles is the largest Tiny Tapeout size, and routing a ~30K-cell design inside 7 GB may be tight. **[UNSURE]**: we'll know on the first full-size run.
- [SUGGESTION] Create `C:\Users\siddh\.wslconfig` with `memory=12GB` and `swap=16GB`, then `wsl --shutdown`. This is a system setting, so it's your call. See [WSL config docs](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).
- Disk is fine: 939 GB free.

---

## 3. Proposed install plan (waiting for your OK)

Nothing here touches your existing Yosys/FPGA setup.

**A. Python environment (uv + Python 3.12)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # installs uv into ~/.local/bin
mkdir -p ~/ttsetup && uv venv --python 3.12 ~/ttsetup/venv
source ~/ttsetup/venv/bin/activate
```

**B. Env vars (add to `~/.bashrc` or a `~/ttsetup/env.sh` you source)** [FACT: values from the official guide and the tt-gds-action defaults]
```bash
export PDK_ROOT=~/ttsetup/pdk
export PDK=ihp-sg13cmos5l
export LIBRELANE_TAG=3.1.0.dev4
```

**C. LibreLane + project tooling** (inside the venv)
```bash
pip install librelane==$LIBRELANE_TAG
# in your project repo (made from ttihp-verilog-template):
git clone https://github.com/TinyTapeout/tt-support-tools tt
pip install -r tt/requirements.txt
pip install -r test/requirements.txt      # cocotb 2.0.1, pytest 8.4.2
```

**D. Simulators and viewers (apt, needs sudo)**
```bash
sudo apt update
sudo apt install -y verilator gtkwave librsvg2-bin pngquant
# Icarus 13 matching Tiny Tapeout's GL-test CI:
wget https://github.com/TinyTapeout/iverilog/releases/download/v13.0/iverilog_13.0-1_amd64.deb
sudo apt install -y ./iverilog_13.0-1_amd64.deb
```
[UNSURE] That `.deb` is built for Ubuntu 24.04. If it won't install on 26.04, fall back to `sudo apt install iverilog` and check `iverilog -V` is 12 or newer.

**E. Formal tools**: two options, pick one [SUGGESTION: option 1]
1. **OSS CAD Suite** (prebuilt sby, yices, boolector, bitwuzla, z3, eqy, plus Surfer-compatible tools): download the latest `linux-x64` tarball from [oss-cad-suite-build releases](https://github.com/YosysHQ/oss-cad-suite-build) into `~/oss-cad-suite`, and **only source it in a formal-work shell** (`source ~/oss-cad-suite/environment`) so it doesn't shadow your `/usr/local/bin/yosys`.
2. apt: `sudo apt install yices2 z3 boolector` plus build `sby` from source. More fiddly.

**F. Optional**
- KLayout native: `sudo apt install klayout` (check version) or the .deb from [klayout.de](https://www.klayout.de/).
- Remove or ignore `~/OpenLane` and the sky130 PDK in `~/.ciel` (2.1 GB) later. I won't delete anything without asking.

**G. Smoke test (the real done-check)**
Fork the template, set `tiles: "8x4"` and a trivial design, then:
```bash
./tt/tt_tool.py --pdk $PDK --create-user-config
./tt/tt_tool.py --pdk $PDK --harden          # first run pulls the Docker image + PDK
./tt/tt_tool.py --pdk $PDK --print-warnings
cd test && make -B                            # RTL tests
cp ../runs/wokwi/final/nl/$(cd .. && ./tt/tt_tool.py --pdk $PDK --print-top-module).nl.v gate_level_netlist.v
make -B GATES=yes                             # gate-level tests
```
Also push to GitHub and confirm the `gds`, `precheck`, `gl_test` and `test` Actions all go green.
