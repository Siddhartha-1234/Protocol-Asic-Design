"""Run the paper programs on the engine model against protocol device models."""
from pathlib import Path

import pytest

import asm
from engine_model import Lane
from harness import simulate
from tbkit.models_i2c import I2cTarget
from tbkit.models_spi import SpiTarget
from tbkit.models_uart import UartDriver, UartMonitor

PROGS = Path(__file__).resolve().parents[1] / "programs"


def load(name, **overrides):
    src = (PROGS / f"{name}.rules").read_text()
    for k, v in overrides.items():                 # e.g. baud=9600 -> edit directive text
        src = src.replace(k, v)
    prog, _ = asm.assemble(src)
    return Lane(prog)


@pytest.mark.parametrize("baud", ["115200", "9600", "1000000"])
def test_uart_tx(baud):
    lane = load("uart_tx", **{"bit(115200)": f"bit({baud})"})
    cpb = round(50e6 / int(baud))
    mon = UartMonitor("TX", cpb)
    data = [0x55, 0x00, 0xFF, 0xA3]
    for b in data:
        assert lane.push_tx(b)
    trace = []
    simulate(lane, [mon], cycles=cpb * 10 * 5, trace=trace)
    assert mon.received == data and not mon.errors
    # every bit of 0x55 (alternating) must last exactly one bit period
    tx = [t["TX"] for t in trace]
    first = tx.index(0)
    runs, n = [], 1
    for a, b in zip(tx[first:first + cpb * 10], tx[first + 1:first + cpb * 10]):
        if a == b:
            n += 1
        else:
            runs.append(n)
            n = 1
    assert runs[:9] == [cpb] * 9


def test_uart_rx_bytes_and_framing_error():
    lane = load("uart_rx")
    cpb = round(50e6 / 115200)
    drv = UartDriver("RX", cpb, gap_bits=1)
    drv.send([0x12, 0xC3, 0x7E])
    simulate(lane, [drv], cycles=cpb * 11 * 4)
    assert list(lane.rxf) == [0x12, 0xC3, 0x7E] and lane.flag == 0

    class BadStop(UartDriver):           # frame with a 0 where the stop bit belongs
        def step(self, levels):
            if not self._bits and self.queue:
                self._bits, self._cnt = [0] + [1] * 8 + [0, 1, 1], self.cpb
                self.queue.pop(0)
            return super().step(levels)
    lane2 = load("uart_rx")
    bad = BadStop("RX", cpb)
    bad.send([0xFF])
    simulate(lane2, [bad], cycles=cpb * 14)
    assert lane2.flag == 1 and not lane2.rxf


def test_spi_mode0_full_duplex():
    lane = load("spi_mode0")
    tgt = SpiTarget(sck="SCK", mosi="MOSI", miso="MISO", cs="CS", mode=0, reply=[0xA5, 0x3C])
    lane.push_tx(0x81)
    lane.push_tx(0x7E)
    simulate(lane, [tgt], cycles=4000)
    assert [f[0] for f in tgt.frames] == [[0x81], [0x7E]]
    assert list(lane.rxf) == [0xA5, 0x3C]


def run_i2c(addr_on_bus, stretch=0):
    lane = load("i2c_write")
    tgt = I2cTarget(scl="SCL", sda="SDA", address=addr_on_bus, stretch_cycles=stretch)
    for b in (0x50 << 1, 0x12, 0x34):
        lane.push_tx(b)
    trace = []
    simulate(lane, [tgt], cycles=60000, trace=trace)
    return lane, tgt, trace


def sda_moves_while_scl_high(trace):
    n = 0
    for a, b in zip(trace, trace[1:]):
        if a["SCL"] == 1 and b["SCL"] == 1 and a["SDA"] != b["SDA"]:
            n += 1
    return n


@pytest.mark.parametrize("stretch", [0, 3000])
def test_i2c_write_with_ack(stretch):
    lane, tgt, trace = run_i2c(0x50, stretch)
    assert tgt.transactions == [{"addr": 0x50, "rw": 0, "data": [0x12, 0x34], "acked": True}]
    assert lane.flag == 0
    # protocol rule: SDA only changes while SCL is low, except START and STOP
    assert sda_moves_while_scl_high(trace) == 2


def test_i2c_nack_sets_flag_and_stops():
    lane, tgt, trace = run_i2c(0x51)
    assert len(tgt.transactions) == 1 and tgt.transactions[0]["acked"] is False
    assert lane.flag == 1 and len(lane.txf) == 2       # waits for the host to flush
    assert trace[-1]["SCL"] == 1 and trace[-1]["SDA"] == 1     # bus released after STOP


def test_i2c_meets_standard_mode_timing():
    from tbkit.i2c_timing import measure, violations
    lane = load("i2c_write")
    tgt = I2cTarget(scl="SCL", sda="SDA", address=0x50)
    for b in (0x50 << 1, 0x12):
        lane.push_tx(b)
    trace = []
    simulate(lane, [tgt], cycles=40000, trace=trace)
    for b in (0x50 << 1, 0x34):                      # a second transaction gives t_buf
        lane.push_tx(b)
    simulate(lane, [tgt], cycles=40000, trace=trace)
    print(measure(trace, 50e6))
    assert violations(trace, 50e6) == {}


@pytest.mark.parametrize("mode, prog, invert", [
    (0, "spi_mode0", False), (1, "spi_mode1", False),
    (2, "spi_mode0", True), (3, "spi_mode1", True),
])
def test_spi_all_modes(mode, prog, invert):
    over = {".pin    p0 = SCK": ".pin    p0 = SCK invert"} if invert else {}
    lane = load(prog, **over)
    tgt = SpiTarget(sck="SCK", mosi="MOSI", miso="MISO", cs="CS", mode=mode, reply=[0x96, 0x0F])
    lane.push_tx(0xC5)
    lane.push_tx(0x3A)
    trace = []
    simulate(lane, [tgt], cycles=4000, trace=trace)
    assert [f[0] for f in tgt.frames] == [[0xC5], [0x3A]]
    assert list(lane.rxf) == [0x96, 0x0F]
    cpol = mode >> 1
    idle_sck = [t["SCK"] for t in trace[-50:]]
    assert set(idle_sck) == {cpol}, "SCK must idle at CPOL"
