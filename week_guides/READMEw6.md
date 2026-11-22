# Week 6 toy example

Companion to `Week_06_Guide.pdf`. A deliberately tiny rule engine used to
practise the Week 6 methods before applying them to your real engine.

| File | What it is |
|---|---|
| `rtl/toy_engine.v` | 8-rule engine + byte loader, with formal properties P1-P6 under `ifdef FORMAL` |
| `rtl/fifo.v` | 4-entry FIFO for the induction lesson (helper assertion behind `HELPER`) |
| `formal/*.sby` | SymbiYosys jobs |
| `test/toy_model.py` | Python reference model |
| `test/gen.py` | constrained-random generators |
| `test/coverage.py` | functional coverage collector and merger |
| `test/test_toy_random.py` | cocotb tests: random regression + one directed test |
| `test/run_seeds.sh` | seed sweep, logs failing seeds, merges coverage |

Copy the folder into WSL (for example `~/asic/week6-toy`), run `ttenv`, then:

```bash
make formal     # expect: prove PASS (k-induction), cover PASS with 3 traces
make fifo       # expect: bmc PASS, prove_nohelper UNKNOWN (on purpose), prove PASS, cover PASS
make test       # expect: 2 tests PASS
make seeds      # expect: 0 failing seeds, coverage percentage and the remaining holes
```
