#!/usr/bin/env python3
"""
FPAD_ASSIGN - Standalone Version
A tool for IC I/O assignment, visualization, and validation.
Usage: python3 fpad_assign.py -list <pin_list> -v <verilog_files> [options]
"""

import argparse
import csv
import io
import os
import sys
import re

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

import datetime

# --- Logger Class ---
class Logger:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn
        if self.log_fn:
            with open(self.log_fn, 'w') as f:
                f.write(f"--- FPAD_ASSIGN Execution Log ({datetime.datetime.now()}) ---\n")

    def info(self, msg):
        out = f"[INFO ] {msg}"
        print(out)
        if self.log_fn:
            with open(self.log_fn, 'a') as f: f.write(out + "\n")

    def warn(self, msg):
        out = f"[WARN ] {msg}"
        print(out)
        if self.log_fn:
            with open(self.log_fn, 'a') as f: f.write(out + "\n")

    def error(self, msg):
        out = f"[ERROR] {msg}"
        print(out)
        if self.log_fn:
            with open(self.log_fn, 'a') as f: f.write(out + "\n")

    def fatal(self, msg):
        out = f"[FATAL] {msg}"
        print(out)
        if self.log_fn:
            with open(self.log_fn, 'a') as f: f.write(out + "\n")
        sys.exit(1)

# --- Field Alias Mapping (Header-Driven Parsing) ---
FIELD_ALIASES = {
    'PKG_NUM':      ['PKG_NUM', 'PIN_NUM'],
    'PKG_PIN_NAME': ['PKG_PIN_NAME'],
    'DIE_NUM':      ['DIE_NUM', 'DIE_PAD_NUM'],
    'DIE_PIN_NAME': ['DIE_PIN_NAME', 'PIN_NAME'],
    'IO_CELL_NAME': ['IO_CELL_NAME'],
    'PKG_LOC':      ['PKG_LOC', 'LOCATION', 'PIN_LOCA'],
    'DIE_LOC':      ['DIE_LOC', 'DIE_PAD_NUM_LOC', 'DIE_LOCA'],
    'DIRECTION':    ['DIRECTION'],
    'LOAD':         ['LOAD'],
    'SLEW':         ['SLEW'],
    'SSO':          ['SSO'],
}

