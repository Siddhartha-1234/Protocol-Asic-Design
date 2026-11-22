# Week 4 kit (tested 22 Nov 2026 with Icarus 12/13, cocotb 2.0.1, Python 3.11 to 3.13)

Copy into your repo:
    test/models/            -> test/models/          (pin-level UART, SPI, I2C models + I2C timing checker)
    test/fixtures/          -> test/fixtures/        (TESTBENCH-ONLY known-good controllers; never in info.yaml)
    test/test_fixtures.py   -> test/                 (19 tests that prove the models)
    test/test_runner.py     -> test/                 (pytest entry: pytest -n auto -q test_runner.py)
    test/tb_open_drain.v    -> replace test/tb.v     (open-drain bus with pull-ups on uio[0], uio[1])
    tools/*                 -> tools/                (area_check.sh, runs_log.py, nightly.sh)
    ci/regression.yaml      -> .github/workflows/
    docs/writeup_skeleton.md -> docs/

Prove it works on your machine first:
    ttenv && cd test && pip install pytest-xdist && pytest -n auto -q test_runner.py
    expected: "19 passed"

Everything is explained in Week_04_Guide.pdf, section 6.
