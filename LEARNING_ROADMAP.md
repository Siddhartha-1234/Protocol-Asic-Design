# Week-by-week roadmap: learning ASIC design while building the protocol emulator

Written 22 Nov 2026. Companion file: `TOOLCHAIN_STATUS.md` (tools installed and missing, install plan).

## How to use this file

- **Competition facts** come from the official rules (via the master doc) and are marked **[RULE]**.
- **Tool facts** were checked against the current Tiny Tapeout IHP template and build scripts and are marked **[FACT]**.
- **The schedule, task split, and expected numbers are my proposal**, marked **[PLAN]** or **[ESTIMATE]**. You decide the architecture, the team split, and any change to dates. Tell me and I'll update this file.
- The roadmap is **architecture-neutral**. Wherever it says "your engine", read whatever architecture you choose.

Each week has six parts:
1. **Goal**: the one sentence that matters.
2. **Do**: the concrete tasks, roughly in order.
3. **Learn**: the concepts you need this week, explained plainly, with resources.
4. **Test**: what you run to prove the week's work.
5. **Where you should be**: the checkpoint at the end of the week.
6. **Expected results**: what the outputs should look like, plus red flags that mean "stop and fix before moving on".

### Competition facts this plan is built around [RULE]
- Deadline **18 Jan 2027**. This plan targets submission on **16 Jan**, keeping 17-18 Jan as buffer.
- Process: **IHP 130 nm SG13CMOS5L** through Tiny Tapeout, max **8x4 tiles** (each about 202 x 155 µm), roughly 1K cells per tile as a loose guide.
- Pins: 8 in, 8 out, 8 bidirectional, plus clock and `rst_n`. 3.3 V digital only, no analog pads.
- Clock comes from the RP2350 on the demo board, and 60 MHz is confirmed OK. You choose a frequency that closes timing.
- Flops do **not** reset to 0 by themselves. When the design is deselected it loses all state, so the program must be reloaded.
- Must be **reprogrammable after fabrication** for new protocols. UART, SPI, and I2C are the required starting point.
- **Submit:** a public repo with RTL, tests, and a passing GDS + precheck from the Tiny Tapeout flow; architecture and instruction-set docs; an assembler or toolchain with example programs; and a verification write-up that includes how AI tools were used.
- Gate-level simulation is **strongly recommended**. The write-up is weighted heavily. **Flexibility is the main judging criterion.**

### Calendar [PLAN]
| Week | Dates | Theme |
|---|---|---|
| 1 | Sun 22 Nov - Sun 29 Nov | Tools working, flow understood, a trivial design taped out "on paper" |
| 2 | Mon 30 Nov - Sun 6 Dec | Spec, area and timing intuition, test infrastructure |
| 3 | Mon 7 Dec - Sun 13 Dec | Engine v0 running its first protocol program |
| 4 | Mon 14 Dec - Sun 20 Dec | UART + SPI + I2C as programs, first real harden |
| 5 | Mon 21 Dec - Sun 27 Dec | Full 8x4 layout, signoff checks, novelty feature |
| 6 | Mon 28 Dec - Sun 3 Jan | Verification build-out: formal, random, gate-level |
| 7 | Mon 4 Jan - Sun 10 Jan | Timing and area closure, **RTL freeze Sun 10 Jan** |
| 8 | Mon 11 Jan - Sat 16 Jan | Write-up, reproducibility, **submit Sat 16 Jan** |
| buffer | Sun 17 - Mon 18 Jan | Emergencies only |

---

## Week 1 (22-29 Nov): get the flow working end to end

**Goal:** a tiny design you wrote goes from Verilog to a GDS that passes Tiny Tapeout precheck, both on your laptop and on GitHub, at **8x4**.

Why first: every later week reuses this pipeline. If the backend is a mystery in December, it becomes a crisis in January.