# --- Parser Class ---
class Parser:
    def __init__(self, logger, list_file, v_files=None):
        self.logger = logger
        self.list_file = list_file
        self.v_files = v_files if v_files else []
        self.header = {}
        self.data = []
        self.v_ports = {}
        self.v_insts = {}
        self.v_net_to_inst = {}
        self.v_raw_insts = {}

    def parse_list(self):
        self.logger.info(f"Reading Pin List: {self.list_file}")
        if not os.path.exists(self.list_file):
            self.logger.fatal(f"File not found: {self.list_file}")

        is_csv = self.list_file.lower().endswith('.csv')
        try:
            with open(self.list_file, 'r', newline='') as f:
                if is_csv:
                    self._parse_csv(f)
                else:
                    self._parse_txt(f)
            self.logger.info(f"Loaded {len(self.data)} entries from pin list.")
            self._reorder_and_reindex_apr_data()
            self._sanity_check_list()
        except Exception as e:
            self.logger.fatal(f"Error parsing list: {e}")

    def _parse_csv(self, f):
        # Read all lines first to handle mixed format (header lines + CSV data)
        lines = f.readlines()

        # Skip header lines (lines containing ':' which are metadata)
        data_start = 0
        header_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            # If line has ':' in first column and doesn't look like CSV data, it's a header
            if ':' in stripped and not stripped.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '(', 'D')):
                # Parse header line (handle CSV format with commas like "PACKAGE,,: value")
                match = re.search(r'^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)[,\s]*:\s*(.*)', stripped, re.I)
                if match:
                    # Remove trailing commas and whitespace
                    value = match.group(2).strip().rstrip(',')
                    self.header[match.group(1).upper()] = value
                data_start = i + 1
            else:
                # Alias-aware header detection: check if any PKG_NUM alias appears in the header
                words = set(w.upper() for w in stripped.split(','))
                if any(a.upper() in words for a in FIELD_ALIASES['PKG_NUM']):
                    # CSV header row
                    self.raw_headers = stripped.split(',')
                    header_idx = i
                    data_start = i + 1
                    break

        # Parse CSV data - include header row for DictReader
        csv_content = ''.join(lines[header_idx:])
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            # Build normalized key map (strip + uppercase all header names)
            norm_row = {k.strip().upper(): (v.strip() if v else '') for k, v in row.items()}

            def get_field(canonical):
                for alias in FIELD_ALIASES[canonical]:
                    val = norm_row.get(alias.upper())
                    if val is not None:
                        return val if val != '' else '-'
                return '-'

            # Skip Inner_bound rows - treat as comment, output as-is
            pkg_num_val = get_field('PKG_NUM')
            if pkg_num_val.upper() == 'INNER_BOUND':
                row_data = {
                    'PKG_NUM':      pkg_num_val,
                    'PKG_PIN_NAME': get_field('PKG_PIN_NAME'),
                    'DIE_NUM':      get_field('DIE_NUM'),
                    'DIE_PIN_NAME': get_field('DIE_PIN_NAME'),
                    'IO_CELL_NAME': get_field('IO_CELL_NAME'),
                    'PKG_LOC':      get_field('PKG_LOC'),
                    'DIE_LOC':      get_field('DIE_LOC'),
                    'DIRECTION':    get_field('DIRECTION'),
                    'LOAD':         get_field('LOAD'),
                    'SLEW':         get_field('SLEW'),
                    'SSO':          get_field('SSO'),
                    'INST_NAME':    '-'
                }
                self.data.append(row_data)
                continue

            row_data = {
                'PKG_NUM':      get_field('PKG_NUM'),
                'PKG_PIN_NAME': get_field('PKG_PIN_NAME'),
                'DIE_NUM':      get_field('DIE_NUM'),
                'DIE_PIN_NAME': get_field('DIE_PIN_NAME'),
                'IO_CELL_NAME': get_field('IO_CELL_NAME'),
                'PKG_LOC':      get_field('PKG_LOC'),
                'DIE_LOC':      get_field('DIE_LOC'),
                'DIRECTION':    get_field('DIRECTION'),
                'LOAD':         get_field('LOAD'),
                'SLEW':         get_field('SLEW'),
                'SSO':          get_field('SSO'),
                'INST_NAME':    '-'
            }
            self.data.append(row_data)

    def _parse_txt(self, f):
        in_table = False
        col_map = {}
        for line in f:
            line = line.strip()
            if not line or re.match(r'^-+$', line): continue
            match = re.search(r'^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)\s*:\s*(.*)', line, re.I)
            if match:
                self.header[match.group(1).upper()] = match.group(2)
                continue
            # Alias-aware header detection: check if any PKG_NUM alias appears in the header
            words = set(line.upper().split())
            if any(a.upper() in words for a in FIELD_ALIASES['PKG_NUM']):
                in_table = True
                self.raw_headers = line.split()
                col_map = {name.upper(): i for i, name in enumerate(self.raw_headers)}
                continue
            if in_table:
                cols = line.split()
                if len(cols) >= 5:
                    def get_txt_field(canonical):
                        for alias in FIELD_ALIASES[canonical]:
                            idx = col_map.get(alias.upper())
                            if idx is not None and idx < len(cols):
                                v = cols[idx]
                                return v if v.strip() else '-'
                        return '-'

                    # Skip Inner_bound rows - treat as comment, output as-is
                    pkg_num_val = get_txt_field('PKG_NUM')
                    if pkg_num_val.upper() == 'INNER_BOUND':
                        row = {
                            'PKG_NUM':      pkg_num_val,
                            'PKG_PIN_NAME': get_txt_field('PKG_PIN_NAME'),
                            'DIE_NUM':      get_txt_field('DIE_NUM'),
                            'DIE_PIN_NAME': get_txt_field('DIE_PIN_NAME'),
                            'IO_CELL_NAME': get_txt_field('IO_CELL_NAME'),
                            'PKG_LOC':      get_txt_field('PKG_LOC'),
                            'DIE_LOC':      get_txt_field('DIE_LOC'),
                            'DIRECTION':    get_txt_field('DIRECTION'),
                            'LOAD':         get_txt_field('LOAD'),
                            'SLEW':         get_txt_field('SLEW'),
                            'SSO':          get_txt_field('SSO'),
                            'INST_NAME':    '-'
                        }
                        self.data.append(row)
                        continue

                    row = {
                        'PKG_NUM':      get_txt_field('PKG_NUM'),
                        'PKG_PIN_NAME': get_txt_field('PKG_PIN_NAME'),
                        'DIE_NUM':      get_txt_field('DIE_NUM'),
                        'DIE_PIN_NAME': get_txt_field('DIE_PIN_NAME'),
                        'IO_CELL_NAME': get_txt_field('IO_CELL_NAME'),
                        'PKG_LOC':      get_txt_field('PKG_LOC'),
                        'DIE_LOC':      get_txt_field('DIE_LOC'),
                        'DIRECTION':    get_txt_field('DIRECTION'),
                        'LOAD':         get_txt_field('LOAD'),
                        'SLEW':         get_txt_field('SLEW'),
                        'SSO':          get_txt_field('SSO'),
                        'INST_NAME':    '-'
                    }
                    self.data.append(row)

    def _reorder_and_reindex_apr_data(self):
        self.logger.info("Re-indexing DIE_NUM with Dynamic D1.xx Reference Update...")
        
        # 1. Capture original mapping and identify D1.xx references
        old_die_num_to_row = {}
        referencing_rows = [] # Rows with PKG_NUM like D1.77

        for row in self.data:
            # Skip special rows - treat as comment, output as-is
            pkg_upper = row['PKG_NUM'].upper()
            if pkg_upper == 'INNER_BOUND' or row['PKG_NUM'] == '-' or row['DIE_NUM'] == '-':
                continue
            d_num = row['DIE_NUM']
            p_num = row['PKG_NUM']
            if d_num not in ('0', '-', ''):
                old_die_num_to_row[d_num] = row

            # Check for D1.xx pattern in PKG_NUM
            match = re.search(r'D1\.(\d+)', p_num.upper())
            if match:
                referencing_rows.append((row, match.group(1))) # (row_object, original_target_xx)

        # 2. Re-indexing logic (First L is 1, keep 0 as 0)
        start_idx = -1
        for i, row in enumerate(self.data):
            # Skip special rows
            if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-' or row['DIE_NUM'] == '-':
                continue
            if row['DIE_LOC'].upper() == 'L' and row['DIE_PIN_NAME'].upper() != 'NC' and row['DIE_NUM'] != '0':
                start_idx = i
                break

        if start_idx != -1:
            ring_seq = self.data[start_idx:] + self.data[:start_idx]
            idx = 1
            orig_to_new = {}  # Map: original DIE_NUM -> new DIE_NUM (for duplicates)
            for row in ring_seq:
                # Skip special rows
                if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-' or row['DIE_NUM'] == '-':
                    continue
                if row['DIE_PIN_NAME'].upper() == 'NC' or row['DIE_NUM'] == '0':
                    row['DIE_NUM'] = '0'
                else:
                    orig_die = row['DIE_NUM']
                    if orig_die in orig_to_new:
                        # Duplicate DIE_NUM: reuse the same new number
                        row['DIE_NUM'] = orig_to_new[orig_die]
                    else:
                        # New DIE_NUM: assign new number
                        row['DIE_NUM'] = str(idx)
                        orig_to_new[orig_die] = str(idx)
                        idx += 1

        # 3. Dynamic Update for D1.xx
        for ref_row, target_xx in referencing_rows:
            if target_xx in old_die_num_to_row:
                target_row_obj = old_die_num_to_row[target_xx]
                new_val = target_row_obj['DIE_NUM']
                # Update PKG_NUM to new reference (preserving parentheses if any)
                orig_pnum = ref_row['PKG_NUM']
                new_pnum = re.sub(r'D1\.\d+', f'D1.{new_val}', orig_pnum, flags=re.I)
                ref_row['PKG_NUM'] = new_pnum
                self.logger.info(f"Updated Dynamic Reference: {orig_pnum} -> {new_pnum} (Target was DIE_NUM {target_xx})")

    def _sanity_check_list(self):
        self.logger.info("Performing Sanity Check on Pin List...")
        # 1. Package Side Count Verification
        pkg_str = self.header.get('PACKAGE', '')
        if not pkg_str:
            self.logger.warn("PACKAGE definition missing in header.")
            return

        parts = pkg_str.split()
        if len(parts) < 5:
            self.logger.error(f"Invalid PACKAGE format: '{pkg_str}'. Expected 'TYPE L B R T'.")
            return

        expected = {'L': int(parts[1]), 'B': int(parts[2]), 'R': int(parts[3]), 'T': int(parts[4])}
        self.logger.info(f"PACKAGE header defines: L={expected['L']}, B={expected['B']}, R={expected['R']}, T={expected['T']}")

        # Helper to infer side from PIN_NUM using cumulative counts
        # e.g., 48QFN 12 12 12 12 -> L:1-12, B:13-24, R:25-36, T:37-48
        def get_side_from_pnum(pnum_str):
            try:
                p = int(pnum_str)
                if p == 0:
                    return None
                cumulative = 0
                for side in ['L', 'B', 'R', 'T']:
                    cumulative += expected[side]
                    if p <= cumulative:
                        return side
                return None
            except (ValueError, TypeError):
                return None

        actual_pnums = {'L': set(), 'B': set(), 'R': set(), 'T': set()}

        for row in self.data:
            loc = row['PKG_LOC'].upper()
            pnum = row['PKG_NUM']
            pname = row['DIE_PIN_NAME'].upper()

            # Count every unique physical pin number (including NC)
            # 1. Ignore '0', '-', or empty which are not physical pin slots
            # 2. Ignore Dummy Pins starting with 'D' or formatted as (D...)
            # 3. EXCEPT: DOWNBOUND should be counted in PKG (DIE_NUM is 0 but PKG has the pin)
            #    Use PIN_NUM to infer side if LOCATION is invalid
            if pname == 'DOWNBOUND':
                side = loc if loc in actual_pnums else get_side_from_pnum(pnum)
                if side:
                    actual_pnums[side].add(pnum)
            elif pnum in ('0', '-', '') or pnum.upper().startswith('D') or '(D' in pnum.upper():
                continue
            elif loc in actual_pnums:
                actual_pnums[loc].add(pnum)

        for side in ('L', 'B', 'R', 'T'):
            # Sort the found pin numbers for cleaner logging
            def pnum_key(x):
                try: return (0, int(x))
                except: return (1, x)
            pnums_found = sorted(list(actual_pnums[side]), key=pnum_key)

            act_cnt = len(pnums_found)
            exp_cnt = expected[side]
            pnums_str = ", ".join(pnums_found)

            if act_cnt != exp_cnt:
                self.logger.error(f"Side {side} check FAILED: Found {act_cnt} unique PKG_NUMs, but PACKAGE expects {exp_cnt}!")
                self.logger.error(f"  - Actual PKG_NUMs on Side {side}: {pnums_str}")
            else:
                self.logger.info(f"Side {side} check passed: {act_cnt} unique PKG_NUMs ({pnums_str})")

        
        # Total count check
        total_exp = sum(expected.values())
        total_act = sum(len(s) for s in actual_pnums.values())
        if total_exp != total_act:
             self.logger.error(f"TOTAL PIN COUNT MISMATCH: PACKAGE expects {total_exp}, List has {total_act} unique pins.")
        else:
             self.logger.info(f"Total pin count check passed: {total_act} pins.")
        
        self.logger.info("Pin list sanity check complete.")

    def parse_verilog(self):
        for v_file in self.v_files:
            if not os.path.exists(v_file):
                self.logger.warn(f"Verilog file not found: {v_file}")
                continue
            self.logger.info(f"Reading Verilog: {v_file}")
            # ... rest of parse_verilog
            try:
                with open(v_file, 'r') as f:
                    content = f.read()
                # Ports
                pm = re.finditer(r'(input|output|inout)\s+(?:\[.*?\]\s+)?(.*?);', content, re.S)
                for m in pm:
                    direction = m.group(1)[0].upper()
                    for p in [x.strip() for x in m.group(2).split(',')]:
                        self.v_ports[p] = direction
                # Instances
                im = re.finditer(r'(\w+)\s+(\w+)\s*\((.*?)\);', content, re.S)
                for m in im:
                    cell, inst, body = m.groups()
                    self.v_raw_insts[inst] = cell
                    pad_m = re.search(r'\.PAD\s*\(\s*(.*?)\s*\)', body, re.S)
                    if pad_m:
                        net = pad_m.group(1).strip()
                        self.v_insts[net] = cell
                        self.v_net_to_inst[net] = inst
            except Exception as e:
                self.logger.warn(f"Error parsing Verilog {v_file}: {e}")

    def bridge_data(self):
        self.logger.info("Bridging data and re-indexing DIE_NUM with Dynamic Reference Update...")
        
        # 1. Capture original mapping and identify D1.xx references
        old_die_num_to_row = {}
        referencing_rows = []
        for row in self.data:
            # Skip special rows - treat as comment, output as-is
            if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-' or row['DIE_NUM'] == '-':
                continue
            d_num = row['DIE_NUM']
            p_num = row['PKG_NUM']
            if d_num not in ('0', '-', ''):
                old_die_num_to_row[d_num] = row
            match = re.search(r'D1\.(\d+)', p_num.upper())
            if match:
                referencing_rows.append((row, match.group(1)))

        # 2. Re-indexing logic
        start_idx = -1
        for i, row in enumerate(self.data):
            # Skip special rows
            if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-' or row['DIE_NUM'] == '-':
                continue
            if row['DIE_LOC'].upper() == 'L' and row['DIE_PIN_NAME'].upper() != 'NC' and row['DIE_NUM'] != '0':
                start_idx = i
                break

        if start_idx != -1:
            ring_seq = self.data[start_idx:] + self.data[:start_idx]
            idx = 1
            orig_to_new = {}  # Map: original DIE_NUM -> new DIE_NUM (for duplicates)
            for row in ring_seq:
                # Skip special rows
                if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-' or row['DIE_NUM'] == '-':
                    continue
                if row['DIE_PIN_NAME'].upper() == 'NC' or row['DIE_NUM'] == '0':
                    row['DIE_NUM'] = '0'
                else:
                    orig_die = row['DIE_NUM']
                    if orig_die in orig_to_new:
                        # Duplicate DIE_NUM: reuse the same new number
                        row['DIE_NUM'] = orig_to_new[orig_die]
                    else:
                        # New DIE_NUM: assign new number
                        row['DIE_NUM'] = str(idx)
                        orig_to_new[orig_die] = str(idx)
                        idx += 1

        # 3. Dynamic Update for D1.xx
        for ref_row, target_xx in referencing_rows:
            if target_xx in old_die_num_to_row:
                target_row_obj = old_die_num_to_row[target_xx]
                new_val = target_row_obj['DIE_NUM']
                orig_pnum = ref_row['PKG_NUM']
                new_pnum = re.sub(r'D1\.\d+', f'D1.{new_val}', orig_pnum, flags=re.I)
                ref_row['PKG_NUM'] = new_pnum
                self.logger.info(f"Updated Dynamic Reference (Bridge): {orig_pnum} -> {new_pnum}")

        # --- Bridging Logic ---
        for row in self.data:
            pname = row['DIE_PIN_NAME']
            pname_upper = pname.upper()
            if pname_upper == 'NC': continue
            
            # Use sn for lookup, handle power/group segments
            sn = pname
            if '%' in pname: sn = pname.split('%')[-1]
            
            p_mode = (row['DIRECTION'] in ('P', 'G') or '%' in pname or 'POWERCUT' in pname_upper)
            
            # Attempt to update IO_CELL_NAME if not already set or is a placeholder
            if row['IO_CELL_NAME'] in ('-', '', 'NOT_FOUND'):
                if p_mode:
                    row['IO_CELL_NAME'] = self.v_raw_insts.get(sn, self.v_insts.get(sn, 'NOT_FOUND'))
                    row['INST_NAME'] = sn
                else:
                    row['IO_CELL_NAME'] = self.v_insts.get(sn, self.v_raw_insts.get(sn, 'NOT_FOUND'))
                    row['INST_NAME'] = self.v_net_to_inst.get(sn, sn)
                    if row['DIRECTION'] in ('-', 'UNKNOWN', ''):
                        row['DIRECTION'] = self.v_ports.get(sn, 'UNKNOWN')

