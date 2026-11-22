# SPDX-FileCopyrightText: © 2026 Siddhartha
# SPDX-License-Identifier: Apache-2.0
#
# Week 1 tests for the UART transmitter.
# A Python "reference receiver" watches the TX pin and decodes bytes,
# then we compare them with what we asked the chip to send.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

CLK_PERIOD_NS = 20               # 50 MHz, matches clock_hz in info.yaml
CLKS_PER_BIT = {0: 434, 1: 50}   # BAUD pin value -> clock cycles per bit


def tx_bit(dut):
    """Current value of the TX pin (uo_out[0])."""
    return int(dut.uo_out.value) & 1


def busy_bit(dut):
    """Current value of the BUSY pin (uo_out[1])."""
    return (int(dut.uo_out.value) >> 1) & 1


async def reset(dut):
    clock = Clock(dut.clk, CLK_PERIOD_NS, unit="ns")
    cocotb.start_soon(clock.start())
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def send_byte(dut, value, baud_sel):
    """Behave like the RP2350: put data on ui_in, then pulse SEND (uio_in[0])."""
    dut.ui_in.value = value
    dut.uio_in.value = (baud_sel << 1) | 0
    await ClockCycles(dut.clk, 2)                 # data settles before SEND rises
    dut.uio_in.value = (baud_sel << 1) | 1        # SEND high
    while busy_bit(dut) == 0:                     # wait until the chip has taken the byte
        await RisingEdge(dut.clk)
    dut.uio_in.value = (baud_sel << 1) | 0        # SEND low again


async def receive_byte(dut, clks_per_bit, timeout_cycles=200_000):
    """Reference receiver: decode one 8N1 frame from the TX pin.

    Waits for the falling edge of the start bit, moves to the middle of the
    start bit, then samples each following bit in its middle.
    """
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        if tx_bit(dut) == 0:
            break
    else:
        raise AssertionError("timed out waiting for a start bit")

    await ClockCycles(dut.clk, clks_per_bit // 2)
    assert tx_bit(dut) == 0, "start bit did not stay low until its middle (glitch?)"

    value = 0
    for i in range(8):
        await ClockCycles(dut.clk, clks_per_bit)
        value |= tx_bit(dut) << i                # UART sends LSB first

    await ClockCycles(dut.clk, clks_per_bit)
    assert tx_bit(dut) == 1, "stop bit was not high (framing error)"
    return value


@cocotb.test()
async def test_idle_after_reset(dut):
    """Straight after reset the line must idle high and BUSY must be low."""
    await reset(dut)
    for _ in range(100):
        await RisingEdge(dut.clk)
        assert tx_bit(dut) == 1, "TX must idle high"
        assert busy_bit(dut) == 0, "BUSY must be low when idle"
    assert (int(dut.uo_out.value) >> 2) == 0, "unused outputs must be 0"


async def check_bytes(dut, data, baud_sel):
    clks = CLKS_PER_BIT[baud_sel]
    for value in data:
        rx = cocotb.start_soon(receive_byte(dut, clks))
        await send_byte(dut, value, baud_sel)
        got = await rx
        dut._log.info(f"sent 0x{value:02X}, decoded 0x{got:02X} ({clks} clks/bit)")
        assert got == value, f"sent 0x{value:02X} but decoded 0x{got:02X}"
        while busy_bit(dut) == 1:                 # let the frame finish
            await RisingEdge(dut.clk)


@cocotb.test()
async def test_bytes_1mbaud(dut):
    """Corner-case bytes at the fast rate (50 clocks per bit)."""
    await reset(dut)
    await check_bytes(dut, [0x55, 0xAA, 0x00, 0xFF, 0x01, 0x80], baud_sel=1)


@cocotb.test()
async def test_bytes_115200(dut):
    """Three bytes at 115200 baud (434 clocks per bit)."""
    await reset(dut)
    await check_bytes(dut, [0x48, 0x69, 0x21], baud_sel=0)   # "Hi!"


@cocotb.test()
async def test_random_bytes(dut):
    """Twenty random bytes at the fast rate, with a fixed seed so failures repeat."""
    rng = random.Random(1234)
    await reset(dut)
    await check_bytes(dut, [rng.randrange(256) for _ in range(20)], baud_sel=1)


@cocotb.test()
async def test_frame_length(dut):
    """BUSY must stay high for exactly 10 bit periods (start + 8 data + stop)."""
    await reset(dut)
    clks = CLKS_PER_BIT[1]
    rx = cocotb.start_soon(receive_byte(dut, clks))
    await send_byte(dut, 0xA5, baud_sel=1)
    cycles = 0
    while busy_bit(dut) == 1:
        await RisingEdge(dut.clk)
        cycles += 1
    await rx
    # send_byte returns one cycle after BUSY rose, so allow +/-2 cycles.
    assert abs(cycles - 10 * clks) <= 2, f"frame took {cycles} cycles, expected about {10 * clks}"


@cocotb.test()
async def test_send_held_high_sends_once(dut):
    """Holding SEND high must not start a second frame (we trigger on the edge)."""
    await reset(dut)
    clks = CLKS_PER_BIT[1]
    dut.ui_in.value = 0x3C
    dut.uio_in.value = 0b11                      # fast baud, SEND high and kept high
    got = await receive_byte(dut, clks)
    assert got == 0x3C
    await ClockCycles(dut.clk, 30 * clks)         # three more frame times
    assert tx_bit(dut) == 1 and busy_bit(dut) == 0, "a second frame started"
