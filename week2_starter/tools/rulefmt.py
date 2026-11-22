"""Rule format v0 for the match-action engine (recommended path, not final).

One rule = 32 bits, MSB first:
  [31:26] guard A   = {invert, source[4:0]}
  [25:20] guard B   = {invert, source[4:0]}
  [19:14] pin action = {op[2:0], pin[1:0], 0}
  [13:12] shift action
  [11:10] timer action
  [9:8]   counter action
  [7:5]   fifo / flag action
  [4:0]   next state (block address)
A rule fires when guard A AND guard B are true. Each state owns a block of
4 rules; the first true rule (lowest slot) wins. All-zero word = never fires.
"""

RULES_PER_BLOCK = 4
NUM_BLOCKS = 32

# Guard sources (5 bits). Source 0 is FALSE, so ALWAYS = !FALSE and an
# all-zero (erased) rule can never fire.
SOURCES = {
    "FALSE": 0, "T0": 1, "C0": 2, "FLAG": 3, "TXF_EMPTY": 4, "RXF_FULL": 5,
    "OUT_BIT": 6, "LAST_BIT": 7,
}
for _p in range(4):
    SOURCES[f"p{_p}"] = 8 + _p          # synchronised pin level
    SOURCES[f"rise(p{_p})"] = 12 + _p   # rising edge seen this cycle
    SOURCES[f"fall(p{_p})"] = 16 + _p   # falling edge seen this cycle

PIN_OPS = {"NONE": 0, "LOW": 1, "HIGH": 2, "RELEASE": 3, "OUT": 4, "OD": 5}
SHIFT_OPS = {"NONE": 0, "SHIFT_IN": 1, "SHIFT_OUT": 2, "LOAD_TX": 3}
TIMER_OPS = {"NONE": 0, "TIMER_A": 1, "TIMER_B": 2, "TIMER_UP": 3}
COUNT_OPS = {"NONE": 0, "COUNT_LOAD": 1, "COUNT_DEC": 2}
FIFO_OPS = {"NONE": 0, "PUSH_RX": 1, "SET_FLAG": 2, "CLR_FLAG": 3, "CRC_STEP": 4}

FIELDS = [  # name, msb, lsb
    ("guard_a", 31, 26), ("guard_b", 25, 20), ("pin", 19, 14),
    ("shift", 13, 12), ("timer", 11, 10), ("count", 9, 8),
    ("fifo", 7, 5), ("next", 4, 0),
]


def pack(**f):
    word = 0
    for name, msb, lsb in FIELDS:
        v = f.get(name, 0)
        width = msb - lsb + 1
        if not 0 <= v < (1 << width):
            raise ValueError(f"field {name}={v} does not fit in {width} bits")
        word |= v << lsb
    return word


def unpack(word):
    return {name: (word >> lsb) & ((1 << (msb - lsb + 1)) - 1)
            for name, msb, lsb in FIELDS}
