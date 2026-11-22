"""UART TX test, ported onto tbkit (driver/monitor + reference model)."""
import os
import random

import cocotb
from cocotb.triggers import ClockCycles

from tbkit.cocotb_glue import TTHarness
from tbkit.models_uart import UartMonitor

CPB = int(os.environ.get("CLKS_PER_BIT", "16"))
PINMAP = {"TX": ("uo", 0), "BUSY": ("uo", 1), "SEND": ("uio", 0),
          "ACT": ("uio", 1), "ECHO_IN": ("uio", 2), "ECHO": ("uo", 2)}


async def setup(dut):
    tt = TTHarness(dut, PINMAP, pullups=["ACT"])
    tt.drive("SEND", "0")
    tt.drive("ECHO_IN", "0")
    await tt.start()
    mon = tt.attach(UartMonitor("TX", CPB))
    return tt, mon


async def send_byte(tt, b):
    """Adapt THIS function to your own Week-1 design's way of starting a frame."""
    while tt.read("BUSY"):
        await tt.cycles(1)
    tt.set_ui(b)
    tt.drive("SEND", "1")
    await tt.cycles(4)                 # long enough for the 2-flop synchroniser
    tt.drive("SEND", "0")
    await tt.cycles(4)


PATTERNS = {
    "alternating": [0x55, 0xAA],
    "all_zero_one": [0x00, 0xFF],
    "random": None,
}


@cocotb.test()
@cocotb.parametrize(pattern=list(PATTERNS))
async def test_uart_tx_bytes(dut, pattern):
    tt, mon = await setup(dut)
    data = PATTERNS[pattern] or [random.randrange(256) for _ in range(8)]
    dut._log.info(f"sending {[hex(b) for b in data]}")   # cocotb logs the seed at start-up
    for b in data:
        await send_byte(tt, b)
    await ClockCycles(dut.clk, CPB * 12)
    assert not mon.errors, mon.errors
    assert mon.received == data


@cocotb.test()
async def test_open_drain_activity_pin(dut):
    tt, mon = await setup(dut)
    assert tt.read("ACT") == 1, "released + pull-up should read high"
    await send_byte(tt, 0x00)
    assert tt.read("ACT") == 0, "chip should pull ACT low while busy"
    await ClockCycles(dut.clk, CPB * 11)
    assert tt.read("ACT") == 1


@cocotb.test()
async def test_input_synchroniser_latency(dut):
    tt, _ = await setup(dut)
    tt.drive("ECHO_IN", "1")
    await ClockCycles(dut.clk, 1)
    assert tt.read("ECHO") == 0          # not through the synchroniser yet
    await ClockCycles(dut.clk, 3)
    assert tt.read("ECHO") == 1


@cocotb.test(expect_fail=True)
async def test_contention_is_caught(dut):
    """Deliberately fight the chip on ACT: the harness must flag it."""
    tt, _ = await setup(dut)
    tt.drive("ACT", "1")                 # push-pull high from outside
    await send_byte(tt, 0x00)            # chip pulls ACT low -> fight
    await ClockCycles(dut.clk, 5)