### Do
1. **Install the toolchain** (`TOOLCHAIN_STATUS.md` section 3, once you approve): Python 3.12 venv, LibreLane 3.1.0.dev4, Icarus 13, cocotb 2.0.1, Verilator, Surfer or GTKWave. Optionally raise WSL memory to 12 GB.
2. **Create your repo** from https://github.com/TinyTapeout/ttihp-verilog-template ("Use this template"). It can stay private until submission [RULE]. Clone it into WSL (for example `~/asic/` rather than `/mnt/c/...`, which is much slower for builds [FACT about WSL]).
3. **Harden the untouched template** at `tiles: "1x1"` to prove the tools work.
4. **Write a small UART transmitter** (8N1, baud set by a parameter, data from `ui_in`, TX on `uo_out[0]`). Use synchronous reset on `rst_n` and a 2-flop synchronizer on any input you sample.
5. **Write a cocotb test** that decodes the TX line in Python and checks the bytes.
6. **Harden the UART at `tiles: "8x4"`**, then run gate-level simulation on the result.
7. **Push to GitHub** and get all four Actions green: `test`, `gds`, `precheck`, `gl_test`. Enable GitHub Pages so the `viewer` job works (see the Tiny Tapeout FAQ).
8. Start a `NOTES.md` in the repo: every command you ran and what each one did.

### Learn
**A. The RTL-to-GDS flow.** Know what each stage does and which file it leaves behind.
- *Lint* (Verilator) catches width mismatches, latches, and undriven nets before anything else runs.
- *Synthesis* (Yosys) turns your Verilog into a netlist of real IHP standard cells: NAND2, DFF, buffers, and so on.
- *Floorplan* sets the die box, pin positions, and power grid. Tiny Tapeout fixes these for you [RULE].
- *Placement* puts every cell at a legal spot in the cell rows.
- *CTS (clock tree synthesis)* builds a buffer tree so the clock reaches every flop at nearly the same time.
- *Routing* draws the metal wires between cells.
- *Signoff:* STA checks timing, DRC checks geometry rules, LVS checks that the layout matches the netlist, and antenna checks catch manufacturing damage risk.
- *GDS* is the layout file sent to the fab. *Precheck* is Tiny Tapeout's final gate before submission.

Resources:
- Zero to ASIC terminology, one plain paragraph per term: https://www.zerotoasiccourse.com/terminology/
- What LibreLane is: https://www.zerotoasiccourse.com/terminology/librelane/
- LibreLane docs, getting started: https://librelane.readthedocs.io/en/latest/getting_started/
- Tiny Tapeout local hardening guide (your main how-to this week): https://tinytapeout.com/guides/local-hardening/

**B. ASIC habits that differ from FPGA.**
- No power-on reset to 0 [RULE], so every flop that matters needs a reset value.
- No `initial` blocks for real logic.
- No free block RAM: arrays become flip-flops, which are large.
- Pin inputs are asynchronous to your clock and need synchronizers.
- Avoid latches, combinational loops, and generated clocks unless you really know why you need them.

Resources:
- Tiny Tapeout "Important!" HDL rules: https://tinytapeout.com/hdl/important/
- FPGA vs ASIC: https://tinytapeout.com/hdl/fpga_vs_asic/
- Tech specs for clock, GPIO, and memory: https://tinytapeout.com/specs/
- Cummings, *Synchronous Resets? Asynchronous Resets?*: http://www.sunburst-design.com/papers/CummingsSNUG2003Boston_Resets.pdf

**C. cocotb basics.** Your testbench is Python. `await RisingEdge(dut.clk)` waits for a clock edge. You set `dut.ui_in.value`, read `dut.uo_out.value`, and compare against a Python model.
- cocotb docs: https://docs.cocotb.org/en/stable/
- Tiny Tapeout "Testing your design": https://tinytapeout.com/hdl/testing/
- Read the template's `test/test.py`, `test/tb.v`, and `test/Makefile` line by line.

