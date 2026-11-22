#!/usr/bin/env bash
# Week-2 area experiments. Run inside `ttenv`.
# Prints one line per block and saves them to area/results.txt.
set -euo pipefail
cd "$(dirname "$0")"
{
./synth_block.sh blocks/timer16.v    timer16
./synth_block.sh blocks/counter6.v   counter6
./synth_block.sh blocks/shifter32.v  shifter32
./synth_block.sh blocks/fifo.v       fifo
./synth_block.sh blocks/guard_eval.v guard_eval
./synth_block.sh blocks/pin_sync.v   pin_sync N=24
./synth_block.sh blocks/add_cmp.v    add_cmp PIPE=0
./synth_block.sh blocks/add_cmp.v    add_cmp PIPE=1
./synth_block.sh blocks/flop_mem.v   flop_mem ADDR_W=5 DATA_W=16 NREAD=1
./synth_block.sh blocks/flop_mem.v   flop_mem ADDR_W=6 DATA_W=32 NREAD=1
for a in 4 5; do
  for r in 1 2 3 4; do
    ./synth_block.sh blocks/flop_mem.v flop_mem ADDR_W=$a DATA_W=128 NREAD=$r
  done
done
for r in 0 1 2; do
  ./synth_block.sh blocks/flop_mem_rst.v flop_mem_rst RST=$r
done
} 2>&1 | grep -v '^Warning' | tee results.txt
