#!/usr/bin/env bash
# Usage: ./synth_block.sh "<file.v> [more.v]" <top> [PARAM=value ...]
# Maps one block onto IHP SG13CMOS5L standard cells and prints cells, flops
# and area. Run it inside `ttenv`. Writes out/<tag>.stat and out/<tag>.log.
set -euo pipefail
LIB=${LIB:-$PDK_ROOT/$PDK/libs.ref/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib}
YOSYS=${YOSYS:-yosys}
FILES=$1; TOP=$2; shift 2
CHP=""
for p in "$@"; do CHP+=" -set ${p%%=*} ${p#*=}"; done
TAG=$(echo "$TOP $*" | tr ' =' '_-' | sed 's/_$//')
# Cells the real flow is not allowed to use (from the PDK's synth_exclude.cells)
EXCL="-dont_use sg13cmos5l_lgcp_1 -dont_use sg13cmos5l_sighold -dont_use sg13cmos5l_slgcp_1 -dont_use sg13cmos5l_sdfbbp_1 -dont_use sg13cmos5l_dfrbp_2"
mkdir -p out
$YOSYS -q -l out/$TAG.log -p "
  read_verilog -sv $FILES
  ${CHP:+chparam $CHP $TOP}
  synth -top $TOP -flatten
  dfflibmap -liberty $LIB $EXCL
  abc -liberty $LIB $EXCL
  opt_clean
  tee -o out/$TAG.stat stat -liberty $LIB
" >/dev/null
CELLS=$(grep -E '^ +[0-9]+ +[0-9.E+-]+ +cells$' out/$TAG.stat | awk '{print $1}')
FLOPS=$( (grep -E 'sg13cmos5l_s?df' out/$TAG.stat || true) | awk '{s+=$1} END{print s+0}')
AREA=$(grep -E 'Chip area for module' out/$TAG.stat | grep -oE '[0-9]+\.[0-9]+' | tail -1)
printf "%-42s cells=%-7s flops=%-6s area_um2=%.0f\n" "$TAG" "$CELLS" "$FLOPS" "$AREA"