### Test
- `verilator --lint-only -Wall src/*.v` reports no warnings you can't explain.
- `cd test && make -B`, then `python -m cocotb_tools.check_results results.xml`.
- `./tt/tt_tool.py --pdk $PDK --harden` and `--print-warnings`.
- `make -B GATES=yes` using `runs/wokwi/final/nl/<top>.nl.v`. IHP uses the unpowered netlist [FACT].
- GitHub Actions, all green.

### Where you should be (Sun 29 Nov)
- [ ] Both teammates can rebuild from scratch by following `NOTES.md`.
- [ ] The UART-TX repo is green on all four Actions at 8x4.
- [ ] Each of you can explain the eight flow stages without notes, and can find the final timing report and the utilisation number in `runs/wokwi/`.
- [ ] You've opened the layout (`--open-in-klayout` or the Actions viewer) and found the standard-cell rows and the power stripes.

### Expected results [ESTIMATE]
- **First harden is slow** because it downloads the LibreLane Docker image and the IHP PDK, several GB in total. Later small hardens take minutes; Tiny Tapeout says local setup takes about 10 min [FACT].
- **UART TX size:** a few hundred cells or fewer. At 8x4 the utilisation will look tiny (well under 5%), which is expected.
- **Timing:** big positive slack at 50-60 MHz. If a UART fails timing, something is wrong with the clock definition, not the logic.
- **Gate-level sim** should pass exactly like the RTL sim. If it shows `X` on outputs, you have a missing reset.

**Red flags:**
- `pip install` fails building numpy: you're on Python 3.14, so switch to the 3.12 venv.
- The harden dies with "Killed" or out-of-memory: raise WSL memory.
- Precheck fails on a trivial design: usually a mistake in the `info.yaml` top module name or source list.

---

## Week 2 (30 Nov - 6 Dec): spec, area and timing intuition, test infrastructure

**Goal:** a written spec for your engine that you've checked against area and timing reality, plus a test setup that will scale to many protocols.

### Do
1. **Write the architecture spec (v1):** block diagram, programmable state (instruction or rule memory, registers, counters), how pins are read and driven, how a program is loaded from the RP2350 [RULE: loading is your job], and how the chip shows it's working. One to three pages.
2. **Write the programming-model spec:** the instruction or rule encoding, with a worked example of how a UART TX program looks in it. If you can't write UART TX, SPI mode 0, and I2C START plus a byte with ACK on paper, the spec isn't ready.
3. **Pin map (draft):** which of the 8 in, 8 out, and 8 bidirectional pins are for the program-load interface, and which are protocol pins. Note what each protocol needs externally, such as I2C pull-ups on a Pmod [RULE: document external needs].
4. **Area experiments:** synthesise standalone blocks (memory at a few sizes, register file, counter or divider, shifter) with your local Yosys and fill in the area table below.
5. **Timing experiments:** harden one experimental block, read its STA report, then break and fix timing on purpose (see Learn B).
6. **Test infrastructure:** a reusable cocotb structure with a pin-level driver and monitor per protocol, a Python reference model per protocol, and a test runner (pytest parametrisation) so new protocols are cheap to add.
7. **Assembler skeleton:** a Python script that turns your program text into the binary format and writes a file the cocotb tests load. It only needs 2-3 instructions or rule types so far.

### Learn
**A. Synthesis and area.**
- Yosys reports cell count, flop count, and area. Synthesis area is smaller than final area, because placement needs empty space and buffers get added.
- *Utilisation* means how full the die box is.
- Flops, wide multiplexers, and large memories dominate area. A memory built from flops costs one flop per bit plus a read mux.

Resources:
- Yosys docs, getting started and `stat`: https://yosyshq.readthedocs.io/projects/yosys/
- Tiny Tapeout memory spec: https://tinytapeout.com/specs/memory/
- For SRAM macros, see the IHP SRAM walkthrough linked from the official post: https://blog.janestreet.com/protocol-emulator-asic-competition/

