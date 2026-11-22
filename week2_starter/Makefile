# Week-2 convenience targets. Run `ttenv` first.
.PHONY: all lint pytest asm test area clean

all: lint pytest asm test

lint:
	verilator --lint-only -Wall -Wno-DECLFILENAME -Isrc src/*.v

pytest:
	python -m pytest -q tests_py

asm:
	@for f in programs/*.rules; do \
	  python tools/asm.py $$f -o build/$$(basename $$f .rules) || exit 1; \
	done

test:
	cd test && $(MAKE) -B && python -m cocotb_tools.check_results results.xml

area:
	./area/run_all.sh

clean:
	rm -rf build area/out test/sim_build test/results.xml test/tb.fst .pytest_cache