# --- PDF Generator Class ---
class PDFGen:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def generate_combined_pdf(self, filename):
        if not HAS_REPORTLAB:
            self.logger.error("ReportLab is not installed.")
            return
        self.logger.info("Generating Combined (PKG+APR) Diagram with Bonding Wires...")
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)
        cx, cy = width / 2, 240
        self._draw_header(c, "COMBINED BONDING DIAGRAM", width, height)

        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)

        # 1. Group data by side
        pkg_data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        apr_data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        apr_t_early = []
        apr_found_l = False
        seen_pnums = set()
        seen_apr_die_nums = set()  # For APR deduplication: skip duplicate DIE_NUM
        # Collect D1.xx rows for inner bound connections
        d1xx_rows = []

        for row in self.parser.data:
            p_loc = row['PKG_LOC'].upper()
            a_loc = row['DIE_LOC'].upper()
            pnum = row['PKG_NUM']
            pname = row['DIE_PIN_NAME'].upper()

            # PKG side (Uses current PIN_NUM order)
            # DOWNBOUND should be included in PKG (even though DIE_NUM=0)
            if p_loc in pkg_data_by_side:
                if pname != 'DOWNBOUND' and pnum in ('0', '-', 'NC') or 'POWERCUT' in pname: pass
                else:
                    if pnum not in seen_pnums:
                        pkg_data_by_side[p_loc].append(row)
                        seen_pnums.add(pnum)

            # APR side (Needs local reordering for the Ring)
            # Skip NC, DOWNBOUND, and DIE_PAD_NUM='0' or '-' (no die pad)
            # Skip Inner_bound and PKG_NUM='-'
            # Skip duplicate DIE_NUM (only show one APR pin for multiple wires to same point)
            die_num = row['DIE_NUM']
            if pname not in ('NC', 'DOWNBOUND') and die_num not in ('0', '-') and a_loc in apr_data_by_side:
                if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-':
                    pass  # Skip
                elif die_num in seen_apr_die_nums:
                    pass  # Skip duplicate
                else:
                    seen_apr_die_nums.add(die_num)
                    if a_loc == 'L': apr_found_l = True

                    if a_loc == 'T' and not apr_found_l:
                        apr_t_early.append(row)
                    else:
                        apr_data_by_side[a_loc].append(row)

            # Collect D1.xx rows for inner bound connections (both D1.xx and (D1.xx) formats)
            if pnum.startswith('D1.') or pnum.startswith('(D1.'):
                d1xx_rows.append(row)
        
        # Move early APR T pins to the end
        apr_data_by_side['T'].extend(apr_t_early)

        edge_pkg, edge_apr = 350, 200
        c.setLineWidth(2)
        c.rect(cx - edge_pkg/2, cy - edge_pkg/2, edge_pkg, edge_pkg)
        c.rect(cx - edge_apr/2, cy - edge_apr/2, edge_apr, edge_apr)

        pkg_coords, apr_coords = {}, {}
        pkg_edge = {'L': cx - edge_pkg/2, 'R': cx + edge_pkg/2, 'B': cy - edge_pkg/2, 'T': cy + edge_pkg/2}
        for side in ('L', 'B', 'R', 'T'):
            p_coords = self._draw_side_boxes(c, side, pkg_data_by_side[side], cx, cy, edge_pkg, getattr(self, f"_{side}_pos")(cx, cy, edge_pkg), l_cnt if side=='L' else b_cnt if side=='B' else r_cnt if side=='R' else t_cnt, 'PKG', label_inside=False)
            pkg_coords.update(p_coords)
            a_coords = self._draw_side_boxes(c, side, apr_data_by_side[side], cx, cy, edge_apr, getattr(self, f"_{side}_pos")(cx, cy, edge_apr), l_cnt if side=='L' else b_cnt if side=='B' else r_cnt if side=='R' else t_cnt, 'APR', label_inside=False, max_label_extent=pkg_edge[side])
            apr_coords.update(a_coords)

        c.setLineWidth(0.3)
        for row in self.parser.data:
            pname = row['DIE_PIN_NAME'].upper()
            # Skip NC, DOWNBOUND, and DIE_PAD_NUM='0' for bonding wires (no APR pin exists)
            if pname in ('NC', 'DOWNBOUND') or row['DIE_NUM'] in ('0', '-'): continue
            p_pt = pkg_coords.get(row['PKG_NUM'])
            a_pt = apr_coords.get(row['DIE_NUM'])
            if p_pt and a_pt:
                # Determine which side based on PIN_NUM location
                pnum_str = row['PKG_NUM']
                side = None
                try:
                    pnum_int = int(pnum_str)
                    pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
                    pkg_parts = pkg_str.split()
                    expected = {'L': int(pkg_parts[1]), 'B': int(pkg_parts[2]), 'R': int(pkg_parts[3]), 'T': int(pkg_parts[4])}
                    cumulative = 0
                    for s in ['L', 'B', 'R', 'T']:
                        cumulative += expected[s]
                        if pnum_int <= cumulative:
                            side = s
                            break
                except:
                    pass

                # Calculate wire start (PKG pin) and end (APR pin)
                if side == 'L':
                    wire_start = (p_pt['pt'][0], p_pt['pt'][1])
                    wire_end = (a_pt['pt'][0], a_pt['pt'][1])
                elif side == 'R':
                    wire_start = (p_pt['pt'][0], p_pt['pt'][1])
                    wire_end = (a_pt['pt'][0], a_pt['pt'][1])
                elif side == 'B':
                    wire_start = (p_pt['pt'][0], p_pt['pt'][1])
                    wire_end = (a_pt['pt'][0], a_pt['pt'][1])
                elif side == 'T':
                    wire_start = (p_pt['pt'][0], p_pt['pt'][1])
                    wire_end = (a_pt['pt'][0], a_pt['pt'][1])
                else:
                    wire_start, wire_end = p_pt['pt'], a_pt['pt']

                dir_color = colors.grey
                if row['DIRECTION'] == 'P': dir_color = colors.red
                elif row['DIRECTION'] == 'G': dir_color = colors.blue
                c.setStrokeColor(dir_color); c.line(wire_start[0], wire_start[1], wire_end[0], wire_end[1])

        # Draw inner bound red lines for D1.xx connections
        # Rule: PKG_NUM=D1.xx + DIE_NUM=yy means xx -> yy (regardless of parentheses)
        # Symmetric pair: D1.90+DIE_NUM=1 AND D1.1+DIE_NUM=90 means 90<->1 connected both ways
        # Asymmetric: only one direction exists = ERROR + dashed line
        if d1xx_rows:
            # First pass: build (source, dest) pairs
            # D1.xx + DIE_NUM=yy -> source=xx, dest=yy
            direction_map = {}  # (source, dest) -> list of rows
            for row in d1xx_rows:
                pnum = row['PKG_NUM']
                die_yy = row['DIE_NUM']
                if not die_yy or die_yy in ('0', '-'):
                    continue
                # Remove parentheses if present, extract xx
                pnum_clean = pnum.lstrip('(').rstrip(')')
                xx = pnum_clean.split('.')[1].rstrip(')')
                # D1.xx, DIE_NUM=yy means xx -> yy (both with and without parentheses)
                source, dest = xx, die_yy
                key = (source, dest)
                if key not in direction_map:
                    direction_map[key] = []
                direction_map[key].append(row)

            # Check for asymmetric connections
            asymmetric_pairs = []
            for (a, b), rows in direction_map.items():
                reverse_key = (b, a)
                if reverse_key not in direction_map:
                    # Asymmetric: a->b exists but b->a missing
                    asymmetric_pairs.append((a, b))
                    self.logger.error(f"Inner Bound ASYMMETRIC: {a}->{b} exists but {b}->{a} missing!")

            drawn_extended_pins = set()

            for (source, dest), rows in direction_map.items():
                pin_src = apr_coords.get(source)
                pin_dst = apr_coords.get(dest)
                if not pin_src or not pin_dst:
                    continue

                pt_src = pin_src['pt']
                pt_dst = pin_dst['pt']
                bw_src = pin_src['bw']
                bh_src = pin_src['bh']
                bw_dst = pin_dst['bw']
                bh_dst = pin_dst['bh']
                side_src = pin_src['side']
                side_dst = pin_dst['side']

                dir_src = dir_dst = None
                for r in self.parser.data:
                    if r['DIE_NUM'] == source:
                        dir_src = r['DIRECTION']
                    if r['DIE_NUM'] == dest:
                        dir_dst = r['DIRECTION']

                def get_pin_color(direction):
                    if direction == 'P': return colors.red
                    elif direction == 'G': return colors.blue
                    return colors.black

                color_src = get_pin_color(dir_src) if dir_src else colors.black
                color_dst = get_pin_color(dir_dst) if dir_dst else colors.black

                ext_src = self._extend_point_toward_center(pt_src, side_src, bh_src, cx, cy)
                ext_dst = self._extend_point_toward_center(pt_dst, side_dst, bh_dst, cx, cy)

                # Draw extended pin shapes only once per unique pin
                if (source, side_src) not in drawn_extended_pins:
                    c.setStrokeColor(colors.red); c.setLineWidth(0.5)
                    self._draw_extended_pin(c, pt_src, side_src, bw_src, bh_src, color_src)
                    drawn_extended_pins.add((source, side_src))
                if (dest, side_dst) not in drawn_extended_pins:
                    c.setStrokeColor(colors.red); c.setLineWidth(0.5)
                    self._draw_extended_pin(c, pt_dst, side_dst, bw_dst, bh_dst, color_dst)
                    drawn_extended_pins.add((dest, side_dst))

                # Determine if symmetric or asymmetric
                reverse_key = (dest, source)
                is_symmetric = reverse_key in direction_map
                count = len(rows)

                # Draw count offset wires
                for i in range(count):
                    offset = (i - (count - 1) / 2) * 2

                    # Apply offset based on side
                    if side_src in ('L', 'R'):
                        # Y axis offset (spread vertically)
                        src_x, src_y = ext_src[0], ext_src[1] + offset
                        dst_x, dst_y = ext_dst[0], ext_dst[1] + offset
                    else:  # B/T
                        # X axis offset (spread horizontally)
                        src_x, src_y = ext_src[0] + offset, ext_src[1]
                        dst_x, dst_y = ext_dst[0] + offset, ext_dst[1]

                    if is_symmetric:
                        c.setStrokeColor(colors.red)
                        c.setLineWidth(1.0)
                        c.line(src_x, src_y, dst_x, dst_y)
                        if count == 1:
                            self.logger.info(f"  Symmetric pair: {source} <-> {dest}, drew SOLID line")
                    else:
                        c.setStrokeColor(colors.red)
                        c.setLineWidth(1.0)
                        c.setDash([4, 2])
                        c.line(src_x, src_y, dst_x, dst_y)
                        c.setDash([])
                        if i == 0:
                            self.logger.error(f"  Asymmetric: {source} -> {dest}, drew DASHED line")

        self._draw_center_info(c, cx, cy, edge_apr, l_cnt, b_cnt, r_cnt, t_cnt, apr_data_by_side)
        c.save()

    def generate_apr_pdf(self, filename):
        if not HAS_REPORTLAB: return
        self.logger.info(f"Generating APR Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4)); width, height = landscape(A4)
        cx, cy = width/2, 255; self._draw_header(c, "APR PIN DIAGRAM", width, height)
        edge = 280
        c.setLineWidth(2); c.rect(cx - edge/2, cy - edge/2, edge, edge)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        t_early = []
        found_l = False
        seen_die_nums = set()  # For deduplication: skip duplicate DIE_NUM
        for row in self.parser.data:
            pname = row['DIE_PIN_NAME'].upper()
            # Skip NC, DOWNBOUND, and DIE_PAD_NUM='0' for APR (no die pad to show)
            if pname in ('NC', 'DOWNBOUND') or row['DIE_NUM'] in ('0', '-'): continue
            # Skip Inner_bound and PKG_NUM='-'
            if row['PKG_NUM'].upper() == 'INNER_BOUND' or row['PKG_NUM'] == '-': continue
            # Skip duplicate DIE_NUM (only show one APR pin for multiple wires to same point)
            die_num = row['DIE_NUM']
            if die_num in seen_die_nums:
                continue
            seen_die_nums.add(die_num)
            loc = row['DIE_LOC'].upper()
            if loc in data_by_side:
                if loc == 'L': found_l = True

                if loc == 'T' and not found_l:
                    t_early.append(row)
                else:
                    data_by_side[loc].append(row)
        data_by_side['T'].extend(t_early)
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)
        self._draw_center_info(c, cx, cy, edge, l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        apr_edge = {'L': cx - edge/2, 'R': cx + edge/2, 'B': cy - edge/2, 'T': cy + edge/2}
        header_bottom = 510
        # For APR, use max pin count to ensure uniform font size across all 4 sides
        max_cnt = max(l_cnt, b_cnt, r_cnt, t_cnt)
        for side in ('L', 'B', 'R', 'T'):
            limit = apr_edge[side]
            if side == 'T': limit = header_bottom
            self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, getattr(self, f"_{side}_pos")(cx, cy, edge), max_cnt, 'APR', label_inside=False, max_label_extent=limit, allow_overflow=True)
        c.save()

    def generate_pkg_pdf(self, filename):
        if not HAS_REPORTLAB: return
        self.logger.info(f"Generating PKG Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4)); width, height = landscape(A4)
        cx, cy = width/2, 255; self._draw_header(c, "PACKAGE PIN DIAGRAM", width, height)
        edge = 280
        c.setLineWidth(2); c.rect(cx - edge/2, cy - edge/2, edge, edge)
        pkg_data = {}; order = []
        for row in self.parser.data:
            pnum = row['PKG_NUM']
            pname = row['DIE_PIN_NAME'].upper()
            # Skip: POWERCUT, but NOT NC (NC should show on PKG) and NOT DOWNBOUND
            if 'POWERCUT' in pname: continue
            if pnum in ('0', '-'): continue
            if pnum not in pkg_data: pkg_data[pnum] = row.copy(); order.append(pnum)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        # Build side mapping from PACKAGE definition (same logic as sanity check)
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        expected = {'L': int(parts[1]), 'B': int(parts[2]), 'R': int(parts[3]), 'T': int(parts[4])}

        def get_side_from_pnum(pnum_str):
            try:
                p = int(pnum_str)
                if p == 0: return None
                cumulative = 0
                for side in ['L', 'B', 'R', 'T']:
                    cumulative += expected[side]
                    if p <= cumulative: return side
                return None
            except (ValueError, TypeError):
                return None

        for pnum in order:
            loc = pkg_data[pnum]['PKG_LOC'].upper()
            pname = pkg_data[pnum]['DIE_PIN_NAME'].upper()
            # For DOWNBOUND or pins with invalid LOCATION, infer side from PIN_NUM
            if pname == 'DOWNBOUND' or loc not in data_by_side:
                inferred_side = get_side_from_pnum(pnum)
                if inferred_side:
                    data_by_side[inferred_side].append(pkg_data[pnum])
            elif loc in data_by_side:
                data_by_side[loc].append(pkg_data[pnum])
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)
        self._draw_center_info(c, cx, cy, edge, l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        pkg_edge = {'L': cx - edge/2, 'R': cx + edge/2, 'B': cy - edge/2, 'T': cy + edge/2}
        header_bottom = 510
        # For PKG, use max pin count to ensure uniform font size across all 4 sides
        max_cnt = max(l_cnt, b_cnt, r_cnt, t_cnt)
        for side in ('L', 'B', 'R', 'T'):
            limit = pkg_edge[side]
            if side == 'T': limit = header_bottom
            self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, getattr(self, f"_{side}_pos")(cx, cy, edge), max_cnt, 'PKG', label_inside=False, max_label_extent=limit)
        c.save()

    def _L_pos(self, cx, cy, edge): return (cx - edge/2, cy)
    def _B_pos(self, cx, cy, edge): return (cx, cy - edge/2)
    def _R_pos(self, cx, cy, edge): return (cx + edge/2, cy)
    def _T_pos(self, cx, cy, edge): return (cx, cy + edge/2)

    def _draw_side_boxes(self, c, side, pins, cx, cy, length, b_pos, total, mode, label_inside=False, max_label_extent=None, allow_overflow=False):
        bx, by = b_pos; coords = {}
        if not pins: return coords
        actual_cnt = len(pins); calc_total = max(actual_cnt, total); step = length / (calc_total + 1)
        box_thickness = max(1, min(step * 0.8, 6)); font_size = max(2, min(step * 0.9, 8))
        if mode == 'PKG': font_size = min(font_size + 1, 10)
        box_len = 15 if mode == 'APR' else 25
        for idx, pin in enumerate(pins, 1):
            pname = pin['DIE_PIN_NAME']; display_name = pname
            if '%' in pname: display_name = pname.split('%')[-1] if mode == 'APR' else pname.split('%')[0]
            px, py = 0, 0; bw, bh = 0, 0
            if side == 'L':
                bw, bh = box_len, box_thickness; px = bx - (0 if label_inside else bw); py = (by + length/2) - (idx * step) - (bh/2)
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (bx, py + bh/2), 'bw': bw, 'bh': bh, 'side': side}
            elif side == 'B':
                bw, bh = box_thickness, box_len; px = (bx - length/2) + (idx * step) - (bw/2); py = by - (0 if label_inside else bh)
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (px + bw/2, by), 'bw': bw, 'bh': bh, 'side': side}
            elif side == 'R':
                bw, bh = box_len, box_thickness; px = bx - (bw if label_inside else 0); py = (by - length/2) + (idx * step) - (bh/2)
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (bx, py + bh/2), 'bw': bw, 'bh': bh, 'side': side}
            elif side == 'T':
                bw, bh = box_thickness, box_len; px = (bx + length/2) - (idx * step) - (bw/2); py = by - (bh if label_inside else 0)
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (px + bw/2, by), 'bw': bw, 'bh': bh, 'side': side}
            c.setLineWidth(0.5); c.setStrokeColor(colors.black); direction = pin['DIRECTION']
            if 'POWERCUT' in pname.upper(): c.setFillColor(colors.black); c.rect(px, py, bw, bh, fill=1)
            elif pname.upper() == 'NC': c.setFillColor(colors.black); c.rect(px, py, bw, bh, fill=1)
            elif direction == 'P': c.setFillColor(colors.red); c.rect(px, py, bw, bh, fill=1)
            elif direction == 'G': c.setFillColor(colors.blue); c.rect(px, py, bw, bh, fill=1)
            else: c.rect(px, py, bw, bh, fill=0)
            c.setFillColor(colors.black)
            # Check if label would extend beyond boundary (page edge, header, or outer frame)
            small_font = font_size
            if max_label_extent is not None and not allow_overflow:
                char_width = font_size * 0.6
                name_len = len(display_name)
                label_extent = name_len * char_width
                # Header boundary for T side (labels go upward)
                header_bottom = 510 if side == 'T' else None
                if side == 'L':
                    label_end = px - 4
                    limit = max_label_extent
                    if label_end - label_extent < limit:
                        small_font = max(2, font_size - 2)
                elif side == 'R':
                    label_end = px + bw + 4 + label_extent
                    limit = max_label_extent
                    if label_end > limit:
                        small_font = max(2, font_size - 2)
                elif side == 'B':
                    label_end = py - 4
                    limit = max_label_extent
                    if label_end - label_extent < limit:
                        small_font = max(2, font_size - 2)
                elif side == 'T':
                    label_end = py + bh + 4 + label_extent
                    # Check against both max_label_extent and header boundary
                    limit = max_label_extent
                    if header_bottom is not None:
                        limit = min(limit, header_bottom) if limit else header_bottom
                    if label_end > limit:
                        small_font = max(2, font_size - 2)
            c.setFont("Helvetica", small_font)
            if side == 'L':
                c.drawRightString(px - 4, py + (bh/2) - (small_font/2), display_name)
            elif side == 'R':
                c.drawString(px + bw + 4, py + (bh/2) - (small_font/2), display_name)
            elif side == 'T':
                c.saveState()
                c.translate(px + bw/2, py + bh + 2)
                c.rotate(90); c.drawString(0, -small_font/2, display_name)
                c.restoreState()
            elif side == 'B':
                c.saveState()
                c.translate(px, py - 4)
                c.rotate(270); c.drawString(0, 0, display_name)
                c.restoreState()

            # --- Pin Numbering (1, 5, 10...) and Start Dot (Pin 1) ---
            num_str = pin['DIE_NUM'] if mode == 'APR' else pin['PKG_NUM']
            try:
                n_int = int(num_str)
                # 1. Draw Start Dot (Top-Left marker: always first pin of Side L)
                draw_dot = (side == 'L' and idx == 1)

                is_combined_inner_apr = (mode == 'APR' and label_inside)
                if draw_dot and not is_combined_inner_apr:
                    dot_r = 6
                    dot_x, dot_y = px + bw/2, py + bh/2
                    if side == 'L': dot_x += bw + 12
                    elif side == 'R': dot_x -= 12
                    elif side == 'T': dot_y -= 12
                    elif side == 'B': dot_y += bh + 12
                    c.setFillColor(colors.black)
                    c.circle(dot_x, dot_y, dot_r, stroke=0, fill=1)

                # 2. Draw Numbering (1, 5, 10...)
                if n_int == 1 or n_int % 5 == 0:
                    c.setFont("Helvetica", font_size)
                    c.setFillColor(colors.black)
                    if side == 'L': c.drawString(bx + 2, py + (bh/2) - (font_size/2), num_str)
                    elif side == 'R': c.drawRightString(bx - 2, py + (bh/2) - (font_size/2), num_str)
                    elif side == 'T': c.drawCentredString(px + bw/2, by - font_size, num_str)
                    elif side == 'B': c.drawCentredString(px + bw/2, by + 2, num_str) # Fixed numbering position
            except (ValueError, TypeError):
                pass
        return coords

    def _extend_point_toward_center(self, pt, side, distance, cx, cy):
        """Extend a point toward chip center by given distance."""
        x, y = pt
        if side == 'L':
            return (x + distance, y)
        elif side == 'R':
            return (x - distance, y)
        elif side == 'B':
            return (x, y + distance)
        elif side == 'T':
            return (x, y - distance)
        return pt

    def _draw_extended_pin(self, c, frame_edge_pt, side, box_len, box_thickness, color):
        """Draw an extended pin shape with SAME shape as original pin, starting from frame edge.
        frame_edge_pt: point on the inner edge of APR frame for this side
        box_len: length of pin shape (perpendicular to edge, same as original)
        box_thickness: thickness extending toward chip center (same as original)
        color: fill color

        NOTE: Due to parameter passing, box_len and box_thickness meanings swap for B/T sides
        L side: original = (box_len x box_thickness) horizontal
        R side: original = (box_len x box_thickness) horizontal
        T side: original = (box_thickness x box_len) vertical [parameters swapped in call]
        B side: original = (box_thickness x box_len) vertical [parameters swapped in call]
        """
        x, y = frame_edge_pt
        c.setFillColor(color); c.setStrokeColor(color); c.setLineWidth(0.5)
        if side == 'L':
            # Original pin: (box_len x box_thickness) at frame edge
            # Extended: same shape, starts at frame inner edge, extends inward
            c.rect(x, y - box_thickness/2, box_len, box_thickness, fill=0, stroke=1)
        elif side == 'R':
            # Original pin: (box_len x box_thickness) at frame edge
            # Extended: same shape, starts at frame inner edge, extends inward
            c.rect(x - box_len, y - box_thickness/2, box_len, box_thickness, fill=0, stroke=1)
        elif side == 'B':
            # B side: frame at y=350, chip center at y=240, toward center = upward (y increases)
            # Original pin: (box_len x box_thickness) where box_len=bw(width), box_thickness=bh(height)
            # Extended: width scaled to 80%, height=box_thickness, bottom at y, extending upward
            width = box_len * 0.8
            c.rect(x - width/2, y, width, box_thickness, fill=0, stroke=1)
        elif side == 'T':
            # T side: frame at y=130, chip center at y=240, toward center = downward (y decreases)
            # Original pin: (box_len x box_thickness) where box_len=bw(width), box_thickness=bh(height)
            # Extended: width scaled to 80%, height=box_thickness, top at y, extending downward
            width = box_len * 0.8
            c.rect(x - width/2, y - box_thickness, width, box_thickness, fill=0, stroke=1)

    def _draw_header(self, c, title, width, height):
        c.setLineWidth(1); c.setStrokeColor(colors.black); c.rect(50, height - 85, width - 100, 65)
        c.setFont("Helvetica-Bold", 18); c.drawCentredString(width/2, height - 45, title)
        c.setFont("Helvetica", 10); h = self.parser.header
        proj = h.get('PRODUCTION NO.', h.get('PRODUCTION NO', 'N/A'))
        pkg = h.get('PACKAGE', 'N/A'); ver = h.get('VERSION', 'N/A')
        c.drawString(60, height - 65, f"Project: {proj}"); c.drawCentredString(width/2, height - 65, f"Package: {pkg}"); c.drawRightString(width - 60, height - 65, f"Version: {ver}")

    def _draw_center_info(self, c, cx, cy, edge, l, b, r, t, data):
        f_max = max(l, b, r, t)
        for s in ('L', 'B', 'R', 'T'): f_max = max(f_max, len(data.get(s, [])))
        step = edge / (f_max + 1); font_size = max(2, min(step * 0.9, 7)); spacing = font_size * 1.5
        c.setFont("Helvetica", font_size); c.setFillColor(colors.black)
        h = self.parser.header
        c.drawCentredString(cx, cy + spacing, f"Project: {h.get('PRODUCTION NO.', 'N/A')}")
        c.drawCentredString(cx, cy, f"Package: {h.get('PACKAGE', 'N/A')}")
        c.drawCentredString(cx, cy - spacing, f"Version: {h.get('VERSION', 'N/A')}")