**B. Static timing analysis (basics).**
- Timing is about paths from one flop, through logic, to the next flop.
- *Setup check:* data must arrive before the next clock edge minus the setup time. *Slack* = required time - arrival time. Negative slack means a violation.
- *Hold check:* data must not change too soon after the edge. The flow fixes hold violations by adding buffers.
- The *critical path* is the slowest path, and it sets your maximum frequency.
- A slower clock fixes setup violations, never hold violations.

Resources:
- VLSI Expert STA series: https://www.vlsi-expert.com/p/static-timing-analysis.html
- OpenSTA: https://github.com/parallaxsw/OpenSTA
- OpenROAD docs (`report_checks`): https://openroad.readthedocs.io/
- Harris & Harris, *Digital Design and Computer Architecture*, ch. 3.5 (timing of sequential logic)

**C. Synchronizers and CDC.** Every external pin is a clock-domain crossing. A synchronizer costs latency, typically 2 cycles. Understand why a multi-bit value can't simply be synchronised bit by bit.
- Cummings CDC paper: http://www.sunburst-design.com/papers/CummingsSNUG2008Boston_CDC.pdf

### Test
- Yosys `stat` on each block, entered into the area table.
- One harden with a deliberately long combinational path: confirm negative slack, add a register, confirm it recovers.
- cocotb: the UART test from week 1, ported onto the new infrastructure (driver, monitor, reference model).
- The assembler's output for one hand-written program, checked against the bits you expect by hand.

### Where you should be (Sun 6 Dec)
- [ ] Spec v1 and programming-model doc committed in `docs/`.
- [ ] UART, SPI, and I2C written on paper as programs for your engine.
- [ ] Area table filled in, with an estimated total under the 8x4 budget, including margin.
- [ ] A target clock frequency chosen (for example 50 MHz) and justified.
- [ ] Test infrastructure and assembler skeleton committed.

### Area table to fill in
| Block | Cells (Yosys) | Flops | Notes |
|---|---|---|---|
| Program/rule memory, size A | | | |
| Program/rule memory, size B | | | |
| Registers / counters | | | |
| Pin I/O + synchronizers | | | |
| Loader interface | | | |
| **Estimated total** | | | Compare to roughly 32K cells [RULE: loose guide] |

### Expected results [ESTIMATE]
- **Memory dominates.** Expect the program or rule memory to be the biggest block by far if it's built from flops. That table is what tells you how much programmability you can afford.
- **Aim for synthesis area at or below about 60-70% of the 8x4 budget.** Routing needs the space. A synthesis estimate near 100% means the design will not fit.
- **Simple blocks at 50-60 MHz** usually have plenty of slack on 130 nm. Deep compare trees or wide adders are where trouble starts.

**Red flags:**
- Your spec can't express I2C ACK handling or clock stretching. Flexibility is the main judging criterion, so revise the spec now.
- The area estimate exceeds budget: shrink memory, reduce engine count, or consider an SRAM macro (a big integration step, so decide this week, not later).

---

## Week 3 (7-13 Dec): engine v0 runs its first protocol program

**Goal:** your engine's RTL loads a program through the real load interface and transmits and receives UART correctly in simulation.

### Do
1. **Write engine RTL v0:** program/rule storage, execution or matching logic, pin input path with synchronizers, pin output and drive-enable path, and the counter or timer. Keep it minimal: only what UART needs.
2. **Write the program loader RTL** exactly as the RP2350 will use it (pins, protocol, timing). Remember that state is lost when the design is deselected [RULE].
3. **Write UART TX and UART RX programs** in your assembler.
4. **Write cocotb tests:**
   - *Instruction-level:* one test per instruction or rule type, each checking a single behaviour.
   - *Protocol-level:* UART TX and RX at 2-3 baud rates against the Python model.
