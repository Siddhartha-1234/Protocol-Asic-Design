import pytest

import asm
import rulefmt as rf

UART_TX = open(__file__.replace("tests_py/test_asm.py", "programs/uart_tx.rules")).read()


def test_first_uart_rule_matches_hand_encoding():
    prog, _ = asm.assemble(UART_TX)
    # !TXF_EMPTY | ALWAYS | LOW(p0) | LOAD_TX | TIMER_A | COUNT_LOAD | - | BIT
    #  100100    | 100000 | 001000  |   11    |   01    |    01      |000| 00001
    assert prog["words"][0] == 0x92023501


def test_unused_slots_are_zero_and_zero_never_fires():
    prog, _ = asm.assemble(UART_TX)
    assert prog["words"][2] == 0 and prog["words"][3] == 0
    assert rf.unpack(0)["guard_a"] == rf.SOURCES["FALSE"]


def test_timer_reload_is_period_minus_one():
    prog, _ = asm.assemble(UART_TX)
    assert prog["config"]["timer_a"] == round(50e6 / 115200) - 1


@pytest.mark.parametrize("bad, msg", [
    ("state A\n  ALWAYS : LOW(p0), HIGH(p1)\n", "one pin action"),
    ("state A\n" + "  ALWAYS : -> A\n" * 5, "more than 4 rules"),
    ("state A\n  ALWAYS : -> NOWHERE\n", "unknown state"),
    ("state A\n  T0 & C0 & FLAG : -> A\n", "at most two guards"),
    ("state A\n  BANANA : -> A\n", "unknown guard"),
])
def test_errors_are_reported(bad, msg):
    with pytest.raises(asm.AsmError, match=msg):
        asm.assemble(bad)