# --- Checker Class ---
class Checker:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def check_stagger(self, filename):
        self.logger.info("Running Stagger Density Check...")
        try:
            with open(filename, 'w') as f:
                f.write("STAGGER DENSITY CHECK REPORT\n")
                f.write("=" * 30 + "\n")
                io_count = 0
                max_io = 8
                for row in self.parser.data:
                    if row['DIRECTION'] in ('I', 'O', 'B'):
                        io_count += 1
                        if io_count > max_io:
                            msg = f"[WARN] Consecutive I/O at Pin {row['PKG_NUM']} ({row['DIE_PIN_NAME']})"
                            f.write(msg + "\n")
                            self.logger.warn(msg)
                    elif row['DIRECTION'] in ('P', 'G'):
                        io_count = 0
            self.logger.info(f"Report saved: {filename}")
        except Exception as e:
            self.logger.error(f"Error in checker: {e}")

# --- Writer Class ---
class Writer:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def generate_completed_list(self, filename):
        self.logger.info(f"Generating completed list: {filename}")
        try:
            # Always use canonical headers (not raw_headers which may contain old field names)
            h = ['PKG_NUM', 'PKG_PIN_NAME', 'DIE_NUM', 'DIE_PIN_NAME', 'IO_CELL_NAME', 'PKG_LOC', 'DIE_LOC', 'DIRECTION', 'LOAD', 'SLEW', 'SSO']
            
            with open(filename, 'w') as f:
                for k, v in sorted(self.parser.header.items()):
                    f.write(f"{k:<20} : {v}\n")
                f.write("\n")
                
                # Format header row (11 columns: PKG_NUM, PKG_PIN_NAME, DIE_NUM, DIE_PIN_NAME, IO_CELL_NAME, PKG_LOC, DIE_LOC, DIRECTION, LOAD, SLEW, SSO)
                head_str = f"{h[0]:<8} {h[1]:<12} {h[2]:<12} {h[3]:<20} {h[4]:<12} {h[5]:<10} {h[6]:<18} "
                if len(h) > 7: head_str += f"{h[7]:<10} "
                if len(h) > 8: head_str += f"{h[8]:<6} "
                if len(h) > 9: head_str += f"{h[9]:<6} "
                if len(h) > 10: head_str += f"{h[10]:<6} "
                f.write(head_str.rstrip() + "\n")
                f.write("-" * 120 + "\n")
                
                def norm(v):
                    return v if v and v.strip() else '-'

                for r in self.parser.data:
                    row_str = f"{norm(r['PKG_NUM']):<8} {norm(r['PKG_PIN_NAME']):<12} {norm(r['DIE_NUM']):<12} {norm(r['DIE_PIN_NAME']):<20} {norm(r['IO_CELL_NAME']):<12} {norm(r['PKG_LOC']):<10} {norm(r['DIE_LOC']):<18} "
                    if len(h) > 7: row_str += f"{norm(r['DIRECTION']):<10} "
                    if len(h) > 8: row_str += f"{norm(r['LOAD']):<6} "
                    if len(h) > 9: row_str += f"{norm(r['SLEW']):<6} "
                    if len(h) > 10: row_str += f"{norm(r['SSO']):<6} "
                    f.write(row_str.rstrip() + "\n")
        except Exception as e:
            self.logger.error(f"Error in writer: {e}")

    def generate_completed_csv(self, filename):
        """Generate CSV format of completed pin list."""
        self.logger.info(f"Generating completed list (CSV): {filename}")
        try:
            h = ['PKG_NUM', 'PKG_PIN_NAME', 'DIE_NUM', 'DIE_PIN_NAME',
                 'IO_CELL_NAME', 'PKG_LOC', 'DIE_LOC', 'DIRECTION', 'LOAD', 'SLEW', 'SSO']

            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=h)
                writer.writeheader()

                def norm(v):
                    return v if v and v.strip() else '-'

                for r in self.parser.data:
                    row = {field: norm(r[field]) for field in h}
                    writer.writerow(row)
        except Exception as e:
            self.logger.error(f"Error in CSV writer: {e}")

    def generate_innovus_io(self, filename):
        self.logger.info(f"Generating Innovus IO Constraint: {filename}")
        try:
            # Sort data by DIE_PAD_NUM for correct ring sequence in constraints
            sorted_data = sorted([r for r in self.parser.data if r['DIE_PIN_NAME'].upper() != 'NC' and r['DIE_NUM'] != '0'], 
                                 key=lambda x: int(x['DIE_NUM']))
            
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            for row in sorted_data:
                loc = row['DIE_LOC'].upper()
                if loc in sides: sides[loc].append(row['INST_NAME'])
            
            with open(filename, 'w') as f:
                f.write("( globals\n    version = 3\n    io_order = default\n)\n")
                f.write("( iopad\n")
                s_map = {'L': 'left', 'B': 'bottom', 'R': 'right', 'T': 'top'}
                for code in ['L', 'B', 'R', 'T']:
                    if not sides[code]: continue
                    f.write(f"    ( {s_map[code]}\n")
                    f.write(f"        ( locals ring_number = 1 )\n")
                    for inst in sides[code]:
                        f.write(f"        ( inst name=\"{inst}\" offset=0 orientation=R0 place_status=fixed spacing=0 )\n")
                    f.write("    )\n")
                f.write(")\n")
        except Exception as e:
            self.logger.error(f"Error in writer: {e}")

    def generate_icc2_io(self, filename):
        self.logger.info(f"Generating ICC2 IO Constraint: {filename}")
        try:
            # Sort data by DIE_PAD_NUM for correct ring sequence
            sorted_data = sorted([r for r in self.parser.data if r['DIE_PIN_NAME'].upper() != 'NC' and r['DIE_NUM'] != '0'], 
                                 key=lambda x: int(x['DIE_NUM']))
            
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            for row in sorted_data:
                loc = row['DIE_LOC'].upper()
                if loc in sides: sides[loc].append(row['INST_NAME'])
                
            with open(filename, 'w') as f:
                f.write("# ICC2 IO Assignment File (Tcl commands)\n\n")
                s_map = {'L': 'left', 'B': 'bottom', 'R': 'right', 'T': 'top'}
                for code in ['L', 'B', 'R', 'T']:
                    if not sides[code]: continue
                    f.write(f"set_io_pad_constraints -side {s_map[code]} -pad_names {{\\\n")
                    for inst in sides[code]:
                        f.write(f"    {inst} \\\n")
                    f.write("}\n\n")
        except Exception as e:
            self.logger.error(f"Error in ICC2 writer: {e}")

