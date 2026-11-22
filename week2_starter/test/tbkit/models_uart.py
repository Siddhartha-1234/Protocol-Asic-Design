"""UART reference model plus cycle-stepped line driver and line monitor."""


def uart_frame(byte, data_bits=8, parity=None, stop_bits=1):
    """Line levels for one frame, one entry per bit time (reference model)."""
    bits = [0] + [(byte >> i) & 1 for i in range(data_bits)]
    if parity == "even":
        bits.append(sum(bits[1:]) & 1)
    elif parity == "odd":
        bits.append(1 - (sum(bits[1:]) & 1))
    return bits + [1] * stop_bits


class UartMonitor:
    """Watches a TX line (driven by the chip) and decodes bytes."""

    def __init__(self, pin, cycles_per_bit, data_bits=8):
        self.pin, self.cpb, self.nbits = pin, cycles_per_bit, data_bits
        self.received, self.errors = [], []
        self._cnt, self._state, self._bit, self._sr = 0, "idle", 0, 0
        self.start_cycles = []        # cycle at which each start bit began
        self._cycle = 0

    def step(self, levels):
        v = levels[self.pin]
        self._cycle += 1
        if self._state == "idle":
            if v == 0:
                self._state, self._cnt = "start", self.cpb // 2
                self.start_cycles.append(self._cycle)
        else:
            self._cnt -= 1
            if self._cnt == 0:
                if self._state == "start":
                    if v != 0:
                        self.errors.append(("glitch", self._cycle))
                        self._state = "idle"
                        return {}
                    self._state, self._bit, self._sr = "data", 0, 0
                elif self._state == "data":
                    self._sr |= v << self._bit
                    self._bit += 1
                    if self._bit == self.nbits:
                        self._state = "stop"
                elif self._state == "stop":
                    if v != 1:
                        self.errors.append(("framing", self._cycle))
                    else:
                        self.received.append(self._sr)
                    self._state = "idle"
                    return {}
                self._cnt = self.cpb
        return {}


class UartDriver:
    """Drives an RX line (into the chip) with queued bytes."""

    def __init__(self, pin, cycles_per_bit, gap_bits=0):
        self.pin, self.cpb, self.gap = pin, cycles_per_bit, gap_bits
        self.queue, self._bits, self._cnt = [], [], 0

    def send(self, data):
        self.queue.extend(data)

    @property
    def idle(self):
        return not self.queue and not self._bits

    def step(self, levels):
        if not self._bits and self.queue:
            self._bits = uart_frame(self.queue.pop(0)) + [1] * self.gap
            self._cnt = self.cpb
        level = self._bits[0] if self._bits else 1
        if self._bits:
            self._cnt -= 1
            if self._cnt == 0:
                self._bits.pop(0)
                self._cnt = self.cpb
        return {self.pin: str(level)}
