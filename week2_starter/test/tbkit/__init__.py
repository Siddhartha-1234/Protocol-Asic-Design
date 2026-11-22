"""tbkit: reusable test infrastructure for the protocol emulator.

models_*.py  : pure-Python, cycle-stepped protocol models (no cocotb import),
               so pytest can test them without a simulator.
bus.py       : wired-AND bus resolution used by the pure-Python harness.
cocotb_glue.py : connects the same models to the DUT pins in cocotb.
"""
