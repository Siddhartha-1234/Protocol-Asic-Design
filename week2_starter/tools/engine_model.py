"""Cycle-accurate Python model of ONE lane of the match-action engine.

This is the "golden model": the RTL you write in week 3 must match it cycle
for cycle. Semantics (write these into the spec):
  * Guards are evaluated on values at the START of the cycle.
  * All actions of the winning rule take effect together at the clock edge.
  * Pin inputs pass through SYNC_STAGES flops before guards see them.
  * Timer: TIMER_A/B loads the reload value; otherwise it counts down to 0
    and stops. TIMER_UP clears it and counts up (for measuring).
  * If no rule is true the lane holds its state; the timer keeps running.
"""
from collections import deque

import rulefmt as rf

SYNC_STAGES = 2


class Lane:
    def __init__(self, prog, fifo_depth=4):
        self.cfg = prog["config"]
        self.words = prog["words"]
        self.fifo_depth = fifo_depth
        self.reset()

    def reset(self):
        self.state = 0
        self.timer = 0
        self.counting_up = False
        self.count = 0
        self.sr = 0
        self.flag = 0
        self.last_bit = 0
        self.txf = deque()
        self.rxf = deque()
        self.out = [1, 1, 1, 1]      # value driven when oe = 1
        self.oe = [0, 0, 0, 0]       # 0 = released (input / high-Z)
        self.sync = [[1] * 4 for _ in range(SYNC_STAGES)]
        self.prev = [1, 1, 1, 1]     # previous synchronised level (for edges)
        self.cycle = 0
        self.fired = None            # (state, slot) of the last rule that fired

    # ---- host side -------------------------------------------------------
    def push_tx(self, byte):
        if len(self.txf) >= self.fifo_depth:
            return False
        self.txf.append(byte)
        return True

    def pop_rx(self):
        return self.rxf.popleft() if self.rxf else None

    # ---- helpers -----------------------------------------------------------
    def _mask(self):
        return (1 << self.cfg["width"]) - 1

    def _out_bit(self):
        w = self.cfg["width"]
        return (self.sr >> (w - 1)) & 1 if self.cfg["msb_first"] else self.sr & 1

    def _source(self, idx, level, rise, fall):
        if idx == 0:
            return 0
        if idx == 1:
            return int(self.timer == 0)
        if idx == 2:
            return int(self.count == 0)
        if idx == 3:
            return self.flag
        if idx == 4:
            return int(len(self.txf) == 0)
        if idx == 5:
            return int(len(self.rxf) >= self.fifo_depth)
        if idx == 6:
            return self._out_bit()
        if idx == 7:
            return self.last_bit
        if 8 <= idx < 12:
            return level[idx - 8]
        if 12 <= idx < 16:
            return rise[idx - 12]
        if 16 <= idx < 20:
            return fall[idx - 16]
        raise ValueError(f"reserved guard source {idx}")

    def pins_out(self):
        """Per logical pin: '0', '1' or 'Z' (released), after the invert bits."""
        res = []
        for p in range(4):
            if not self.oe[p]:
                res.append("Z")
            else:
                v = self.out[p] ^ (1 if p in self.cfg["invert"] else 0)
                res.append(str(v))
        return res

    # ---- one clock cycle -----------------------------------------------------
    def step(self, pins_in):
        """pins_in: list of 4 bus levels (0/1) seen at the pads this cycle."""
        pins_in = [v ^ (1 if p in self.cfg["invert"] else 0) for p, v in enumerate(pins_in)]
        level = self.sync[-1]
        rise = [int(l and not pv) for l, pv in zip(level, self.prev)]
        fall = [int(pv and not l) for l, pv in zip(level, self.prev)]

        winner = None
        base = self.state * rf.RULES_PER_BLOCK
        for slot in range(rf.RULES_PER_BLOCK):
            r = rf.unpack(self.words[base + slot])
            ga = self._source(r["guard_a"] & 31, level, rise, fall) ^ (r["guard_a"] >> 5)
            gb = self._source(r["guard_b"] & 31, level, rise, fall) ^ (r["guard_b"] >> 5)
            if ga and gb:
                winner = (slot, r)
                break

        # next-state values, all computed from current-cycle values
        n_timer = self.timer + 1 if self.counting_up else max(self.timer - 1, 0)
        n_up, n_count, n_sr, n_flag = self.counting_up, self.count, self.sr, self.flag
        n_state, n_out, n_oe, n_last = self.state, list(self.out), list(self.oe), self.last_bit
        self.fired = None
        if winner:
            slot, r = winner
            self.fired = (self.state, slot)
            op, pin = r["pin"] >> 3, (r["pin"] >> 1) & 3
            if op == 1:
                n_out[pin], n_oe[pin] = 0, 1
            elif op == 2:
                n_out[pin], n_oe[pin] = 1, 1
            elif op == 3:
                n_oe[pin] = 0
            elif op == 4:
                n_out[pin], n_oe[pin], n_last = self._out_bit(), 1, self._out_bit()
            elif op == 5:
                b = self._out_bit()
                n_out[pin], n_oe[pin], n_last = 0, int(b == 0), b
            if r["shift"] == 1:
                inb = level[self.cfg["in_pin"]]
                if self.cfg["msb_first"]:
                    n_sr = ((self.sr << 1) | inb) & self._mask()
                else:
                    n_sr = (self.sr >> 1) | (inb << (self.cfg["width"] - 1))
            elif r["shift"] == 2:
                n_sr = ((self.sr << 1) & self._mask()) if self.cfg["msb_first"] else self.sr >> 1
            elif r["shift"] == 3 and self.txf:
                n_sr = self.txf.popleft()
            if r["timer"] == 1:
                n_timer, n_up = self.cfg["timer_a"], False
            elif r["timer"] == 2:
                n_timer, n_up = self.cfg["timer_b"], False
            elif r["timer"] == 3:
                n_timer, n_up = 0, True
            if r["count"] == 1:
                n_count = self.cfg["count"]
            elif r["count"] == 2:
                n_count = max(self.count - 1, 0)
            if r["fifo"] == 1 and len(self.rxf) < self.fifo_depth:
                self.rxf.append(self.sr & self._mask())
            elif r["fifo"] == 2:
                n_flag = 1
            elif r["fifo"] == 3:
                n_flag = 0
            n_state = r["next"]

        # clock edge
        self.prev = level
        self.sync = [pins_in] + self.sync[:-1]
        self.timer, self.counting_up, self.count = n_timer & 0xFFFF, n_up, n_count
        self.sr, self.flag, self.state = n_sr, n_flag, n_state
        self.out, self.oe, self.last_bit = n_out, n_oe, n_last
        self.cycle += 1
        return self.pins_out()