# --- Main Logic ---
def main():
    p = argparse.ArgumentParser(description="FPAD_ASSIGN Standalone Tool")
    p.add_argument("-list", required=True, help="Pin list file")
    p.add_argument("-v", nargs='*', help="Verilog files")
    p.add_argument("-apr", action="store_true", help="APR Diagram")
    p.add_argument("-pkg", action="store_true", help="PKG Diagram")
    p.add_argument("-combined", action="store_true", help="Combined Diagram with wires")
    p.add_argument("-c", action="store_true", help="Generate .new and .const files")
    p.add_argument("-stagger", action="store_true", help="Stagger check")
    p.add_argument("-all", action="store_true", help="All functions")
    p.add_argument("-o", "--outdir", default=".", help="Output folder (default: current directory)")
    args = p.parse_args()

    if args.all: args.apr = args.pkg = args.combined = args.c = args.stagger = True

    # 1. Initial Logger
    logger = Logger() # Defaults to stdout only if no filename
    logger.info("Starting FPAD_ASSIGN Standalone Tool...")

    # 2. Pre-scan the pin list for PRODUCTION NO. to set up output early
    proj_no = "fpad_out"
    if os.path.exists(args.list):
        try:
            with open(args.list, 'r') as f:
                for line in f:
                    match = re.search(r'PRODUCTION NO\.\s*:\s*(.*)', line, re.I)
                    if match:
                        proj_no = match.group(1).strip()
                        break
        except: pass
    
    proj_no = re.sub(r'[^\w\-]', '_', proj_no)
    
    out_dir = "."
    if args.outdir:
        out_dir = args.outdir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            # We can't log this to the file yet, but it's okay

    # 3. Setup final log file location
    log_path = os.path.join(out_dir, f"{proj_no}.log")
    logger.log_fn = log_path
    with open(log_path, 'w') as f:
        f.write(f"--- FPAD_ASSIGN Execution Log ({datetime.datetime.now()}) ---\n")
        f.write(f"Project: {proj_no}\n")
    logger.info(f"Log file initialized: {log_path}")

    # 4. Now run the full parsing and check
    parser = Parser(logger, args.list, args.v)
    parser.parse_list()

    if args.v:
        parser.parse_verilog()
        parser.bridge_data()
    else:
        logger.warn("No Verilog files, skipping bridging.")

    prefix = os.path.join(out_dir, proj_no)

    if args.stagger:
        Checker(logger, parser).check_stagger(f"{prefix}_stagger.rpt")
    
    if args.c:
        w = Writer(logger, parser)
        w.generate_completed_list(f"{prefix}.new")
        w.generate_completed_csv(f"{prefix}.new.csv")
        w.generate_innovus_io(f"{prefix}_chip.inn.const")
        w.generate_icc2_io(f"{prefix}_chip.icc2.const")

    if args.apr or args.pkg or args.combined:
        pg = PDFGen(logger, parser)
        if args.apr: pg.generate_apr_pdf(f"{prefix}_apr.pdf")
        if args.pkg: pg.generate_pkg_pdf(f"{prefix}_pkg.pdf")
        if args.combined: pg.generate_combined_pdf(f"{prefix}_combined.pdf")

    logger.info("Execution successful.")

if __name__ == "__main__":
    main()
