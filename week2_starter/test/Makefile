# Makefile (template version plus a few additions, marked "W2")
SIM ?= icarus
FST ?= -fst
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = project.v

# W2: a small clock divider value keeps RTL tests fast; the design default is 434.
CLKS_PER_BIT ?= 16

ifneq ($(GATES),yes)
SIM_BUILD        = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
COMPILE_ARGS    += -DCLKS_PER_BIT=$(CLKS_PER_BIT)
else
SIM_BUILD        = sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
PDK ?= ihp-sg13cmos5l
PDK_CELL_PREFIX = $(patsubst ihp-%,%,$(PDK))
PDK_LIBS_REF = $(PDK_ROOT)/$(PDK)/libs.ref
VERILOG_SOURCES += $(PDK_LIBS_REF)/$(PDK_CELL_PREFIX)_io/verilog/$(PDK_CELL_PREFIX)_io.v
VERILOG_SOURCES += $(wildcard $(PDK_LIBS_REF)/$(PDK_CELL_PREFIX)_stdcell/verilog/$(PDK_CELL_PREFIX)_udp.v)
VERILOG_SOURCES += $(PDK_LIBS_REF)/$(PDK_CELL_PREFIX)_stdcell/verilog/$(PDK_CELL_PREFIX)_stdcell.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
# W2: the netlist was hardened with the default divider, so tell the tests.
CLKS_PER_BIT = 434
endif

COMPILE_ARGS += -I$(SRC_DIR)
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

# W2: pass the divider to Python, and list every test module here.
export CLKS_PER_BIT
COCOTB_TEST_MODULES = test_uart

include $(shell cocotb-config --makefiles)/Makefile.sim
