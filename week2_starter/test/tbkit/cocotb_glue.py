"""Connects tbkit's pure-Python protocol models to the Tiny Tapeout pins.

A test names nets ("TX", "SDA", ...) and says which pin each net is on:
    PINMAP = {"TX": ("uo", 0), "SEND": ("uio", 0), "SDA": ("uio", 4)}
Models only ever see net names, so moving a protocol to other pins is a
one-line change in the test, and the same model works for every program.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge


def _bit(handle_value, i):
    s = str(handle_value)            # MSB first, e.g. "10z1x000"
    c = s[len(s) - 1 - i].lower()
    if c in "01":
        return int(c)
    raise ValueError(f"pin bit {i} is '{c}' (X or Z): undriven or contended")


class TTHarness:
    def __init__(self, dut, pinmap, clk_hz=50_000_000, pullups=()):
        self.dut, self.pinmap, self.clk_hz = dut, dict(pinmap), clk_hz
        self._ui = 0
        self._ext_oe = self._ext_out = self._ext_low = 0
        self._pullup = 0
        for net in pullups:
            kind, i = self.pinmap[net]
            assert kind == "uio", "pull-ups only make sense on bidirectional pins"
            self._pullup |= 1 << i
        self._models = []

    # ---- setup ------------------------------------------------------------
    async def start(self, reset_cycles=10):
        period_ns = round(1e9 / self.clk_hz, 3)
        cocotb.start_soon(Clock(self.dut.clk, period_ns, unit="ns").start())
        self.dut.ena.value = 1
        self.dut.rst_n.value = 0
        self._apply()
        await ClockCycles(self.dut.clk, reset_cycles)
        self.dut.rst_n.value = 1
        cocotb.start_soon(self._run_models())

    def _apply(self):
        self.dut.ui_in.value = self._ui
        self.dut.ext_oe.value = self._ext_oe
        self.dut.ext_out.value = self._ext_out
        self.dut.ext_pull_low.value = self._ext_low
        self.dut.pull_up.value = self._pullup

    # ---- pin access by net name ------------------------------------------
    def read(self, net):
        kind, i = self.pinmap[net]
        if kind == "ui":
            return (self._ui >> i) & 1
        if kind == "uo":
            return _bit(self.dut.uo_out.value, i)
        return _bit(self.dut.uio_bus.value, i)

    def drive(self, net, level):
        """level: '0', '1' or 'Z' (release). On ui pins 'Z' is not allowed."""
        kind, i = self.pinmap[net]
        m = 1 << i
        if kind == "ui":
            if level == "Z":
                raise ValueError(f"{net}: dedicated inputs cannot float")
            self._ui = (self._ui | m) if level == "1" else (self._ui & ~m)
        elif kind == "uio":
            self._ext_oe &= ~m
            self._ext_low &= ~m
            if level == "0":
                self._ext_low |= m               # open-drain style low
            elif level == "1":
                self._ext_oe |= m
                self._ext_out |= m               # push-pull high
        else:
            raise ValueError(f"{net} is a chip output; the test cannot drive it")
        self._apply()

    def set_ui(self, value):
        self._ui = value & 0xFF
        self._apply()

    # ---- models -------------------------------------------------------------
    def attach(self, model):
        """Step a tbkit model once per clock, on the falling edge."""
        self._models.append(model)
        return model

    async def _run_models(self):
        while True:
            await FallingEdge(self.dut.clk)
            if int(self.dut.contention.value):
                raise AssertionError("bus contention on a bidirectional pin")
            if not self._models:
                continue
            levels = {}
            for net in self.pinmap:
                try:
                    levels[net] = self.read(net)
                except ValueError:
                    levels[net] = None              # floating: models must not use it
            for m in self._models:
                for net, lvl in m.step(levels).items():
                    self.drive(net, lvl)

    async def cycles(self, n):
        await ClockCycles(self.dut.clk, n)
