#!/usr/bin/env python3
"""Assembler skeleton for rule format v0.

Usage:  python tools/asm.py programs/uart_tx.rules -o build/uart_tx
Writes  build/uart_tx.json (config + rule words), build/uart_tx.hex
        ($readmemh image, 128 words) and build/uart_tx.lst (listing).

Source syntax (one rule per line, inside a state):
    state NAME
        GUARD [& GUARD]  :  ACTION, ACTION, ...  [-> NEXT]
GUARD   = ALWAYS | T0 | C0 | FLAG | TXF_EMPTY | RXF_FULL | OUT_BIT | LAST_BIT
          | pN | rise(pN) | fall(pN)      with an optional leading '!'
ACTION  = LOW(pN) HIGH(pN) RELEASE(pN) OUT(pN) OD(pN)        (at most one)
          SHIFT_IN SHIFT_OUT LOAD_TX | TIMER_A TIMER_B TIMER_UP
          COUNT_LOAD COUNT_DEC | PUSH_RX SET_FLAG CLR_FLAG CRC_STEP
Directives:
    .clock HZ                    core clock, used by bit()/half()/quarter()
    .timer A|B = EXPR            EXPR: number, bit(BAUD), half(HZ), quarter(HZ)
    .count N                     value loaded by COUNT_LOAD
    .shift width=N msb_first=0|1 in=pN
    .pin pN = NAME [invert]
Comments start with ';'. NEXT defaults to the current state.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rulefmt as rf  # noqa: E402


class AsmError(Exception):
    pass


def _cycles(expr, clock):
    m = re.fullmatch(r"(bit|half|quarter)\(\s*([0-9.eE+]+)\s*\)", expr)
    if m:
        if clock is None:
            raise AsmError(f"{expr} needs a .clock directive first")
        div = {"bit": 1, "half": 2, "quarter": 4}[m.group(1)]
        # A timer loaded with N reaches zero N cycles later, and the rule that
        # sees T0 acts on the next edge, so one period = N + 1 cycles.
        return round(clock / (float(m.group(2)) * div)) - 1
    return int(expr, 0)


def parse_guard(tok):
    tok = tok.strip()
    inv = tok.startswith("!")
    name = tok[1:].strip() if inv else tok
    if name == "ALWAYS":
        name, inv = "FALSE", not inv
    if name not in rf.SOURCES:
        raise AsmError(f"unknown guard '{tok}'")
    return (int(inv) << 5) | rf.SOURCES[name]


def parse_actions(text):
    f = {"pin": 0, "shift": 0, "timer": 0, "count": 0, "fifo": 0}
    for tok in [t.strip() for t in text.split(",") if t.strip()]:
        m = re.fullmatch(r"(LOW|HIGH|RELEASE|OUT|OD)\(p([0-3])\)", tok)
        if m:
            if f["pin"]:
                raise AsmError("only one pin action per rule in format v0")
            f["pin"] = (rf.PIN_OPS[m.group(1)] << 3) | (int(m.group(2)) << 1)
            continue
        for field, table in (("shift", rf.SHIFT_OPS), ("timer", rf.TIMER_OPS),
                             ("count", rf.COUNT_OPS), ("fifo", rf.FIFO_OPS)):
            if tok in table:
                if f[field]:
                    raise AsmError(f"two {field} actions in one rule ({tok})")
                f[field] = table[tok]
                break
        else:
            raise AsmError(f"unknown action '{tok}'")
    return f


def assemble(src):
    cfg = {"clock": None, "timer_a": 0, "timer_b": 0, "count": 0,
           "width": 8, "msb_first": 0, "in_pin": 0, "pins": {}, "invert": []}
    states, order, cur = {}, [], None
    for lineno, raw in enumerate(src.splitlines(), 1):
        line = raw.split(";")[0].strip()
        if not line:
            continue
        try:
            if line.startswith(".clock"):
                cfg["clock"] = float(line.split()[1])
            elif line.startswith(".timer"):
                m = re.fullmatch(r"\.timer\s+([AB])\s*=\s*(.+)", line)
                cfg["timer_" + m.group(1).lower()] = _cycles(m.group(2).strip(), cfg["clock"])
            elif line.startswith(".count"):
                cfg["count"] = int(line.split()[1], 0)
            elif line.startswith(".shift"):
                for kv in line.split()[1:]:
                    k, v = kv.split("=")
                    if k == "in":
                        cfg["in_pin"] = int(v.lstrip("p"))
                    else:
                        cfg[k] = int(v)
            elif line.startswith(".pin"):
                m = re.fullmatch(r"\.pin\s+p([0-3])\s*=\s*(\w+)(\s+invert)?", line)
                cfg["pins"][f"p{m.group(1)}"] = m.group(2)
                if m.group(3):
                    cfg["invert"].append(int(m.group(1)))
            elif line.startswith("state"):
                cur = line.split()[1]
                if cur in states:
                    raise AsmError(f"state {cur} defined twice")
                states[cur], order = [], order + [cur]
            else:
                if cur is None:
                    raise AsmError("rule outside a state")
                m = re.fullmatch(r"(.+?):(.*?)(?:->\s*(\w+))?", line)
                if not m:
                    raise AsmError("expected 'GUARDS : ACTIONS [-> NEXT]'")
                guards = [g for g in m.group(1).split("&")]
                if len(guards) > 2:
                    raise AsmError("at most two guards per rule")
                if len(guards) == 1:
                    guards.append("ALWAYS")
                states[cur].append({
                    "guard_a": parse_guard(guards[0]), "guard_b": parse_guard(guards[1]),
                    **parse_actions(m.group(2)), "next_name": m.group(3) or cur,
                    "line": lineno, "text": raw.strip()})
                if len(states[cur]) > rf.RULES_PER_BLOCK:
                    raise AsmError(f"state {cur} has more than {rf.RULES_PER_BLOCK} rules")
        except AsmError as e:
            raise AsmError(f"line {lineno}: {e}") from None
        except (AttributeError, ValueError, IndexError):
            raise AsmError(f"line {lineno}: cannot parse '{raw.strip()}'") from None
    if len(order) > rf.NUM_BLOCKS:
        raise AsmError(f"{len(order)} states, only {rf.NUM_BLOCKS} blocks")
    addr = {name: i for i, name in enumerate(order)}   # first state = block 0 = reset state
    words, listing = [0] * (rf.NUM_BLOCKS * rf.RULES_PER_BLOCK), []
    for name in order:
        for slot, r in enumerate(states[name]):
            if r["next_name"] not in addr:
                raise AsmError(f"line {r['line']}: unknown state '{r['next_name']}'")
            fields = {k: r[k] for k in ("guard_a", "guard_b", "pin", "shift", "timer", "count", "fifo")}
            w = rf.pack(**fields, next=addr[r["next_name"]])
            i = addr[name] * rf.RULES_PER_BLOCK + slot
            words[i] = w
            listing.append(f"{i:3d}  blk {addr[name]:2d}.{slot}  {w:08x}  {r['text']}")
    for k in ("timer_a", "timer_b"):
        if not 0 <= cfg[k] < 1 << 16:
            raise AsmError(f"{k}={cfg[k]} does not fit the 16-bit timer")
    return {"config": cfg, "states": addr, "words": words}, listing


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source")
    ap.add_argument("-o", "--out", help="output path without extension")
    a = ap.parse_args()
    try:
        prog, listing = assemble(Path(a.source).read_text())
    except AsmError as e:
        sys.exit(f"{a.source}: {e}")
    out = Path(a.out or Path("build") / Path(a.source).stem)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(prog, indent=1))
    out.with_suffix(".hex").write_text("".join(f"{w:08x}\n" for w in prog["words"]))
    out.with_suffix(".lst").write_text("\n".join(listing) + "\n")
    used = sum(1 for w in prog["words"] if w)
    print(f"{a.source}: {len(prog['states'])} states, {used} rules -> {out}.json/.hex/.lst")


if __name__ == "__main__":
    main()
