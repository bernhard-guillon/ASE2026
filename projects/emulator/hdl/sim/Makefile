# Verilator Simulation Makefile
# Builds and runs RISC-V emulator HDL model

VERILATOR = verilator
VERILATOR_FLAGS = --cc --exe --build -Wall -Wno-fatal
VERILATOR_FLAGS += --trace  # Enable VCD waveform dump
VERILATOR_FLAGS += -O3      # Optimization level

# Directories
RTL_DIR = ../rtl
TB_DIR = ../tb
BUILD_DIR = obj_dir

# Source files
VERILOG_SRCS = \
    $(RTL_DIR)/emulator_top.v \
    $(RTL_DIR)/cpu.v \
    $(RTL_DIR)/alu.v \
    $(RTL_DIR)/fpu.v \
    $(RTL_DIR)/memory.v

CPP_SRCS = $(TB_DIR)/verilator_runner.cpp

# Top module
TOP_MODULE = emulator_top

# Output binary
TARGET = verilator_runner

.PHONY: all clean run test

all: $(TARGET)

$(TARGET): $(VERILOG_SRCS) $(CPP_SRCS)
	$(VERILATOR) $(VERILATOR_FLAGS) \
		--top-module $(TOP_MODULE) \
		-CFLAGS "-std=c++17" \
		-o $(TARGET) \
		$(VERILOG_SRCS) $(CPP_SRCS)
	cp $(BUILD_DIR)/$(TARGET) .

clean:
	rm -rf $(BUILD_DIR) $(TARGET) *.vcd

# Run a test program
run: $(TARGET)
	./$(TARGET) $(PROG) $(ARGS)

# Run with VCD tracing
trace: $(TARGET)
	./$(TARGET) $(PROG) $(ARGS) +trace
	@echo "Waveform saved to trace.vcd"

# Quick test with hello.s
test-hello: $(TARGET)
	@echo "Testing with hello program..."
	./$(TARGET) ../../build/hello.bin --verbose

# Test neural character generation
test-neural: $(TARGET)
	@echo "Testing neural character generation..."
	./$(TARGET) ../../neural.elf --char A --cycles 1000000 --render-framebuffer

# Lint check only
lint:
	$(VERILATOR) --lint-only -Wall $(VERILOG_SRCS)
