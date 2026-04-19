#!/usr/bin/env python3
"""
FPAD_ASSIGN Python Implementation
A tool for IC I/O assignment, visualization, and validation.
"""

import argparse
import os
import sys

# Add lib to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(repo_root, "lib"))

from fpad_py.logger import Logger
from fpad_py.parser import Parser
from fpad_py.checker import Checker
from fpad_py.writer import Writer
from fpad_py.pdf_gen import PDFGen

def main():
    parser = argparse.ArgumentParser(description="FPAD_ASSIGN Python Core.")
    parser.add_argument("-list", dest="list_file", required=True, help="Pin sequence list file (9-column).")
    parser.add_argument("-v", dest="verilog_files", nargs="*", help="Verilog netlist files.")
    parser.add_argument("-apr", action="store_true", help="Generate APR diagram (PDF).")
    parser.add_argument("-pkg", action="store_true", help="Generate PKG diagram (PDF).")
    parser.add_argument("-c", dest="check", action="store_true", help="Generate completed pin list and Innovus IO constraint.")
    parser.add_argument("-stagger", action="store_true", help="Run stagger density check.")
    parser.add_argument("-all", action="store_true", help="Run all functions.")
    args = parser.parse_args()

    logger = Logger()
    
    if args.all:
        args.apr = args.pkg = args.check = args.stagger = True

    logger.info("Starting FPAD_ASSIGN (Python Implementation)...")

    # 1. Parsing Phase
    fpad_parser = Parser(logger, args.list_file, args.verilog_files)
    fpad_parser.parse_list()
    
    if args.verilog_files:
        fpad_parser.parse_verilog()
        fpad_parser.bridge_data()
    else:
        logger.warn("No Verilog files provided, skipping Verilog parsing and bridging.")

    # 2. Execution Phase
    base_name = os.path.splitext(args.list_file)[0]

    # Checker
    if args.stagger:
        checker = Checker(logger, fpad_parser)
        checker.check_stagger(f"{base_name}_stagger.rpt")

    # Writer
    if args.check:
        writer = Writer(logger, fpad_parser)
        writer.generate_completed_list(f"{base_name}.new")
        writer.generate_innovus_io(f"{base_name}_chip.const")

    # PDF Generation
    if args.apr or args.pkg:
        pdf_gen = PDFGen(logger, fpad_parser)
        if args.apr:
            pdf_gen.generate_apr_pdf(f"{base_name}_apr.pdf")
        if args.pkg:
            pdf_gen.generate_pkg_pdf(f"{base_name}_pkg.pdf")

    logger.info("FPAD_ASSIGN process completed successfully.")

if __name__ == "__main__":
    main()
