#!/usr/bin/env python3
"""
Python launcher for FPAD_ASSIGN that delegates to the existing Perl implementation
to ensure feature parity with the .pl version. This enables a unified multi-language
workflow while maintaining a single entry point for bin-based execution.
"""

import argparse
import os
import sys
import subprocess

def main():
    parser = argparse.ArgumentParser(description="FPAD_ASSIGN Python launcher (delegates to the Perl core).")
    parser.add_argument("-list", dest="list_file", help="Pin sequence list file (9-column).")
    parser.add_argument("-v", dest="verilog_files", nargs="*", help="Verilog netlist files.")
    parser.add_argument("-apr", action="store_true", help="Generate APR diagram (delegated to Perl).")
    parser.add_argument("-pkg", action="store_true", help="Generate PKG diagram (delegated to Perl).")
    parser.add_argument("-c", dest="check", action="store_true", help="Generate completed list (delegated to Perl).")
    parser.add_argument("-stagger", action="store_true", help="Run stagger check (delegated to Perl).")
    parser.add_argument("-all", action="store_true", help="Run all functions (delegated to Perl).")
    args = parser.parse_args()

    # Validate input
    if not args.list_file and not args.verilog_files:
        parser.print_help()
        sys.exit(1)

    # Locate the original Perl script
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    perl_script = os.path.join(repo_root, "fpad_assign.opencode", "fpad_assign.pl")
    if not os.path.isfile(perl_script):
        print(f"Perl script not found at {perl_script}")
        sys.exit(2)

    # Build command to delegate to Perl implementation
    cmd = ["perl", perl_script]
    if args.list_file:
        cmd.extend(["-list", args.list_file])
    if args.verilog_files:
        # Pass all verilog files as separate -v arguments
        for vf in args.verilog_files:
            cmd.extend(["-v", vf])
    if args.all:
        cmd.append("-all")
    else:
        if args.apr:
            cmd.append("-apr")
        if args.pkg:
            cmd.append("-pkg")
        if args.check:
            cmd.append("-c")
        if args.stagger:
            cmd.append("-stagger")

    print("Executing:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
