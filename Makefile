# Makefile for FT_PAD_ASSIGN (Cross-Platform Standalone)

# --- Configuration ---
CXX = g++
CXXFLAGS = -std=c++11 -Wall -O2
CPP_SRC = bin/ft_pad_assign.cpp
CPP_BIN = bin/ft_pad_assign_cpp
PY_BIN  = bin/ft_pad_assign.py
PL_BIN  = bin/ft_pad_assign.pl

EXAMPLES = $(wildcard examples/*.csv)
V_FILES = $(wildcard examples/*.v)

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
		case "$$list" in *JD1750_PSRAM*|*DIE3_example*) continue ;; esac ; \
		python3 $(PY_BIN) -list $$list -v $(V_FILES) -all -o test_out ; \
	done
	@echo "Python tests complete."
run:
	python3 $(PY_BIN) -list examples/qfn40.8803.0505_v3_pg.pin_list.csv  -v examples/va8803.vg -all -o test_out --die2 examples/JD1750_PSRAM.csv --die2-flip-x ; \

# 2b. Test DIE2 Overlay (all examples + DIE2 on 8803 examples)
test_die2:
	@echo "--- Testing DIE2 Overlay ---"
	@for list in $(EXAMPLES); do \
		case "$$list" in *JD1750_PSRAM*|*DIE3_example*) continue ;; esac ; \
		echo "=== $$list ===" ; \
		python3 $(PY_BIN) -list $$list --die2 examples/JD1750_PSRAM.csv -all -o test_out ; \
	done
	@echo "DIE2 overlay tests complete."
test_die2_flip_x:
	@echo "--- Testing DIE2 Overlay (deprecated --die2-flip-x) ---"
	@for list in $(EXAMPLES); do \
		case "$$list" in *JD1750_PSRAM*|*DIE3_example*) continue ;; esac ; \
		echo "=== $$list ===" ; \
		python3 $(PY_BIN) -list $$list --die2 examples/JD1750_PSRAM.csv --die2-flip-x -all -o test_out ; \
	done
	@echo "DIE2 overlay tests complete."

# 2c. Test DIE3 Overlay
test_die3:
	@echo "--- Testing DIE3 Overlay ---"
	@for list in $(EXAMPLES); do \
		case "$$list" in *JD1750_PSRAM*|*DIE3_example*) continue ;; esac ; \
		echo "=== $$list ===" ; \
		python3 $(PY_BIN) -list $$list --die2 examples/JD1750_PSRAM.csv --die3 examples/DIE3_example.csv -all -o test_out ; \
	done
	@echo "DIE3 overlay tests complete."

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
#---sync: test_py
#---	@echo "--- Tests passed. Syncing to GitHub ---"
#---	git add .
#---	@git commit -m "Auto-sync: $$(date +'%Y-%m-%d %H:%M:%S') - update scripts and design" || echo "No changes to commit"
#---	git push origin main
#---	@echo "--- GitHub synchronization complete ---"

# --- Utility Targets ---
clean:
	@echo "Cleaning up generated files and binaries..."
	@rm -f $(CPP_BIN)
	@rm -rf test_out
	@echo "Clean completed."

help:
	@echo "FT_PAD_ASSIGN Makefile Help"
	@echo "-------------------------"
	@echo "make build     : Compile C++ version to $(CPP_BIN)"
	@echo "make test_py   : Run tests using Python script"
	@echo "make test_die2 : Run tests with DIE2 overlay (PSRAM)"
	@echo "make test_die3 : Run tests with DIE2+DIE3 overlay"
	@echo "make test_pl   : Run tests using Perl script"
	@echo "make test_cpp  : Compile and run tests using C++ binary"
	@echo "make test_all  : Run tests for all 3 languages (Py/Pl/Cpp)"
	@echo "make clean     : Remove all binaries and generated files"

.PHONY: all build test_py test_die2 test_die2_flip_x test_die3 test_pl test_cpp test_all clean help