5. **Write your first formal proof** on a small, self-contained block: the loader, a FIFO if you have one, or the synchronizer and edge detector.
6. **Run Verilator lint on every commit:** a `make lint` target, or wire it into CI.

### Learn
**A. Formal verification basics.** Instead of choosing inputs, a solver checks *every* possible input sequence.
- *BMC* (bounded model checking) proves nothing fails for N cycles. *Induction* proves it never fails.
- You write `assume` (legal inputs), `assert` (must always hold), and `cover` (must be reachable), inside `` `ifdef FORMAL ``.
- SymbiYosys (`sby`) runs Yosys plus an SMT solver (Yices, Boolector, Z3).

Resources:
- ZipCPU formal tutorial (best beginner path): https://zipcpu.com/tutorial/formal.html
- SymbiYosys docs: https://yosyshq.readthedocs.io/projects/sby/

**B. Testing strategy.** Separate *what the engine does* (instruction-level tests) from *whether a protocol works* (protocol-level tests with a reference model). Keep each test's seed so failures can be reproduced.

### Test
- `make lint`, `make -B` (cocotb), `sby -f <file>.sby` (formal).
- Harden the v0 engine at 8x4: first look at real area and slack.

### Where you should be (Sun 13 Dec)
- [ ] The engine loads a program through the real loader interface in simulation.
- [ ] UART TX and RX pass at 2-3 baud rates.
- [ ] At least one formal proof passes in `prove` mode.
- [ ] The engine v0 harden completes, and you have recorded its area and worst slack.

### Expected results [ESTIMATE]
- **First formal run usually fails.** It finds either a real bug or a missing `assume`. That's normal and is how you learn to read counterexample traces.
- **Engine v0 area** should land near your week-2 table, within about ±30%. If it's far off, find out why before adding features.
- **Gate-level sim of the loader** should already pass. Loader bugs at gate level almost always mean a missing reset.

**Red flags:**
- UART needs special-case hardware the spec didn't plan for. That's a sign the programming model is too weak for SPI and I2C too.
- The harden fails timing at your target clock already in v0.

---

## Week 4 (14-20 Dec): UART + SPI + I2C as programs, first real area check

**Goal:** all three required protocols run as programs on one unchanged engine, with an honest area and timing picture.

### Do
1. **Write the SPI programs:** controller mode, modes 0-3 (CPOL and CPHA), and at least one target-mode or MSB/LSB variant if your engine can do it.
2. **Write the I2C programs:** controller START, address, write and read bytes, ACK/NACK, STOP, at 100 kHz and 400 kHz. Use open-drain emulation: drive low or release, using the bidirectional pin's output enable.
3. **Add any engine features these exposed** (for example, branching on pin state for ACK). Re-run every earlier test after each change.
4. **Write reference-model tests:** an SPI device model (for example a simple register file or EEPROM model) and an I2C target model in Python that responds with ACKs.
5. **Harden nightly** from now on, logging each run in the runs table (see the Week 5 "Flow runs log").
6. **Start the write-up skeleton** in `docs/`: architecture, programming model, verification plan. Write it while you still remember why you made each decision.

### Learn
**A. STA in depth.**
- Read a full path report line by line: startpoint, endpoint, each cell delay, net delay, clock arrival, required time, slack.
- *Setup and hold across corners:* the flow analyses slow and fast process/voltage/temperature corners.
- *I/O timing:* about 10 ns pin round trip is estimated [RULE], so very fast sampling needs care.
- Resources: as in Week 2, plus the LibreLane docs on the STA steps.

**B. Bidirectional pins and open-drain.** In Tiny Tapeout, `uio_oe` controls whether each bidirectional pin drives [FACT, template]. Open-drain means driving 0 or letting the pin float high through an external pull-up, which goes on the Pmod [RULE].

**C. Protocols.**
- NXP I2C-bus specification UM10204 (START/STOP, ACK, clock stretching).
- SparkFun's plain-language UART, SPI, and I2C tutorials.

### Test
- The full regression: instruction-level tests plus three protocols, multiple speeds and modes.
- The nightly harden: area, slack, and runtime logged.
- A gate-level sim of at least the UART test on the nightly netlist.

### Where you should be (Sun 20 Dec)
- [ ] UART, SPI modes 0-3, and I2C at 100 and 400 kHz pass as programs, **with no protocol-specific RTL**.
- [ ] The full regression runs in CI in reasonable time (under about 15 min).
- [ ] Area and slack known from a real harden of the whole engine.
- [ ] Write-up skeleton committed.

### Expected results [ESTIMATE]
- **Utilisation** somewhere around 30-60% of 8x4 for a modest engine. Your number will depend heavily on memory size.
- **Positive setup slack** at your target clock, or a known single critical path you can fix next week.
- **Harden runtime** grows with the design: tens of minutes on your laptop is normal for a well-filled 8x4.

**Red flags:**
- Utilisation over about 70%: routing will struggle. Cut now.
- I2C needs hacks: your pin model or branching is too weak, and that hurts the flexibility story.
- Harden runtime approaching hours: plan to harden locally and use Tiny Tapeout's custom GDS action [RULE: allowed if it passes precheck].

---

## Week 5 (21-27 Dec): full layout, signoff checks, novelty

**Goal:** the real design is placed and routed at 8x4 with clean DRC, LVS, and precheck, and your novelty feature is in progress.

### Do
1. **Get the full design to precheck** on GitHub Actions.
2. **Review the layout** in KLayout or the OpenROAD GUI: congestion hotspots, the clock tree, where the memory ended up.
3. **If you use an IHP SRAM macro**, integrate it *this week* following the walkthrough linked from the official post. Macros are the most common cause of DRC, LVS, and power-grid trouble.
4. **Build your novelty feature:** whatever you decide sets your entry apart. Keep it behind a parameter or `define` so you can drop it if it threatens the schedule.
5. **Test a protocol you didn't design for.** Write a program for JTAG, SWD, PS/2, or similar on the *unchanged* engine. This is the strongest evidence for the flexibility criterion [RULE: main judging criterion].

### Learn
**A. Place and route knobs.**
- *Placement density* (how tightly cells pack) trades area against routability.
- *Congestion* happens when too many wires want the same tracks.
- Long nets add delay, and the flow inserts buffers (*repair_design*, *resizer*).
- Resources: the LibreLane step reference (https://librelane.readthedocs.io/) and the OpenROAD flow tutorial (https://openroad-flow-scripts.readthedocs.io/en/latest/tutorials/FlowTutorial.html). The latter uses a different wrapper over the same engine, with good pictures.

**B. DRC, LVS, and antenna.**
- *DRC:* shapes too thin or too close. *LVS:* layout is not the same circuit as the netlist. *Antenna:* long wires during manufacturing; the flow adds diodes.
- Pure standard-cell designs usually pass. Macros and hand edits are where failures come from.
- Resources: Zero to ASIC terminology, and the `precheck/` folder in https://github.com/TinyTapeout/tt-support-tools

### Test
- Precheck: `gds`, `precheck`, and `gl_test` Actions all green.
- Novelty feature: its own instruction-level and protocol-level tests.
- "Unplanned protocol" test: a cocotb test with a reference model.

### Where you should be (Sun 27 Dec)
- [ ] The full design passes precheck on GitHub.
- [ ] The novelty feature works in RTL sim.
- [ ] At least one protocol beyond UART/SPI/I2C runs with **zero RTL changes**.
- [ ] A Flow runs log table exists and is up to date.

### Flow runs log (keep in the repo)
| Date | Commit | Clock | Utilisation | Worst setup slack | Worst hold slack | Runtime | Peak RAM | Precheck |
|---|---|---|---|---|---|---|---|---|

### Expected results [ESTIMATE]
- **DRC and LVS clean** without manual effort for a pure standard-cell design. If you added SRAM, expect one or two iterations.
- **Antenna violations:** often a handful that the flow repairs automatically. Persistent ones point to very long nets.
- **Gate-level sim passes** the same tests as RTL.

**Red flags:**
- Precheck fails in a way you can't understand within a day: ask in the Tiny Tapeout Discord, or email the organizers for clarification. They answer specific questions but won't review designs [RULE].
- The novelty feature isn't converging: freeze it behind its parameter and move on to verification.

---

## Week 6 (28 Dec - 3 Jan): verification build-out

**Goal:** a verification story you can defend: formal proofs on the key invariants, constrained-random testing, gate-level simulation, and coverage numbers.

### Do
1. **Write formal properties for the engine** (adapt them to your architecture):
   - Reset reaches a known state.
   - No deadlock or livelock under legal inputs.
   - Pins are never driven in an illegal combination (for example, an open-drain pin never driven high).
   - The loader writes exactly what was sent.
   - FIFO or buffer invariants hold.
   - Your engine's own ordering or priority rules hold.
2. **Add constrained-random tests:** random legal programs and random pin input sequences, checked against a Python model of the engine. Run many seeds in CI and keep failing seeds as regression tests.
3. **Collect coverage:** which instructions or rule types, branches, and protocol modes the tests actually hit. Even a simple Python counter of instruction usage is fine.
4. **Run gate-level sim on the full suite,** or a documented subset if it's too slow.
5. **Optional:** equivalence check of RTL against the netlist with `eqy` (https://github.com/YosysHQ/eqy), and FPGA validation using your iCE40/ECP5 tools. FPGA validation is suggested by the organizers [RULE].
6. **Draft the verification section** of the write-up, including how you used AI tools [RULE].

### Learn
- **Induction and strengthening assertions:** why `prove` mode fails when BMC passes, and how to add helper assertions. ZipCPU tutorial, later lessons: https://zipcpu.com/tutorial/
- **Constrained-random testing:** generate only *legal* stimulus (constraints), check against a model (scoreboard), measure what you covered.
- **X-propagation in gate-level sim:** why an unreset flop shows as `X`, and why that bug is invisible in RTL.

### Test
- `make formal`: all proofs pass, and each has a cover trace showing it isn't vacuous.
- Random regression over at least a few thousand programs and seeds.
- `make -B GATES=yes`.

### Where you should be (Sun 3 Jan)
- [ ] A list of formal properties, each passing, documented with what it guarantees.
- [ ] The random regression is green, with any bugs it found logged (these are great write-up material).
- [ ] The gate-level suite is green.
- [ ] Verification write-up draft exists.

### Expected results [ESTIMATE]
- **Random testing finds real bugs** you didn't catch in directed tests. If it finds zero, check that it's actually generating interesting programs.
- **Some properties won't prove by induction at first.** Plan time to add helper assertions.
- **Gate-level sim is much slower than RTL** (often 10x or more). A smaller GL subset is acceptable if documented.

**Red flags:**
- Gate-level and RTL results differ: stop and find out why. It's usually a reset or X issue, occasionally a tool bug. The organizers flag both [RULE].

---

## Week 7 (4-10 Jan): timing and area closure, RTL freeze

**Goal:** a clean final harden at your chosen clock, precheck green, RTL frozen on Sun 10 Jan.

### Do
1. **Fix every remaining setup and hold violation** at the frequency in `info.yaml` (`clock_hz`).
2. **Fix all lint warnings** and review `--print-warnings`.
3. **Decide the final feature set.** Anything not stable by Thursday 7 Jan is removed or disabled.
4. **Produce demos:** waveform screenshots and a short recording or script showing each protocol running as a program. Plan how the RP2350 loads programs on the real board, and document it.
5. **Freeze RTL Sunday 10 Jan:** tag the commit, and from then on allow only documentation and test changes.

### Learn
**Timing closure method, in order:**
1. Find the critical path.
2. Restructure or pipeline it.
3. Lower the clock if your protocols don't need the speed.
4. Only then tune flow knobs.

Hold issues are normally fixed by the flow. Resources: Week 2 and Week 4 STA material.

### Test
- The final full harden, the full regression, formal, and gate-level sim, all from the tagged commit.
- A **clean-checkout test:** clone the repo fresh into a new folder, follow only the README, and confirm everything passes.

### Where you should be (Sun 10 Jan)
- [ ] Tagged RTL freeze commit.
- [ ] All Actions green on that commit: `test`, `gds`, `precheck`, `gl_test`, `viewer`.
- [ ] Zero timing violations reported.
- [ ] Demos recorded or scripted.

### Expected results [ESTIMATE]
- **The final numbers go into the write-up:** utilisation, frequency, cell count, and the protocols demonstrated.

**Red flags:**
- Still fighting precheck or timing after Wednesday 7 Jan: cut features rather than slip the freeze.

---

## Week 8 (11-16 Jan): write-up and submission

**Goal:** a judge can understand the novelty, run the tests, and see the protocols working within about 10 minutes of opening your repo.

### Do
1. **README:** a one-sentence novelty statement, block diagram, "run the tests in 3 commands", results summary, and pin map with any external parts needed [RULE].
2. **Architecture and programming-model reference:** every instruction or rule, its encoding, and an example of each [RULE: architecture and ISA docs].
3. **Toolchain:** the assembler, with usage docs and one example program per protocol, including the "not designed for" protocol [RULE].
4. **Verification report:** methods, tools, formal property list, random-test stats, gate-level results, bugs found, and the AI-tool usage section [RULE].
5. **Update Tiny Tapeout's own `docs/info.md`** (the datasheet page).
6. **Optional:** a short demo video. Judges look at it if provided [RULE].
7. **Final clean-checkout re-run,** then make the repo public and submit through the form on the official blog page by **Sat 16 Jan** [RULE: the form is added near the deadline].

### Learn
Technical writing: one idea per section, lead with results, use diagrams. The write-up is weighted heavily, and judges value readability and a clear explanation of new techniques [RULE].

### Test
- Ask someone outside the team (the PhD student or a classmate) to follow the README cold. Fix everything they stumble on.

### Where you should be (Sat 16 Jan)
- [ ] Submitted. The repo is public, all Actions are green, and the docs are complete.

---

## Background drills (if any fundamentals feel shaky)
| Topic | Resource | You're good when |
|---|---|---|
| Verilog fluency | HDLBits: https://hdlbits.01xz.net/ | The FSM and verification sections feel easy |
| Quick reference | ChipVerify: https://www.chipverify.com/ | Use it as a lookup |
| Timing fundamentals | Harris & Harris, *Digital Design and Computer Architecture*, ch. 3 | You can compute max frequency from t_clk-q, t_pd, and t_setup |
| What a standard cell is | Weste & Harris, *CMOS VLSI Design*, ch. 1-2; SiliWiz: https://tinytapeout.com/siliwiz/ | You can sketch CMOS NAND and inverter transistors |
| Lint | Verilator guide: https://verilator.org/guide/latest/ | `make lint` is clean |
| PDK layout of files | IHP Open PDK: https://github.com/IHP-GmbH/IHP-Open-PDK | You know where the stdcell Verilog and liberty files are |

## Weekly rhythm [PLAN]
- **Friday:** 15-minute check against this file. Tick boxes, and move anything slipping to a "cut list".
- **From week 4:** harden nightly, and log every run.
- Always keep a working minimum version: engine + UART/SPI/I2C + assembler + docs, green on Actions. Add novelty on top of that, never in place of it.
