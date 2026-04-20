# Makefile for FPAD_ASSIGN (Cross-Platform Standalone)

# --- Configuration ---
CXX = g++
CXXFLAGS = -std=c++11 -Wall -O2
CPP_SRC = bin/fpad_assign.cpp
CPP_BIN = bin/fpad_assign_cpp
PY_BIN  = bin/fpad_assign.py
PL_BIN  = bin/fpad_assign.pl

EXAMPLES = examples/example.pin_list examples/qfn64.pin_list
V_FILES = examples/*.v

# --- Main Targets ---
all: build

# 1. Build C++ Standalone
build: $(CPP_SRC)
	@echo "--- Compiling C++ Standalone ---"
	$(CXX) $(CXXFLAGS) $(CPP_SRC) -o $(CPP_BIN)
	@echo "Build successful: $(CPP_BIN)"

# 2. Test Python Version
test_py:
	@echo "--- Testing Python Version ---"
	@for list in $(EXAMPLES); do \
		python3 $(PY_BIN) -list $$list -v $(V_FILES) -all; \
	done
	@echo "Python tests complete."

# 3. Test Perl Version
test_pl:
	@echo "--- Testing Perl Version ---"
	@for list in $(EXAMPLES); do \
		perl $(PL_BIN) -list $$list -v $(V_FILES) -all; \
	done
	@echo "Perl tests complete."

# 4. Test C++ Version
test_cpp: build
	@echo "--- Testing C++ Version ---"
	@for list in $(EXAMPLES); do \
		./$(CPP_BIN) -list $$list -v $(V_FILES) -all; \
	done
	@echo "C++ tests complete."

# 5. Test All Versions
test_all: test_py test_pl test_cpp
	@echo "--- All platform tests passed successfully! ---"

# 6. Automation Hook: Test and Sync to GitHub
sync: test_py
	@echo "--- Tests passed. Syncing to GitHub ---"
	git add .
	@git commit -m "Auto-sync: $$(date +'%Y-%m-%d %H:%M:%S') - update scripts and design" || echo "No changes to commit"
	git push origin main
	@echo "--- GitHub synchronization complete ---"

# --- Utility Targets ---
clean:
	@echo "Cleaning up generated files and binaries..."
	@rm -f $(CPP_BIN)
	@rm -f examples/*.new examples/*_stagger.rpt examples/*_chip*.const
	@rm -f examples/*_apr.pdf examples/*_pkg.pdf examples/*_combined.pdf
	@echo "Clean completed."

help:
	@echo "FPAD_ASSIGN Makefile Help"
	@echo "-------------------------"
	@echo "make build     : Compile C++ version to $(CPP_BIN)"
	@echo "make test_py   : Run tests using Python script"
	@echo "make test_pl   : Run tests using Perl script"
	@echo "make test_cpp  : Compile and run tests using C++ binary"
	@echo "make test_all  : Run tests for all 3 languages (Py/Pl/Cpp)"
	@echo "make clean     : Remove all binaries and generated files"

.PHONY: all build test_py test_pl test_cpp test_all clean help
