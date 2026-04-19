# Makefile for FPAD_ASSIGN (C++ Version)

CXX = g++
CXXFLAGS = -std=c++11 -Wall -O2
TARGET = bin/fpad_assign
SRC = bin/fpad_assign.cpp

# Default target
all: $(TARGET)

$(TARGET): $(SRC)
	@echo "Compiling C++ Implementation..."
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)
	@echo "Build successful: $(TARGET)"

# Run tests using examples
test: $(TARGET)
	@echo "Running tests with examples/..."
	./$(TARGET) -list examples/example.pin_list -v examples/example_top.v -all
	./$(TARGET) -list examples/qfn64.pin_list -v examples/qfn64_top.v -all
	@echo "Tests completed. Check examples/ for outputs."

# Clean up binaries and generated test files
clean:
	@echo "Cleaning up..."
	rm -f $(TARGET)
	rm -f examples/*.new examples/*_stagger.rpt examples/*_chip.const examples/*_apr.pdf examples/*_pkg.pdf
	@echo "Cleaned."

.PHONY: all test clean
