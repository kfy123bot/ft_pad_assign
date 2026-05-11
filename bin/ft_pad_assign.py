#!/usr/bin/env python3
"""
FT_PAD_ASSIGN - Standalone Version
A tool for IC I/O assignment, visualization, and validation.
Usage: python3 ft_pad_assign.py -list <pin_list> -v <verilog_files> [options]
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

VERSION = "v3.1"

# --- Logger Class ---
class Logger:
    def __init__(self, log_fn=None):
        self.log_fn = log_fn
        self._fh = None
        self._indent = 0  # nesting depth
        if self.log_fn:
            self._fh = open(self.log_fn, 'w')
            self._fh.write(f"--- FT_PAD_ASSIGN Execution Log ({datetime.datetime.now()}) ---\n")
            self._fh.flush()

    def set_log_file(self, log_fn):
        if self._fh:
            self._fh.close()
        self.log_fn = log_fn
        self._fh = open(self.log_fn, 'w')
        self._fh.write(f"--- FT_PAD_ASSIGN Execution Log ({datetime.datetime.now()}) ---\n")
        self._fh.flush()

    def indent(self):
        self._indent += 1

    def dedent(self):
        self._indent = max(0, self._indent - 1)

    def _prefix(self):
        if self._indent == 0:
            return ""
        return "│  " * self._indent

    def _write(self, out):
        line = self._prefix() + out
        print(line)
        if self._fh:
            self._fh.write(line + "\n")
            self._fh.flush()

    def section(self, msg):
        """Print a section header (file reading). Clears indent first."""
        line = f"├── {msg}"
        print(line)
        if self._fh:
            self._fh.write(line + "\n")
            self._fh.flush()

    def info(self, msg):
        self._write(f"[INFO ] {msg}")

    def warn(self, msg):
        self._write(f"[WARN ] {msg}")

    def error(self, msg):
        self._write(f"[ERROR] {msg}")

    def fatal(self, msg):
        self._write(f"[FATAL] {msg}")
        if self._fh:
            self._fh.close()
        sys.exit(1)

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None

# --- Field Alias Mapping (Header-Driven Parsing) ---
FIELD_ALIASES = {
    'PKG_NUM':      ['PKG_NUM', 'PIN_NUM'],
    'PKG_PIN_NAME': ['PKG_PIN_NAME', 'PACKAGE_PIN', 'PKG_PIN'],
    'DIE_NUM':      ['DIE_NUM', 'DIE_PAD_NUM'],
    'DIE_PIN_NAME': ['DIE_PIN_NAME', 'PIN_NAME'],
    'IO_CELL_NAME': ['IO_CELL_NAME', 'CELL_NAME', 'IO_CELL', 'IOCELL'],
    'PKG_LOC':      ['PKG_LOC', 'LOCATION', 'PIN_LOCA'],
    'DIE_LOC':      ['DIE_LOC', 'DIE_PAD_NUM_LOC', 'DIE_LOCA'],
    'DIRECTION':    ['DIRECTION', 'IO_DIRECTION', 'IO_TYPE', 'DIR'],
    'LOAD':         ['LOAD', 'CAP', 'CAPACITANCE'],
    'SLEW':         ['SLEW', 'TRANSITION', 'SLEW_RATE'],
    'SSO':          ['SSO', 'SSO_RATIO'],
}

# --- Package Body Size Lookup (mm) ---
# Duplicate pin counts resolve to the smallest body size.
QFN_BODY_SIZES = {
    12: 3, 16: 3, 20: 3,
    24: 4, 28: 4,
    32: 5, 40: 5,
    44: 6, 48: 6, 56: 6,
    64: 7,
    76: 9, 88: 9,
}

# --- QFN Physical Dimensions (mm) for accurate pin drawing ---
# Source: JEDEC MO-220 (docs/QFN40*.xlsx, docs/QFN56*.xlsx)
# (body_mm, pitch_mm, pin_width_typ_mm, pin_length_typ_mm, exposed_pad_mm)
QFN_PHYSICAL_SPECS = {
    32: (5.0, 0.4, 0.20, 0.40, 3.30),
    40: (5.0, 0.4, 0.20, 0.40, 3.30),
    44: (6.0, 0.4, 0.20, 0.40, 4.30),
    48: (6.0, 0.4, 0.20, 0.40, 4.30),
    56: (6.0, 0.4, 0.20, 0.40, 4.30),
    64: (7.0, 0.4, 0.20, 0.40, 5.30),
    76: (9.0, 0.5, 0.25, 0.50, 7.00),
    88: (9.0, 0.5, 0.25, 0.50, 7.00),
}

# --- Placement Transforms ---
# Maps PLACEMENT header value → (rotation_degrees, flip_x)
PLACEMENT_TRANSFORMS = {
    'R0': (0, False), 'R90': (90, False), 'R180': (180, False), 'R270': (270, False),
    'R0_FLIP_X': (0, True), 'R90_FLIP_X': (90, True), 'R180_FLIP_X': (180, True), 'R270_FLIP_X': (270, True),
}

# --- DIE Overlay Color Scheme (unified for all overlay dies) ---
DIE_OVERLAY_COLORS = {
    'frame': '#8B4513',      # brown
    'signal': '#8B4513',     # brown for signal pads
    'wire_power': colors.red,
    'wire_signal': '#8B4513',
}

def rotate_point(x, y, degrees):
    """Rotate (x, y) around origin.
    R90:  逆時針 90 度 → (-y, x)
    R180: 倒過來       → (-x, -y)
    R270: 順時針 90 度 → (y, -x)
    """
    if degrees == 0:
        return x, y
    elif degrees == 90:
        return -y, x
    elif degrees == 180:
        return -x, -y
    elif degrees == 270:
        return y, -x
    return x, y

# --- DIE2 Spec Parser ---
def parse_die2_md(filepath, logger):
    """Parse a DIE2 spec markdown file (e.g. JD1750_PSRAM.md).

    Returns dict: {'die_size': (w, h) in um, 'pads': [{'num': str, 'name': str, 'x': float, 'y': float}, ...]}
    Uses only the first section found (ignores subsequent ## headers).
    """
    result = {'die_size': None, 'pads': []}
    logger.info(f"Reading: {filepath}")
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Cannot read DIE2 spec file: {filepath} ({e})")
        return result

    found_section = False
    in_table = False
    header_seen = False

    for line in lines:
        stripped = line.strip().replace('\\_', '_')
        # Stop at next section header if we already found one
        if stripped.startswith('## ') and found_section:
            break
        if stripped.startswith('## '):
            found_section = True

        # Parse DIE_SIZE (handle markdown escaped underscores: DIE\_SIZE)
        if 'DIE_SIZE' in stripped and not result['die_size']:
            m = re.search(r'(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)', stripped)
            if m:
                result['die_size'] = (float(m.group(1)), float(m.group(2)))
                logger.info(f"DIE2 DIE_SIZE: {m.group(1)}x{m.group(2)} um")

        # Parse table rows: | D2.N | PAD_NAME | X | Y |
        if '|' not in stripped:
            continue
        cells = [c.strip() for c in stripped.split('|')]
        # Remove empty leading/trailing from split
        cells = [c for c in cells if c]

        if len(cells) < 3:
            continue

        # Check for header row (PAD NO. / PAD Name / X Location / Y Location)
        if 'PAD' in cells[0].upper() and 'NAME' in cells[1].upper():
            header_seen = True
            in_table = True
            continue

        # Skip separator rows (---)
        if cells[0].startswith('---'):
            continue

        # Data rows: first cell should be D2.N
        if in_table and re.match(r'D2\.\d+', cells[0]):
            pad_num = cells[0]
            pad_name = cells[1] if len(cells) > 1 else ''
            try:
                x = float(cells[2]) if len(cells) > 2 else 0.0
                y = float(cells[3]) if len(cells) > 3 else 0.0
            except ValueError:
                logger.warn(f"DIE2: skip row with non-numeric coords: {stripped}")
                continue
            result['pads'].append({'num': pad_num, 'name': pad_name, 'x': x, 'y': y})

    logger.info(f"DIE2 parsed: {len(result['pads'])} pads from {filepath}")
    return result


def parse_die_csv(filepath, die_prefix, logger):
    """Unified parser for DIE2/DIE3 CSV spec files.

    Args:
        filepath: Path to CSV file
        die_prefix: 'DIE2' or 'DIE3'
        logger: Logger instance

    Returns dict: {
        'name': str,              # DIE2_NAME / DIE3_NAME
        'die_size': (w, h),       # um
        'loc': (x, y),            # um, relative to DIE1 bottom-left (0,0)
        'loc_relative': 'bottom_left',
        'placement': str,         # e.g. 'R0', 'R90_FLIP_X'
        'rotation': int,          # 0, 90, 180, 270
        'flip_x': bool,
        'pads': [{'num': str, 'name': str, 'x': float, 'y': float,
                   'd1_pad': str, 'type': str}, ...]
    }
    """
    pad_prefix = 'D2' if die_prefix == 'DIE2' else 'D3'
    default_name = die_prefix
    result = {
        'name': default_name, 'die_size': None, 'loc': None,
        'loc_relative': 'bottom_left', 'placement': 'R0',
        'rotation': 0, 'flip_x': False, 'pads': []
    }
    logger.info(f"Reading: {filepath}")
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Cannot read {die_prefix} CSV file: {filepath} ({e})")
        return result

    name_key = f'{die_prefix}_NAME'
    loc_key = f'{die_prefix}_LOC'
    num_key = f'{pad_prefix}_NUM'

    # Phase 1: parse KEY : VALUE headers
    data_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or all(c in ', ' for c in stripped):
            data_start = i + 1
            continue
        if ':' in stripped:
            key, _, val = stripped.partition(':')
            key = key.strip().upper()
            val = val.strip().strip(',').strip()
            if key == name_key:
                result['name'] = val
                logger.info(f"  {name_key}: {val}")
            elif key == 'DIE_SIZE':
                m = re.match(r'(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)', val)
                if m:
                    result['die_size'] = (float(m.group(1)), float(m.group(2)))
                    logger.info(f"  DIE_SIZE: {m.group(1)}x{m.group(2)} um")
            elif key == loc_key:
                m = re.match(r'([\d.]+)\s*[,xX+\s]\s*([\d.]+)', val)
                if m:
                    try:
                        result['loc'] = (float(m.group(1)), float(m.group(2)))
                        logger.info(f"  {loc_key}: ({m.group(1)}, {m.group(2)}) um (relative to DIE1 bottom-left)")
                    except ValueError:
                        logger.error(f"Invalid {loc_key} value: '{val}'")
                else:
                    logger.error(f"Invalid {loc_key} value: '{val}'")
            elif key == 'PLACEMENT':
                val_upper = val.upper().replace(' ', '_')
                if val_upper in PLACEMENT_TRANSFORMS:
                    rot, flip = PLACEMENT_TRANSFORMS[val_upper]
                    result['placement'] = val_upper
                    result['rotation'] = rot
                    result['flip_x'] = flip
                    logger.info(f"  PLACEMENT: {val_upper} (rotation={rot}, flip_x={flip})")
                else:
                    logger.error(f"Invalid PLACEMENT value: '{val}'. Valid: {', '.join(PLACEMENT_TRANSFORMS.keys())}")
        else:
            # First non-header, non-blank line → data table starts
            data_start = i
            break

    # Phase 2: parse data table (skip header row)
    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        cells = [c.strip() for c in stripped.split(',')]
        if len(cells) < 4:
            continue
        # Skip header row (match D2_NUM, D3_NUM, PAD NO., etc.)
        if re.match(r'(D[23]_NUM|PAD)', cells[0].upper()):
            continue
        pad_num = cells[0]
        pad_name = cells[1]
        try:
            x = float(cells[2])
            y = float(cells[3])
        except ValueError:
            continue
        d1_pad = cells[4].strip() if len(cells) > 4 and cells[4].strip() else ''
        conn_type = cells[5].strip() if len(cells) > 5 and cells[5].strip() else ''
        result['pads'].append({'num': pad_num, 'name': pad_name, 'x': x, 'y': y,
                               'd1_pad': d1_pad, 'type': conn_type})

    n_conn = sum(1 for p in result['pads'] if p.get('d1_pad'))
    logger.info(f"  Parsed: {len(result['pads'])} pads ({n_conn} connections)")
    return result


def parse_die2_csv(filepath, logger):
    """Parse DIE2 spec CSV file. Wrapper around parse_die_csv()."""
    return parse_die_csv(filepath, 'DIE2', logger)


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
        self.logger.section(f"Pin List: {self.list_file}")
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
            self._ring_shift_data()
            self._reindex_pkg_num()
            self._reassign_pkg_loc()
            self._reassign_die_loc()
            self._sanity_check_list()
            for row in self.data:
                row['_orig_die_num'] = row['DIE_NUM']
            self._reorder_and_reindex_apr_data()
            self._parse_die_size()
            self._extract_cell_from_pin_name()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.fatal(f"Error parsing list: {e}")

    def _parse_csv(self, f):
        # Read all lines first to handle mixed format (header lines + CSV data)
        lines = f.readlines()

        # Skip header lines (lines containing ':' which are metadata)
        header_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            # If line has ':' in first column and doesn't look like CSV data, it's a header
            if ':' in stripped and not stripped.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '(', 'D1')):
                # Parse header line (handle CSV format with commas like "PACKAGE,,: value")
                match = re.search(r'^(PRODUCTION NO\.?|PROJECT NO\.?|PKG_TOP_LEFT_PIN|PACKAGE|VERSION|DIE_SIZE|PKG_SIZE)[,\s]*:\s*(.*)', stripped, re.I)
                if match:
                    value = match.group(2).strip().rstrip(',')
                    key = match.group(1).upper().rstrip('.')
                    if key == 'PROJECT NO':
                        key = 'PRODUCTION NO'
                    self.header[key] = value
            else:
                # Alias-aware header detection: check if any PKG_NUM alias appears in the header
                words = set(w.upper() for w in stripped.split(','))
                if any(a.upper() in words for a in FIELD_ALIASES['PKG_NUM']):
                    # CSV header row
                    self.raw_headers = stripped.split(',')
                    header_idx = i
                    break

        # Parse CSV data - include header row for DictReader
        if header_idx == -1:
            self.logger.error("CSV header row with PKG_NUM/PIN_NUM not found. Cannot parse data.")
            return
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

            # Skip Inner_bond rows - treat as comment, output as-is
            pkg_num_val = get_field('PKG_NUM')
            if pkg_num_val.upper() == 'INNER_BOND':
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
            match = re.search(r'^(PRODUCTION NO\.?|PROJECT NO\.?|PKG_TOP_LEFT_PIN|PACKAGE|VERSION|DIE_SIZE|PKG_SIZE)\s*:\s*(.*)', line, re.I)
            if match:
                key = match.group(1).upper().rstrip('.')
                if key == 'PROJECT NO':
                    key = 'PRODUCTION NO'
                self.header[key] = match.group(2)
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

                    # Skip Inner_bond rows - treat as comment, output as-is
                    pkg_num_val = get_txt_field('PKG_NUM')
                    if pkg_num_val.upper() == 'INNER_BOND':
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
            if pkg_upper == 'INNER_BOND' or row['DIE_NUM'] == '-':
                continue
            d_num = row['DIE_NUM']
            p_num = row['PKG_NUM']
            if d_num not in ('0', '-', ''):
                old_die_num_to_row[d_num] = row

            # Check for D1.xx pattern in PKG_NUM
            match = re.search(r'D1\.(\d+)', p_num.upper())
            if match:
                referencing_rows.append((row, match.group(1))) # (row_object, original_target_xx)

        # 2. Re-indexing logic: sort by DIE_LOC (L→B→R→T), then assign 1,2,3,...
        SIDE_ORDER = {'L': 0, 'B': 1, 'R': 2, 'T': 3}
        reindexable = []  # (side_order, row_index, orig_die_num_str, row)
        for row_idx, row in enumerate(self.data):
            if row['PKG_NUM'].upper() == 'INNER_BOND' or row['DIE_NUM'] == '-':
                continue
            if row['DIE_PIN_NAME'].upper() == 'NC' or row['DIE_NUM'] == '0':
                row['DIE_NUM'] = '0'
                continue
            die_loc = row['DIE_LOC'].upper()
            if die_loc not in SIDE_ORDER:
                continue
            if row['DIE_NUM'] in ('', '-'):
                continue
            reindexable.append((SIDE_ORDER[die_loc], row_idx, row['DIE_NUM'], row))

        if not reindexable:
            self.logger.warn("No reindexable DIE_NUM found, DIE_NUM reindexing skipped.")
        else:
            # Find the CSV row index of the first L-side reindexable entry.
            # T-side rows that appear before this index are the "wraparound" tail of
            # the ring and must be numbered after all other T-side rows.
            l_start = next((ri for _, ri, _, r in reindexable if r['DIE_LOC'].upper() == 'L'), None)
            n = len(self.data)

            def sort_key(entry):
                side_ord, ri, _, r = entry
                # T-side rows before the first L-side entry are ring-tail; push them
                # to the very end by inflating their row index.
                if l_start is not None and side_ord == SIDE_ORDER['T'] and ri < l_start:
                    return (side_ord, n + ri)
                return (side_ord, ri)

            # Sort by DIE_LOC side order, then by CSV row order within each side.
            # Row order preserves PKG ring order; original DIE_NUM value is not used.
            reindexable.sort(key=sort_key)
            idx = 1
            orig_to_new = {}
            for _, _row_idx, orig_die_str, row in reindexable:
                if orig_die_str in orig_to_new:
                    row['DIE_NUM'] = orig_to_new[orig_die_str]
                else:
                    row['DIE_NUM'] = str(idx)
                    orig_to_new[orig_die_str] = str(idx)
                    idx += 1
            self.logger.info(f"DIE_NUM reindexed: {len(orig_to_new)} unique values (L→B→R→T order)")

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
            else:
                self.logger.warn(f"D1.xx reference target DIE_NUM={target_xx} not found in reindex map, skipped.")

    def _sanity_check_list(self):
        self.logger.info("Performing Sanity Check on Pin List...")
        # 0. Normalize: PKG_PIN_NAME='NC'/'DOWNBOND' propagates to DIE_PIN_NAME and forces DIE_NUM='0'
        for row in self.data:
            pkg_pn = row.get('PKG_PIN_NAME', '-')
            if not pkg_pn or pkg_pn == '-':
                continue
            pkg_pn_upper = pkg_pn.upper()
            if pkg_pn_upper not in ('NC', 'DOWNBOND'):
                continue
            if row['DIE_PIN_NAME'].upper() != pkg_pn_upper:
                self.logger.info(f"PKG_PIN_NAME='{pkg_pn}' → DIE_PIN_NAME overridden (PKG_NUM={row['PKG_NUM']}, was '{row['DIE_PIN_NAME']}')")
                row['DIE_PIN_NAME'] = pkg_pn_upper
            if row['DIE_NUM'] != '0':
                self.logger.info(f"PKG_PIN_NAME='{pkg_pn}' → DIE_NUM forced to '0' (PKG_NUM={row['PKG_NUM']}, was '{row['DIE_NUM']}')")
                row['DIE_NUM'] = '0'

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

        actual_pnums = {'L': set(), 'B': set(), 'R': set(), 'T': set()}

        for row in self.data:
            loc = row['PKG_LOC'].upper()
            pnum = row['PKG_NUM']
            pname = row['DIE_PIN_NAME'].upper()

            if pname == 'DOWNBOND':
                side = loc if loc in actual_pnums else self._get_ring_side(pnum)
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
                except (ValueError, TypeError): return (1, x)
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

        # PKG_NUM=0 / D1.xx / (D1.xx) rows must not have PKG_PIN_NAME
        for row in self.data:
            pnum = row['PKG_NUM']
            pkg_pn = row.get('PKG_PIN_NAME', '-')
            if not (pkg_pn and pkg_pn != '-'):
                continue
            if pnum == '0':
                self.logger.warn(f"PKG_NUM=0 row (DIE_PIN_NAME={row['DIE_PIN_NAME']}) must not have PKG_PIN_NAME '{pkg_pn}', discarding")
                row['PKG_PIN_NAME'] = '-'
            elif re.match(r'^\(D1\.\d+\)$', pnum) or re.match(r'^D1\.\d+$', pnum, re.I):
                self.logger.warn(f"D1.xx row (PKG_NUM={pnum}) must not have PKG_PIN_NAME '{pkg_pn}', discarding")
                row['PKG_PIN_NAME'] = '-'

        # DIE_NUM=0 or '-' rows must not have DIE_PIN_NAME (NC and DOWNBOND are expected exceptions)
        _VALID_ZERO_DIE_NAMES = {'NC', 'DOWNBOND'}
        for row in self.data:
            die_num = row['DIE_NUM']
            if die_num not in ('0', '-'):
                continue
            die_pn = row['DIE_PIN_NAME']
            if not die_pn or die_pn == '-':
                continue
            if die_pn.upper() in _VALID_ZERO_DIE_NAMES:
                continue
            self.logger.warn(f"DIE_NUM={die_num} row (PKG_NUM={row['PKG_NUM']}) must not have DIE_PIN_NAME '{die_pn}', discarding")
            row['DIE_PIN_NAME'] = '-'

        self.logger.info("Pin list sanity check complete.")

    def _get_ring_side(self, pnum_str):
        """Determine L/B/R/T side for a PKG_NUM, accounting for PKG_TOP_LEFT_PIN ring offset.
        Returns side string or None if PKG_NUM is invalid.
        """
        try:
            p_int = int(pnum_str)
            if p_int <= 0:
                return None
        except (ValueError, TypeError):
            return None

        pkg_str = self.header.get('PACKAGE', '')
        if not pkg_str:
            return None
        parts = pkg_str.split()
        if len(parts) < 5:
            return None
        expected = {'L': int(parts[1]), 'B': int(parts[2]), 'R': int(parts[3]), 'T': int(parts[4])}
        total = sum(expected.values())

        aa_str = self.header.get('PKG_TOP_LEFT_PIN', '1')
        try:
            aa = int(aa_str)
        except (ValueError, TypeError):
            aa = 1

        offset = aa - 1
        ring_order = ((p_int - offset - 1) % total) + 1

        cumulative = 0
        for side in ['L', 'B', 'R', 'T']:
            cumulative += expected[side]
            if ring_order <= cumulative:
                return side
        return None

    def _ring_shift_data(self):
        """Reorder self.data so PKG_TOP_LEFT_PIN becomes the first L-side pin.
        When PKG_TOP_LEFT_PIN is 1 or missing, this is a no-op.
        """
        aa_str = self.header.get('PKG_TOP_LEFT_PIN', '1')
        try:
            aa = int(aa_str)
        except (ValueError, TypeError):
            return
        if aa == 1:
            return

        pkg_str = self.header.get('PACKAGE', '')
        if not pkg_str:
            return
        parts = pkg_str.split()
        if len(parts) < 5:
            return
        total = sum(int(x) for x in parts[1:5])
        offset = aa - 1

        # Compute sort key for each row
        sortable = []
        last_pkg_sort_key = 0
        for row in self.data:
            pnum = row['PKG_NUM']
            if pnum.upper() == 'INNER_BOND':
                sortable.append((float('inf'), row))
                continue
            try:
                p_int = int(pnum)
                if p_int > 0:
                    ring_pos = ((p_int - offset - 1) % total)
                    last_pkg_sort_key = ring_pos
                    sortable.append((ring_pos, row))
                else:
                    sortable.append((last_pkg_sort_key + 0.5, row))
            except (ValueError, TypeError):
                sortable.append((last_pkg_sort_key + 0.5, row))

        sortable.sort(key=lambda x: x[0])
        self.data = [row for _, row in sortable]
        self._ring_shifted = True
        self.logger.info(f"Ring-sorted data: PKG_TOP_LEFT_PIN={aa}, offset={offset}, total={total}")

    def _reindex_pkg_num(self):
        """Re-index PKG_NUM sequentially from 1 following ring order.
        Only applies when PKG_TOP_LEFT_PIN != 1.
        After re-indexing, PKG_TOP_LEFT_PIN is reset to 1 since numbering starts from 1.
        """
        aa_str = self.header.get('PKG_TOP_LEFT_PIN', '1')
        try:
            aa = int(aa_str)
        except (ValueError, TypeError):
            return
        if aa == 1:
            return

        idx = 1
        reassigned = 0
        for row in self.data:
            pnum = row['PKG_NUM']
            if pnum.upper() == 'INNER_BOND':
                continue
            try:
                p_int = int(pnum)
                if p_int > 0:
                    row['PKG_NUM'] = str(idx)
                    idx += 1
                    reassigned += 1
            except (ValueError, TypeError):
                pass

        if reassigned > 0:
            self.header['PKG_TOP_LEFT_PIN'] = '1'
            self.logger.info(f"Re-indexed PKG_NUM for {reassigned} rows (PKG_TOP_LEFT_PIN reset to 1)")

    def _reassign_pkg_loc(self):
        """Reassign PKG_LOC for all rows based on PKG_NUM and PACKAGE header L/B/R/T counts.
        Accounts for PKG_TOP_LEFT_PIN ring offset via _get_ring_side().
        Also validates that sum(L,B,R,T) matches total unique PKG_NUM count.
        """
        pkg_str = self.header.get('PACKAGE', '')
        if not pkg_str:
            self.logger.warn("PACKAGE header missing, cannot reassign PKG_LOC.")
            return

        parts = pkg_str.split()
        if len(parts) < 5:
            self.logger.error(f"Invalid PACKAGE format: '{pkg_str}'")
            return

        expected = {'L': int(parts[1]), 'B': int(parts[2]), 'R': int(parts[3]), 'T': int(parts[4])}
        total_expected = sum(expected.values())

        valid_pnums = set()
        for row in self.data:
            pnum = row['PKG_NUM']
            if pnum in ('0', '-', '') or pnum.upper() == 'INNER_BOND':
                continue
            if pnum.upper().startswith('D') or '(D' in pnum.upper():
                continue
            try:
                p_int = int(pnum)
                if p_int > 0:
                    valid_pnums.add(p_int)
            except (ValueError, TypeError):
                pass

        total_actual = len(valid_pnums)
        if total_expected != total_actual:
            self.logger.error(
                f"PKG_LOC reassign TOTAL MISMATCH: "
                f"PACKAGE header expects {total_expected} pins (L={expected['L']} B={expected['B']} "
                f"R={expected['R']} T={expected['T']}), but found {total_actual} unique PKG_NUMs"
            )

        reassigned = 0
        for row in self.data:
            side = self._get_ring_side(row['PKG_NUM'])
            if side:
                if row['PKG_LOC'] != side:
                    row['PKG_LOC'] = side
                    reassigned += 1
            # Rows with invalid PKG_NUM keep their existing PKG_LOC

        if reassigned > 0:
            self.logger.info(f"Reassigned PKG_LOC for {reassigned} rows.")

    def _reassign_die_loc(self):
        """Reassign DIE_LOC to follow PKG_LOC pattern (L->B->R->T).
        Only active when ring was shifted (PKG_TOP_LEFT_PIN originally != 1).
        """
        if not getattr(self, '_ring_shifted', False):
            return
        last_side = '-'
        reassigned = 0
        for row in self.data:
            pkg_loc = row['PKG_LOC']
            if pkg_loc and pkg_loc != '-':
                last_side = pkg_loc
            pnum = row['PKG_NUM']
            if pnum in ('0', '-', '') or pnum.upper() == 'INNER_BOND':
                # Shared die pad or special row: DIE_LOC follows nearest PKG_LOC
                if last_side != '-' and row['DIE_LOC'] != last_side:
                    row['DIE_LOC'] = last_side
                    reassigned += 1
            else:
                try:
                    p_int = int(pnum)
                    if p_int > 0 and pkg_loc and pkg_loc != '-':
                        if row['DIE_LOC'] != pkg_loc:
                            row['DIE_LOC'] = pkg_loc
                            reassigned += 1
                except (ValueError, TypeError):
                    pass

        if reassigned > 0:
            self.logger.info(f"Reassigned DIE_LOC for {reassigned} rows.")

    def parse_verilog(self):
        for v_file in self.v_files:
            if not os.path.exists(v_file):
                self.logger.warn(f"Verilog file not found: {v_file}")
                continue
            self.logger.section(f"Verilog: {v_file}")
            # ... rest of parse_verilog
            try:
                with open(v_file, 'r') as f:
                    content = f.read()
                # Ports — match one port per occurrence to avoid multi-line capture
                pm = re.finditer(r'\b(input|output|inout)\s+(?:\[.*?\]\s+)?(\w+)', content)
                for m in pm:
                    self.v_ports[m.group(2)] = m.group(1)[0].upper()
                # Instances
                _VERILOG_KEYWORDS = {'module', 'function', 'task', 'input', 'output', 'inout', 'reg', 'wire', 'parameter'}
                im = re.finditer(r'(\w+)\s+(\w+)\s*\((.*?)\);', content, re.S)
                for m in im:
                    cell, inst, body = m.groups()
                    if cell.lower() in _VERILOG_KEYWORDS:
                        continue
                    self.v_raw_insts[inst] = cell
                    # Build net→instance from ALL .port(net) connections (not just .PAD)
                    for conn_m in re.finditer(r'\.\w+\s*\(\s*(\w+)\s*\)', body):
                        net = conn_m.group(1)
                        if net not in self.v_net_to_inst:
                            self.v_net_to_inst[net] = inst
                            self.v_insts[net] = cell
            except Exception as e:
                self.logger.warn(f"Error parsing Verilog {v_file}: {e}")
        if self.v_ports or self.v_raw_insts:
            net_conn = len(self.v_net_to_inst)
            self.logger.info(
                f"Verilog parsed: {len(self.v_ports)} ports, "
                f"{len(self.v_raw_insts)} instances"
                + (f", {net_conn} net-to-instance connections" if net_conn else " (no instance connections — using U_<signal> naming convention)")
            )

    def bridge_data(self):
        self.logger.info("Bridging data and re-indexing DIE_NUM with Dynamic Reference Update...")
        
        # 1. Capture original mapping and identify D1.xx references
        old_die_num_to_row = {}
        referencing_rows = []
        for row in self.data:
            # Skip special rows - treat as comment, output as-is
            if row['PKG_NUM'].upper() == 'INNER_BOND' or row['DIE_NUM'] == '-':
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
            if row['PKG_NUM'].upper() == 'INNER_BOND' or row['DIE_NUM'] == '-':
                continue
            if row['PKG_LOC'].upper() == 'L' and row['DIE_PIN_NAME'].upper() != 'NC' and row['DIE_NUM'] != '0':
                start_idx = i
                break

        if start_idx == -1:
            self.logger.warn("No L-side signal pin found, DIE_NUM reindexing skipped.")
        if start_idx != -1:
            ring_seq = self.data[start_idx:] + self.data[:start_idx]
            idx = 1
            orig_to_new = {}  # Map: original DIE_NUM -> new DIE_NUM (for duplicates)
            for row in ring_seq:
                # Skip special rows
                if row['PKG_NUM'].upper() == 'INNER_BOND' or row['DIE_NUM'] == '-':
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
        _skip_names = {'NC', 'DOWNBOND', 'POWERCUT', '-', ''}
        matched_signals = set()    # port_sn resolved to a real instance
        fallback_signals = set()   # port_sn with no matching instance
        no_port_signals = set()    # port_sn not found in verilog module ports
        no_inst_cells = set()      # (port_sn, zz) where zz not found in verilog instances

        for row in self.data:
            pname = row['DIE_PIN_NAME']
            pname_upper = pname.upper()
            if pname_upper in _skip_names or row['PKG_NUM'].upper() == 'INNER_BOND':
                continue

            has_pct = '%' in pname
            # sn  : last segment after % — used as cell-path / net for instance lookup
            sn = pname.split('%')[-1] if has_pct else pname
            if not sn: sn = pname
            # port_sn: first segment before % — corresponds to verilog module port name
            port_sn = pname.split('%')[0] if has_pct else pname

            p_mode = (row['DIRECTION'] in ('P', 'G') or has_pct or 'POWERCUT' in pname_upper)

            # Attempt to update IO_CELL_NAME if not already set or is a placeholder
            if row['IO_CELL_NAME'] in ('-', '', 'NOT_FOUND'):
                # Resolve instance: primary = .PAD(net) trace; fallback = U_{port} convention
                inst = self.v_net_to_inst.get(sn)
                if inst is None:
                    fallback = f"U_{sn}"
                    inst = fallback if fallback in self.v_raw_insts else None

                if p_mode:
                    cell = self.v_raw_insts.get(sn, self.v_insts.get(sn, 'NOT_FOUND'))
                    row['IO_CELL_NAME'] = cell
                    row['INST_NAME'] = inst if inst else sn
                else:
                    cell = self.v_insts.get(sn)
                    if cell is None and inst:
                        cell = self.v_raw_insts.get(inst, 'NOT_FOUND')
                    row['IO_CELL_NAME'] = cell if cell else 'NOT_FOUND'
                    row['INST_NAME'] = inst if inst else sn
                    if row['DIRECTION'] in ('-', 'UNKNOWN', ''):
                        row['DIRECTION'] = self.v_ports.get(port_sn, 'UNKNOWN')

                # Instance resolution tracking (all pin types)
                port_in_verilog = (not self.v_ports) or (port_sn in self.v_ports)
                if inst:
                    matched_signals.add(port_sn)
                elif port_in_verilog:
                    # Check 1 passed (port exists), check 2 failed (no instance trace)
                    fallback_signals.add(port_sn)
                # If port not in verilog, skip check 2 — will be caught by no_port_signals

            # --- Sanity checks (run regardless of IO_CELL_NAME state) ---
            if self.v_ports or self.v_raw_insts:
                # 1. port_sn must exist in verilog module ports (only for plain pins, not xx%yy%zz)
                if not has_pct and self.v_ports and port_sn not in self.v_ports:
                    no_port_signals.add((port_sn, row.get('_orig_die_num', row['DIE_NUM'])))

                # 2. For %C%/%IO% pins: top-level of zz must exist in verilog instances
                if has_pct and self.v_raw_insts:
                    top_inst = sn.split('/')[0]  # e.g. "U_AIP_TOP/U_X" → "U_AIP_TOP"
                    if top_inst not in self.v_raw_insts:
                        no_inst_cells.add((port_sn, sn, row.get('_orig_die_num', row['DIE_NUM'])))

        # --- Verilog Sanity Report ---
        if self.v_ports or self.v_raw_insts:
            total = len(matched_signals) + len(fallback_signals)
            self.logger.info(
                f"Verilog bridge: {len(matched_signals)}/{total} pins resolved to instances"
                + (f", {len(fallback_signals)} with no matching instance" if fallback_signals else "")
            )
            for sig in sorted(fallback_signals):
                die = next((r.get('_orig_die_num', r['DIE_NUM']) for r in self.data
                            if r['DIE_PIN_NAME'].split('%')[0] == sig or r['DIE_PIN_NAME'] == sig), '?')
                self.logger.warn(f"  No instance for '{sig}' (DIE_NUM={die})")

            if no_port_signals:
                self.logger.warn(
                    f"Verilog port mismatch: {len(no_port_signals)} DIE_PIN_NAME(s) "
                    f"not found in verilog module ports:"
                )
                for sig, die in sorted(no_port_signals):
                    self.logger.warn(f"  '{sig}' not in verilog ports (DIE_NUM={die})")

            if no_inst_cells:
                self.logger.warn(
                    f"Verilog instance mismatch: {len(no_inst_cells)} %C%/%IO% cell path(s) "
                    f"not found in verilog instances:"
                )
                for sig, zz, die in sorted(no_inst_cells):
                    self.logger.warn(
                        f"  '{sig}%...%{zz}' top-inst '{zz.split('/')[0]}' not in verilog (DIE_NUM={die})"
                    )

            # Verilog ports not referenced by any DIE_PIN_NAME in the pin list
            pinlist_port_sn = {
                (r['DIE_PIN_NAME'].split('%')[0] if '%' in r['DIE_PIN_NAME'] else r['DIE_PIN_NAME'])
                for r in self.data if r['DIE_PIN_NAME'].upper() not in _skip_names
            }
            unused_ports = sorted(set(self.v_ports) - pinlist_port_sn)
            if unused_ports:
                self.logger.warn(
                    f"Verilog ports not referenced in pin list ({len(unused_ports)}): "
                    + ', '.join(unused_ports)
                )

    def _parse_die_size(self):
        raw = self.header.get('DIE_SIZE')
        if not raw:
            self.die_size = None
            return
        m = re.match(r'\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*$', raw.strip())
        if not m:
            self.logger.warn(f"Invalid DIE_SIZE format: '{raw}'. Expected 'AxB' (um). Ignoring.")
            self.die_size = None
            return
        self.die_size = (float(m.group(1)), float(m.group(2)))
        self.logger.info(f"DIE_SIZE parsed: {self.die_size[0]}x{self.die_size[1]} um")

    def _extract_cell_from_pin_name(self):
        # PIN_NAME with %C% encoding: "VDD11%C%U_TOP/U_VDD11_APR0"
        # APR display uses the part before first %, IO_CELL_NAME comes from the part after last %
        for row in self.data:
            pname = row['DIE_PIN_NAME']
            if '%' not in pname:
                continue
            if row['IO_CELL_NAME'] not in ('-', ''):
                continue
            cell = pname.split('%')[-1]
            if cell:
                row['IO_CELL_NAME'] = cell

# --- PDF Generator Class ---
class PDFGen:
    def __init__(self, logger, parser, die2_info=None, die2_loc=None, die2_label="DIE2",
                 die3_info=None, die3_loc=None, die3_label="DIE3"):
        self.logger = logger
        self.parser = parser
        self.die2_info = die2_info
        self.die2_loc = die2_loc   # (x, y) tuple in um
        self.die2_label = die2_label
        # Overlay list for iteration in combined PDF
        self.overlays = []
        if die2_info:
            self.overlays.append({'info': die2_info, 'loc': die2_loc, 'label': die2_label, 'colors': DIE_OVERLAY_COLORS})
        if die3_info:
            self.overlays.append({'info': die3_info, 'loc': die3_loc, 'label': die3_label, 'colors': DIE_OVERLAY_COLORS})

    def _get_package_body_mm(self):
        # 1. PKG_SIZE header takes priority (unit: um, convert to mm for internal use)
        pkg_size_raw = self.parser.header.get('PKG_SIZE')
        if pkg_size_raw:
            m = re.match(r'\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*$', pkg_size_raw.strip())
            if m:
                body_x_um, body_y_um = float(m.group(1)), float(m.group(2))
                body_x, body_y = body_x_um / 1000, body_y_um / 1000
                die_size = self.parser.die_size
                if die_size:
                    max_die = max(die_size)
                    if max_die > max(body_x_um, body_y_um):
                        self.logger.warn(f"DIE_SIZE {die_size[0]}x{die_size[1]}um exceeds PKG_SIZE {body_x_um}x{body_y_um}um")
                return (body_x, body_y)
            else:
                self.logger.warn(f"Invalid PKG_SIZE format: '{pkg_size_raw}'. Expected 'AxB' (um). Ignoring.")

        # 2. Fall back to pin count lookup
        pkg_str = self.parser.header.get('PACKAGE', '')
        parts = pkg_str.split()
        if not parts:
            return None
        m = re.match(r'(\d+)', parts[0])
        if not m:
            return None
        pin_count = int(m.group(1))
        body_mm = QFN_BODY_SIZES.get(pin_count)
        if body_mm is None:
            return None
        die_size = self.parser.die_size
        if die_size:
            die_x_um, die_y_um = die_size
            body_um = body_mm * 1000
            max_die = max(die_x_um, die_y_um)
            if max_die > body_um:
                self.logger.warn(f"DIE_SIZE {die_x_um}x{die_y_um}um exceeds package body {int(body_mm*1000)}x{int(body_mm*1000)}um")
        return (body_mm, body_mm)

    def _compute_frame_dimensions(self, base_apr, base_pkg):
        body = self._get_package_body_mm()
        die_size = self.parser.die_size

        if body is None and die_size is None:
            return base_apr, base_apr, base_pkg, base_pkg

        if die_size:
            die_x, die_y = die_size
            ratio = die_x / die_y if die_y > 0 else 1.0
            if ratio >= 1.0:
                apr_x = base_apr
                apr_y = base_apr / ratio
            else:
                apr_x = base_apr * ratio
                apr_y = base_apr

            if body:
                body_um_x, body_um_y = body[0] * 1000, body[1] * 1000
                scale_x = body_um_x / die_x if die_x > 0 else 1.0
                scale_y = body_um_y / die_y if die_y > 0 else 1.0
                pkg_x = min(apr_x * scale_x, base_pkg)
                pkg_y = min(apr_y * scale_y, base_pkg)
            else:
                pkg_x = pkg_y = base_pkg
        else:
            apr_x = apr_y = base_apr
            pkg_x = pkg_y = base_pkg

        return apr_x, apr_y, pkg_x, pkg_y

    def _side_length(self, side, edge_x, edge_y):
        return edge_y if side in ('L', 'R') else edge_x

    def _get_pin_drawing_dims(self, frame_x, frame_y, mode='PKG'):
        """Return physical-scaled pin dimensions in points.

        Returns dict: pitch, pin_len, pin_width (or None), center_pad (or None).
        Falls back to legacy defaults when no QFN spec is available.
        """
        body = self._get_package_body_mm()
        if body is None:
            return {'pitch': None, 'pin_len': 25 if mode == 'PKG' else 15, 'pin_width': None, 'center_pad': None}

        # Get total pin count from PACKAGE header
        pkg_str = self.parser.header.get('PACKAGE', '')
        parts = pkg_str.split()
        try:
            total_pins = sum(int(p) for p in parts[1:5]) if len(parts) >= 5 else 0
        except (ValueError, IndexError):
            total_pins = 0

        spec = QFN_PHYSICAL_SPECS.get(total_pins)
        if spec:
            body_mm, pitch_mm, pw_mm, pl_mm, cp_mm = spec
            pts_per_mm = frame_x / (body_mm * 1000) if body_mm > 0 else 0.056
            return {
                'pitch': pitch_mm * 1000 * pts_per_mm,
                'pin_len': pl_mm * 1000 * pts_per_mm,
                'pin_width': pw_mm * 1000 * pts_per_mm,
                'center_pad': cp_mm * 1000 * pts_per_mm,
            }

        # Fallback: body known but pin count not in spec table
        return {'pitch': None, 'pin_len': 25 if mode == 'PKG' else 15, 'pin_width': None, 'center_pad': None}

    def generate_combined_pdf(self, filename):
        if not HAS_REPORTLAB:
            self.logger.error("ReportLab is not installed.")
            return
        self.logger.info("Generating Combined (PKG+APR) Diagram with Bonding Wires...")
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)
        cx, cy = width / 2, 265
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
        # Collect D1.xx rows for inner bond connections
        d1xx_rows = []

        for row in self.parser.data:
            p_loc = row['PKG_LOC'].upper()
            a_loc = row['DIE_LOC'].upper()
            pnum = row['PKG_NUM']
            pname = row['DIE_PIN_NAME'].upper()

            # PKG side (Uses current PIN_NUM order)
            # DOWNBOND should be included in PKG (even though DIE_NUM=0)
            pkg_pn = row.get('PKG_PIN_NAME', '-')
            if p_loc in pkg_data_by_side:
                if (pname not in ('DOWNBOND', 'NC') and pnum in ('0', '-', 'NC')) or 'POWERCUT' in pname: pass
                elif pname not in ('DOWNBOND', 'NC') and (not pkg_pn or pkg_pn == '-'): pass
                else:
                    if pnum not in seen_pnums:
                        pkg_data_by_side[p_loc].append(row)
                        seen_pnums.add(pnum)

            # APR side (Needs local reordering for the Ring)
            # Skip NC, DOWNBOND, and DIE_PAD_NUM='0' or '-' (no die pad)
            # Skip Inner_bond and PKG_NUM='-'
            # Skip duplicate DIE_NUM (only show one APR pin for multiple wires to same point)
            die_num = row['DIE_NUM']
            if pname not in ('NC', 'DOWNBOND') and die_num not in ('0', '-') and a_loc in apr_data_by_side:
                if row['PKG_NUM'].upper() == 'INNER_BOND':
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

            # Collect D1.xx rows for inner bond connections (both D1.xx and (D1.xx) formats)
            if pnum.startswith('D1.') or pnum.startswith('(D1.'):
                d1xx_rows.append(row)
        
        # Move early APR T pins to the end
        apr_data_by_side['T'].extend(apr_t_early)

        # Sort PKG pins by PKG_NUM for correct pin positioning
        def _pnum_key(r):
            try:
                return int(r['PKG_NUM'])
            except (ValueError, TypeError):
                return float('inf')
        for side in ('L', 'B', 'R', 'T'):
            pkg_data_by_side[side].sort(key=_pnum_key)

        edge_apr_x, edge_apr_y, edge_pkg_x, edge_pkg_y = self._compute_frame_dimensions(200, 350)
        c.setLineWidth(2)
        c.rect(cx - edge_pkg_x/2, cy - edge_pkg_y/2, edge_pkg_x, edge_pkg_y)
        pin_dims_pkg = self._get_pin_drawing_dims(edge_pkg_x, edge_pkg_y, 'PKG')
        if pin_dims_pkg.get('center_pad'):
            self._draw_center_pad(c, cx, cy, pin_dims_pkg['center_pad'])
        c.rect(cx - edge_apr_x/2, cy - edge_apr_y/2, edge_apr_x, edge_apr_y)

        pkg_coords, apr_coords = {}, {}
        pkg_edge = {'L': cx - edge_pkg_x/2, 'R': cx + edge_pkg_x/2, 'B': cy - edge_pkg_y/2, 'T': cy + edge_pkg_y/2}
        pkg_margin = 8
        # PKG pin boundary limits: APR label must not extend past PKG pin inner edge
        # L/B: limit = inner boundary toward frame edge (label extends left/down toward it)
        # R/T: limit = inner boundary toward center (label extends right/up toward it)
        pkg_pin_len = pin_dims_pkg.get('pin_len', 25) if pin_dims_pkg else 25
        apr_lim = {
            'L': pkg_edge['L'] + pkg_pin_len + pkg_margin,
            'R': pkg_edge['R'] - pkg_pin_len - pkg_margin,
            'B': pkg_edge['B'] + pkg_pin_len + pkg_margin,
            'T': min(pkg_edge['T'] - pkg_pin_len - pkg_margin, 510),
        }

        # Use max pin count for uniform font size across all 4 sides (PKG + APR)
        max_cnt = max(l_cnt, b_cnt, r_cnt, t_cnt)
        # APR pin size: 100um physical, scaled to frame
        die_size = self.parser.die_size
        if die_size:
            apr_pin_sz = 100.0 * edge_apr_x / max(die_size[0], die_size[1])
        else:
            apr_pin_sz = 6
        for side in ('L', 'B', 'R', 'T'):
            pkg_len = self._side_length(side, edge_pkg_x, edge_pkg_y)
            apr_len = self._side_length(side, edge_apr_x, edge_apr_y)
            p_coords = self._draw_side_boxes(c, side, pkg_data_by_side[side], cx, cy, pkg_len, getattr(self, f"_{side}_pos")(cx, cy, edge_pkg_x, edge_pkg_y), max_cnt, 'PKG', label_inside=False, pin_dims=pin_dims_pkg, pin_inside=True)
            pkg_coords.update(p_coords)
            a_coords = self._draw_side_boxes(c, side, apr_data_by_side[side], cx, cy, apr_len, getattr(self, f"_{side}_pos")(cx, cy, edge_apr_x, edge_apr_y), max_cnt, 'APR', label_inside=False, max_label_extent=apr_lim[side], hollow_pg=True, skip_start_dot=True, pin_inside=True, apr_pin_size=apr_pin_sz)
            apr_coords.update(a_coords)

        c.setLineWidth(0.3)
        for row in self.parser.data:
            pname = row['DIE_PIN_NAME'].upper()
            # Skip NC, DOWNBOND, and DIE_PAD_NUM='0' for bonding wires (no APR pin exists)
            if pname in ('NC', 'DOWNBOND') or row['DIE_NUM'] in ('0', '-'): continue
            p_pt = pkg_coords.get(row['PKG_NUM'])
            a_pt = apr_coords.get(row['DIE_NUM'])
            if p_pt and a_pt:
                # Determine which side based on PIN_NUM location (with ring offset)
                side = self.parser._get_ring_side(row['PKG_NUM'])

                # PKG pin center: pin_inside=True, pin extends inward from frame edge
                p_cx, p_cy = p_pt['pt']
                p_bw, p_bh = p_pt['bw'], p_pt['bh']
                p_side = p_pt['side']
                if p_side == 'L':
                    wire_start = (p_cx + p_bw/2, p_cy)
                elif p_side == 'R':
                    wire_start = (p_cx - p_bw/2, p_cy)
                elif p_side == 'B':
                    wire_start = (p_cx, p_cy + p_bh/2)
                elif p_side == 'T':
                    wire_start = (p_cx, p_cy - p_bh/2)
                else:
                    wire_start = p_pt['pt']

                a_side = a_pt['side']
                a_wedge = a_pt['pt']
                a_bw = a_pt['bw']
                a_bh = a_pt['bh']
                # APR pin center: pin_inside=True means pin extends inward from frame edge
                # 'pt' is at frame edge; actual center is box_len/2 inward
                pin_cx, pin_cy = a_wedge
                if a_side == 'L':
                    wire_end = (pin_cx + a_bw/2, pin_cy)
                elif a_side == 'R':
                    wire_end = (pin_cx - a_bw/2, pin_cy)
                elif a_side == 'B':
                    wire_end = (pin_cx, pin_cy + a_bh/2)
                elif a_side == 'T':
                    wire_end = (pin_cx, pin_cy - a_bh/2)
                else:
                    wire_end = a_wedge

                dir_color = colors.grey
                if row['DIRECTION'] == 'P': dir_color = colors.red
                elif row['DIRECTION'] == 'G': dir_color = colors.blue
                c.setStrokeColor(dir_color); c.line(wire_start[0], wire_start[1], wire_end[0], wire_end[1])

                c.setFillColor(dir_color)
                c.circle(wire_start[0], wire_start[1], 1.5, stroke=0, fill=1)
                c.circle(wire_end[0], wire_end[1], 1.5, stroke=0, fill=1)

        # Draw inner bond red lines for D1.xx connections
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
                xx = pnum_clean.split('.')[1]
                # D1.xx, DIE_NUM=yy means xx -> yy (both with and without parentheses)
                source, dest = xx, die_yy
                key = (source, dest)
                if key not in direction_map:
                    direction_map[key] = []
                direction_map[key].append(row)

            # Check for asymmetric connections
            for (a, b), rows in direction_map.items():
                reverse_key = (b, a)
                if reverse_key not in direction_map:
                    # Asymmetric: a->b exists but b->a missing
                    self.logger.error(f"Inner Bond ASYMMETRIC: {a}->{b} exists but {b}->{a} missing!")

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

        # Draw ground symbols with anchor-dot style
        entries = {}  # coord_key -> count

        # Ground pins (PKG_NUM=0, DIRECTION=G)
        for row in self.parser.data:
            if row['PKG_NUM'] != '0' or row['DIRECTION'] != 'G':
                continue
            die_num = row['DIE_NUM']
            if die_num in ('0', '-', ''):
                continue
            entries[die_num] = entries.get(die_num, 0) + 1

        for coord_key, count in entries.items():
            apr_pin = apr_coords.get(coord_key)
            if not apr_pin:
                continue

            pt = apr_pin['pt']
            bw = apr_pin['bw']
            bh = apr_pin['bh']
            side = apr_pin['side']

            # pin_inside=True: pin extends inward, center is at pt + half-dimension
            if side == 'L':
                cx_c, cy_c = pt[0] + bw / 2, pt[1]
            elif side == 'R':
                cx_c, cy_c = pt[0] - bw / 2, pt[1]
            elif side == 'B':
                cx_c, cy_c = pt[0], pt[1] + bh / 2
            elif side == 'T':
                cx_c, cy_c = pt[0], pt[1] - bh / 2
            else:
                continue

            for i in range(count):
                self._draw_ground_symbol(c, cx_c, cy_c, side, count, i)

            self.logger.info(f"  Ground/DB: key={coord_key}, count={count}")

        # Compute unified pad size and label font from all overlays (use smallest)
        die1_size = self.parser.die_size
        if die1_size:
            die1_max = max(die1_size)
            scale = edge_apr_x / die1_max
        else:
            scale = edge_apr_x / 1000
        unified_pad_sz = None
        unified_fn_name = None
        unified_fn_size = None
        for overlay in self.overlays:
            pads = overlay['info'].get('pads', [])
            sz = self._compute_optimal_pad_size(pads, scale)
            if unified_pad_sz is None or sz < unified_pad_sz:
                unified_pad_sz = sz
            # Label font: need frame width in pts
            info = overlay['info']
            od_w, od_h = info.get('die_size', (1000, 1000))
            rot = info.get('rotation', 0)
            if rot in (90, 270):
                fw_pts = od_h * scale
            else:
                fw_pts = od_w * scale
            name_s = info.get('name', overlay['label'])
            size_s = f"{int(od_w)}x{int(od_h)} um"
            fn, fs = self._compute_label_font_size(name_s, size_s, fw_pts)
            if unified_fn_name is None or fn < unified_fn_name:
                unified_fn_name = fn
            if unified_fn_size is None or fs < unified_fn_size:
                unified_fn_size = fs
        for overlay in self.overlays:
            self._draw_die_overlay(c, cx, cy, edge_apr_x, edge_apr_y, die1_size,
                                   overlay['info'], overlay['loc'], overlay['label'],
                                   overlay['colors'], apr_coords,
                                   pad_sz=unified_pad_sz,
                                   label_font_name=unified_fn_name,
                                   label_font_size=unified_fn_size)
        self._draw_scale_bar(c, edge_pkg_x, edge_pkg_y, 'COMBINED', width)
        self._draw_timestamp(c)
        c.save()

    def generate_apr_pdf(self, filename):
        if not HAS_REPORTLAB: return
        self.logger.info(f"Generating APR Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4)); width, height = landscape(A4)
        cx, cy = width/2, 255; self._draw_header(c, "APR PIN DIAGRAM", width, height)
        edge_x, edge_y = self._compute_frame_dimensions(280, 280)[:2]
        c.setLineWidth(2); c.rect(cx - edge_x/2, cy - edge_y/2, edge_x, edge_y)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        t_early = []
        found_l = False
        seen_die_nums = set()  # For deduplication: skip duplicate DIE_NUM
        for row in self.parser.data:
            pname = row['DIE_PIN_NAME'].upper()
            # Skip NC, DOWNBOND, and DIE_PAD_NUM='0' for APR (no die pad to show)
            if pname in ('NC', 'DOWNBOND') or row['DIE_NUM'] in ('0', '-'): continue
            # Skip Inner_bond and PKG_NUM='-'
            if row['PKG_NUM'].upper() == 'INNER_BOND': continue
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
        self._draw_center_info(c, cx, cy, min(edge_x, edge_y), l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        apr_edge = {'L': cx - edge_x/2, 'R': cx + edge_x/2, 'B': cy - edge_y/2, 'T': cy + edge_y/2}
        header_bottom = 510
        # For APR, use max pin count to ensure uniform font size across all 4 sides
        max_cnt = max(l_cnt, b_cnt, r_cnt, t_cnt)
        # APR pin size: 50um physical, scaled to frame
        die_size = self.parser.die_size
        if die_size:
            apr_pin_sz = 100.0 * edge_x / max(die_size[0], die_size[1])
        else:
            apr_pin_sz = 6
        apr_coords_apr = {}
        for side in ('L', 'B', 'R', 'T'):
            limit = apr_edge[side]
            if side == 'T': limit = header_bottom
            side_len = self._side_length(side, edge_x, edge_y)
            a_coords = self._draw_side_boxes(c, side, data_by_side[side], cx, cy, side_len, getattr(self, f"_{side}_pos")(cx, cy, edge_x, edge_y), max_cnt, 'APR', label_inside=False, max_label_extent=limit, allow_overflow=True, pin_inside=True, apr_pin_size=apr_pin_sz)
            apr_coords_apr.update(a_coords)
        self._draw_scale_bar(c, edge_x, edge_y, 'APR', width)
        self._draw_timestamp(c)
        c.save()

    def generate_pkg_pdf(self, filename):
        if not HAS_REPORTLAB: return
        self.logger.info(f"Generating PKG Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4)); width, height = landscape(A4)
        cx, cy = width/2, 255; self._draw_header(c, "PACKAGE PIN DIAGRAM", width, height)
        _, _, edge_x, edge_y = self._compute_frame_dimensions(280, 280)
        c.setLineWidth(2); c.rect(cx - edge_x/2, cy - edge_y/2, edge_x, edge_y)
        pin_dims = self._get_pin_drawing_dims(edge_x, edge_y, 'PKG')
        if pin_dims.get('center_pad'):
            self._draw_center_pad(c, cx, cy, pin_dims['center_pad'])
        pkg_data = {}; order = []
        for row in self.parser.data:
            pnum = row['PKG_NUM']
            pname = row['DIE_PIN_NAME'].upper()
            pkg_pn = row.get('PKG_PIN_NAME', '-')
            # Same rules as Combined PDF PKG side
            if (pname not in ('DOWNBOND', 'NC') and pnum in ('0', '-', 'NC')) or 'POWERCUT' in pname: continue
            if pname not in ('DOWNBOND', 'NC') and (not pkg_pn or pkg_pn == '-'): continue
            if pnum not in pkg_data: pkg_data[pnum] = row.copy(); order.append(pnum)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for pnum in order:
            loc = pkg_data[pnum]['PKG_LOC'].upper()
            pname = pkg_data[pnum]['DIE_PIN_NAME'].upper()
            # For DOWNBOND or pins with invalid LOCATION, infer side from PIN_NUM
            if pname == 'DOWNBOND' or loc not in data_by_side:
                inferred_side = self.parser._get_ring_side(pnum)
                if inferred_side:
                    data_by_side[inferred_side].append(pkg_data[pnum])
            elif loc in data_by_side:
                data_by_side[loc].append(pkg_data[pnum])
        # Sort each side by PKG_NUM (numeric order) for correct pin positioning
        def _pnum_key(r):
            try:
                return int(r['PKG_NUM'])
            except (ValueError, TypeError):
                return float('inf')
        for side in ('L', 'B', 'R', 'T'):
            data_by_side[side].sort(key=_pnum_key)
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)
        info_cy = cy + (pin_dims['center_pad'] / 2 + 10 if pin_dims.get('center_pad') else 0)
        self._draw_center_info(c, cx, info_cy, min(edge_x, edge_y), l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        pkg_edge = {'L': cx - edge_x/2, 'R': cx + edge_x/2, 'B': cy - edge_y/2, 'T': cy + edge_y/2}
        header_bottom = 510
        # For PKG, use max pin count to ensure uniform font size across all 4 sides
        max_cnt = max(l_cnt, b_cnt, r_cnt, t_cnt)
        for side in ('L', 'B', 'R', 'T'):
            limit = pkg_edge[side]
            if side == 'T': limit = header_bottom
            side_len = self._side_length(side, edge_x, edge_y)
            self._draw_side_boxes(c, side, data_by_side[side], cx, cy, side_len, getattr(self, f"_{side}_pos")(cx, cy, edge_x, edge_y), max_cnt, 'PKG', label_inside=False, max_label_extent=limit, allow_overflow=True, pin_dims=pin_dims, pin_inside=True)
        self._draw_scale_bar(c, edge_x, edge_y, 'PKG', width)
        self._draw_timestamp(c)
        c.save()

    def _L_pos(self, cx, cy, edge_x, edge_y=None): return (cx - edge_x/2, cy)
    def _B_pos(self, cx, cy, edge_x, edge_y=None): return (cx, cy - (edge_y or edge_x)/2)
    def _R_pos(self, cx, cy, edge_x, edge_y=None): return (cx + edge_x/2, cy)
    def _T_pos(self, cx, cy, edge_x, edge_y=None): return (cx, cy + (edge_y or edge_x)/2)

    def _draw_side_boxes(self, c, side, pins, cx, cy, length, b_pos, total, mode, label_inside=False, max_label_extent=None, allow_overflow=False, hollow_pg=False, skip_start_dot=False, pin_dims=None, pin_inside=False, apr_pin_size=None):
        bx, by = b_pos; coords = {}
        if not pins: return coords
        actual_cnt = len(pins); calc_total = max(actual_cnt, total)
        # Use physical pitch for step when available, center pins on side for proper corner gaps
        if pin_dims and pin_dims.get('pitch') is not None:
            step = pin_dims['pitch']
            margin = (length - (actual_cnt - 1) * step) / 2
            # Ensure corner pins have enough space at frame corners (JEDEC MO-220)
            # Pull corner pins inward by 0.5×pitch beyond natural centering
            if pin_dims.get('pitch') is not None:
                min_margin = pin_dims['pitch'] * 1.5
                margin = max(margin, min_margin)
                # Recalculate step to keep pins centered with new margin
                step = (length - 2 * margin) / max(1, actual_cnt - 1)
            font_step = step
        else:
            step = length / (calc_total + 1)
            margin = step
            # Corner pin pullback: ensure pins don't touch at frame corners
            min_margin = step * 1.5
            margin = max(margin, min_margin)
            step = (length - 2 * margin) / max(1, actual_cnt - 1)
            font_step = step
        font_size = max(2, min(font_step * 0.9, 8))
        if mode == 'PKG': font_size = min(font_size + 1, 10)
        if pin_dims and pin_dims.get('pin_width') is not None:
            box_thickness = min(pin_dims['pin_width'], step * 0.9)
            box_len = pin_dims['pin_len']
        else:
            box_thickness = max(1, min(step * 0.8, 6))
            box_len = (apr_pin_size or 6) if mode == 'APR' else 25
        for idx, pin in enumerate(pins, 1):
            pname = pin['DIE_PIN_NAME']
            if mode == 'PKG':
                pkg_pin = pin.get('PKG_PIN_NAME', '-')
                display_name = pkg_pin if pkg_pin and pkg_pin != '-' else pname
            else:
                display_name = pname.split('%', 1)[0] if '%' in pname else pname
            px, py = 0, 0; bw, bh = 0, 0
            if side == 'L':
                bw, bh = box_len, box_thickness
                px = bx if pin_inside else (bx - (0 if label_inside else bw))
                py = (by + length/2) - margin - ((idx - 1) * step) - (bh/2)
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (bx, py + bh/2), 'bw': bw, 'bh': bh, 'side': side}
            elif side == 'B':
                bw, bh = box_thickness, box_len
                px = (bx - length/2) + margin + ((idx - 1) * step) - (bw/2)
                py = by if pin_inside else (by - (0 if label_inside else bh))
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (px + bw/2, by), 'bw': bw, 'bh': bh, 'side': side}
            elif side == 'R':
                bw, bh = box_len, box_thickness
                px = bx - bw if pin_inside else (bx - (bw if label_inside else 0))
                py = (by - length/2) + margin + ((idx - 1) * step) - (bh/2)
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (bx, py + bh/2), 'bw': bw, 'bh': bh, 'side': side}
            elif side == 'T':
                bw, bh = box_thickness, box_len
                px = (bx + length/2) - margin - ((idx - 1) * step) - (bw/2)
                py = by - bh if pin_inside else (by - (bh if label_inside else 0))
                coords[pin['PKG_NUM'] if mode == 'PKG' else pin['DIE_NUM']] = {'pt': (px + bw/2, by), 'bw': bw, 'bh': bh, 'side': side}
            c.setLineWidth(0.5); c.setStrokeColor(colors.black); direction = pin['DIRECTION']
            if 'POWERCUT' in pname.upper(): c.setFillColor(colors.black); c.rect(px, py, bw, bh, fill=1)
            elif pname.upper() == 'NC': c.setFillColor(colors.black); c.rect(px, py, bw, bh, fill=1)
            elif direction == 'P': c.setStrokeColor(colors.red); c.setLineWidth(1.0); c.rect(px, py, bw, bh, fill=0)
            elif direction == 'G': c.setStrokeColor(colors.blue); c.setLineWidth(1.0); c.rect(px, py, bw, bh, fill=0)
            else: c.rect(px, py, bw, bh, fill=0)
            c.setFillColor(colors.black)
            small_font = font_size
            if max_label_extent is not None and not allow_overflow:
                name_len = len(display_name)
                header_bottom = 510 if side == 'T' else None
                limit = max_label_extent
                if side == 'T' and header_bottom is not None:
                    limit = min(limit, header_bottom) if limit else header_bottom

                if side == 'L':
                    available_width = px - 4 - limit
                elif side == 'R':
                    available_width = limit - (px + bw + 4)
                elif side == 'B':
                    available_width = (py - 4) - limit
                elif side == 'T':
                    available_width = limit - (py + bh + 4)

                for try_font in range(int(font_size), 1, -1):
                    char_width = try_font * 0.6
                    if name_len * char_width <= available_width:
                        small_font = try_font
                        break
                    small_font = max(2, try_font)
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
                if draw_dot and not is_combined_inner_apr and not skip_start_dot:
                    dot_r = 6
                    # Place at intersection of L-side pin center X and T-side pin center Y
                    # Compute frame edges from b_pos and length
                    L_edge = b_pos[0]  # L-side X
                    T_edge = cy + length / 2  # T-side Y (length = edge_y for L side)
                    # Pin center offset: half pin dimension inward from frame edge
                    if pin_inside:
                        dot_x = L_edge + bw / 2
                        dot_y = T_edge - bh
                    else:
                        dot_x = L_edge
                        dot_y = T_edge
                    c.setFillColor(colors.black)
                    c.circle(dot_x, dot_y, dot_r, stroke=0, fill=1)

                # 2. Draw Numbering (1, 5, 10...)
                if n_int == 1 or n_int % 5 == 0:
                    c.setFont("Helvetica", font_size)
                    c.setFillColor(colors.black)
                    # APR pin_inside: number shifts past pin shape to avoid overlap
                    n_off = (bw if side in ('L', 'R') else bh) if (mode == 'APR' and pin_inside) else 0
                    if side == 'L': c.drawString(bx + 2 + n_off, py + (bh/2) - (font_size/2), num_str)
                    elif side == 'R': c.drawRightString(bx - 2 - n_off, py + (bh/2) - (font_size/2), num_str)
                    elif side == 'T': c.drawCentredString(px + bw/2, by - font_size - n_off, num_str)
                    elif side == 'B': c.drawCentredString(px + bw/2, by + 2 + n_off, num_str)
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
            c.rect(x, y - box_thickness/2, box_len, box_thickness, fill=0, stroke=1)
            c.circle(x + box_len/2, y, 1.5, stroke=0, fill=1)
        elif side == 'R':
            c.rect(x - box_len, y - box_thickness/2, box_len, box_thickness, fill=0, stroke=1)
            c.circle(x - box_len/2, y, 1.5, stroke=0, fill=1)
        elif side == 'B':
            width = box_len * 0.8
            c.rect(x - width/2, y, width, box_thickness, fill=0, stroke=1)
            c.circle(x, y + box_thickness/2, 1.5, stroke=0, fill=1)
        elif side == 'T':
            width = box_len * 0.8
            c.rect(x - width/2, y - box_thickness, width, box_thickness, fill=0, stroke=1)
            c.circle(x, y - box_thickness/2, 1.5, stroke=0, fill=1)

    def _draw_ground_symbol(self, c, cx, cy, side, count, idx):
        """Draw anchor-dot ground symbol: dot at pin center -> short wire -> ground symbol.

        Args:
            c: PDF canvas
            cx, cy: Center of the APR pin shape (anchor point)
            side: Which side (L/B/R/T) to determine outward direction
            count: Total number of ground wires for this pin
            idx: Which wire (0-based) for offset calculation
        """
        offset = (idx - (count - 1) / 2) * 2
        short_len = 7
        stem_len = 4

        # Offset along the pin's long axis
        if side in ('L', 'R'):
            ax, ay = cx, cy + offset  # vertical spread
        else:
            ax, ay = cx + offset, cy  # horizontal spread

        light_blue = colors.Color(0, 0, 0.8, 0.35)
        c.setStrokeColor(light_blue)
        c.setFillColor(light_blue)
        c.setLineWidth(1.0)

        # Anchor dot
        c.circle(ax, ay, 1.5, stroke=0, fill=1)

        if side == 'L':
            end_x, end_y = ax - short_len, ay
            c.line(ax, ay, end_x, end_y)
            c.line(end_x, end_y, end_x - stem_len, end_y)
            c.line(end_x - stem_len, end_y - 3, end_x - stem_len, end_y + 3)
            c.line(end_x - stem_len + 2, end_y - 2, end_x - stem_len + 2, end_y + 2)
        elif side == 'R':
            end_x, end_y = ax + short_len, ay
            c.line(ax, ay, end_x, end_y)
            c.line(end_x, end_y, end_x + stem_len, end_y)
            c.line(end_x + stem_len, end_y - 3, end_x + stem_len, end_y + 3)
            c.line(end_x + stem_len - 2, end_y - 2, end_x + stem_len - 2, end_y + 2)
        elif side == 'B':
            end_x, end_y = ax, ay - short_len
            c.line(ax, ay, end_x, end_y)
            c.line(end_x, end_y, end_x, end_y - stem_len)
            c.line(end_x - 3, end_y - stem_len, end_x + 3, end_y - stem_len)
            c.line(end_x - 2, end_y - stem_len + 2, end_x + 2, end_y - stem_len + 2)
        elif side == 'T':
            end_x, end_y = ax, ay + short_len
            c.line(ax, ay, end_x, end_y)
            c.line(end_x, end_y, end_x, end_y + stem_len)
            c.line(end_x - 3, end_y + stem_len, end_x + 3, end_y + stem_len)
            c.line(end_x - 2, end_y + stem_len - 2, end_x + 2, end_y + stem_len - 2)

    def _draw_header(self, c, title, width, height):
        c.setLineWidth(1); c.setStrokeColor(colors.black); c.rect(50, height - 85, width - 100, 65)
        c.setFont("Helvetica-Bold", 18); c.drawCentredString(width/2, height - 45, title)
        c.setFont("Helvetica", 10); h = self.parser.header
        proj = h.get('PRODUCTION NO.', h.get('PRODUCTION NO', 'N/A'))
        pkg = h.get('PACKAGE', 'N/A'); ver = h.get('VERSION', 'N/A')
        die_size = h.get('DIE_SIZE', '')
        body = self._get_package_body_mm()
        pkg_size_str = f" ({int(body[0]*1000)}x{int(body[1]*1000)} um)" if body else ''
        die_str = f"  ,  Die: {die_size} um" if die_size else ''
        c.drawString(60, height - 65, f"Project: {proj}"); c.drawCentredString(width/2, height - 65, f"Package: {pkg}{pkg_size_str}{die_str}"); c.drawRightString(width - 60, height - 65, f"Version: {ver}")

    def _draw_center_info(self, c, cx, cy, edge, l, b, r, t, data):
        f_max = max(l, b, r, t)
        for s in ('L', 'B', 'R', 'T'): f_max = max(f_max, len(data.get(s, [])))
        step = edge / (f_max + 1); font_size = max(2, min(step * 0.9, 7)); spacing = font_size * 1.5
        c.saveState()
        c.setFont("Helvetica", font_size)
        c.setFillColor(colors.black)
        c.setFillAlpha(1.0)
        h = self.parser.header
        c.drawCentredString(cx, cy + spacing, f"Project: {h.get('PRODUCTION NO.', h.get('PRODUCTION NO', 'N/A'))}")
        c.drawCentredString(cx, cy, f"Package: {h.get('PACKAGE', 'N/A')}")
        c.drawCentredString(cx, cy - spacing, f"Version: {h.get('VERSION', 'N/A')}")
        c.restoreState()

    def _draw_center_pad(self, c, cx, cy, pad_size_pts, label="GND"):
        """Draw a dashed rectangle for the center exposed/thermal pad."""
        half = pad_size_pts / 2
        light = colors.Color(0.55, 0.55, 0.55, 0.3)
        c.saveState()
        c.setDash([3, 3])
        c.setLineWidth(0.8)
        c.setStrokeColor(light)
        c.rect(cx - half, cy - half, pad_size_pts, pad_size_pts, fill=0, stroke=1)
        c.setDash([])
        c.restoreState()
        font_size = max(5, min(pad_size_pts * 0.12, 12))
        c.setFont("Helvetica", font_size)
        c.setFillColor(light)
        c.drawCentredString(cx, cy - font_size / 2, label)

    def _draw_corner_indicators(self, c, cx, cy, edge_x, edge_y, arm_length=8):
        """Draw L-shaped corner indicators at all 4 corners of the PKG frame."""
        half_x, half_y = edge_x / 2, edge_y / 2
        corners = [
            (cx - half_x, cy + half_y, arm_length, arm_length),    # TL: right + down
            (cx + half_x, cy + half_y, -arm_length, arm_length),   # TR: left + down
            (cx - half_x, cy - half_y, arm_length, -arm_length),   # BL: right + up
            (cx + half_x, cy - half_y, -arm_length, -arm_length),  # BR: left + up
        ]
        for i, (x, y, dx, dy) in enumerate(corners):
            c.setLineWidth(1.5 if i == 0 else 1.0)
            c.setStrokeColor(colors.black)
            c.line(x, y, x + dx, y)
            c.line(x, y, x, y + dy)

    def _draw_scale_bar(self, c, frame_x, frame_y, mode, page_width):
        """Draw a scale bar at bottom-right showing physical size reference.
        mode: 'PKG', 'APR', or 'COMBINED'
        """
        body = self._get_package_body_mm()
        die_size = self.parser.die_size

        if body is None and die_size is None:
            return

        # --- Compute scale (pts per um) ---
        if mode == 'APR':
            if die_size:
                max_dim = max(die_size)
                scale = frame_x / max_dim if max_dim > 0 else None
            elif body:
                scale = frame_x / (body[0] * 1000)
            else:
                return
        elif mode == 'PKG':
            if body:
                scale = frame_x / (body[0] * 1000)
            else:
                return
        else:  # COMBINED
            if body:
                scale = frame_x / (body[0] * 1000)
            else:
                return

        # --- Choose bar length (round physical distance) ---
        if scale <= 0:
            return
        candidates_um = [500, 1000, 2000, 5000, 10000]
        bar_len = None
        for um_val in candidates_um:
            pts = um_val * scale
            if 30 <= pts <= 120:
                bar_len = pts
                bar_um = um_val
                break
        if bar_len is None:
            bar_len = 1000 * scale
            bar_um = 1000

        # --- Position: bottom-right corner ---
        rx = page_width - 60
        ry = 30

        # --- Draw scale bar ---
        c.setStrokeColor(colors.black); c.setLineWidth(0.8); c.setFillColor(colors.black)
        c.line(rx - bar_len, ry, rx, ry)
        c.line(rx - bar_len, ry - 3, rx - bar_len, ry + 3)
        c.line(rx, ry - 3, rx, ry + 3)
        c.setFont("Helvetica", 7)
        c.drawCentredString(rx - bar_len / 2, ry + 5, f"{bar_um:g} um")

        # --- Physical size annotation ---
        info_y = ry - 10
        c.setFont("Helvetica", 6)
        if body:
            c.drawRightString(rx, info_y, f"PKG: {int(body[0]*1000)}x{int(body[1]*1000)} um")
            info_y -= 8
        if die_size:
            c.drawRightString(rx, info_y, f"Die: {int(die_size[0])}x{int(die_size[1])} um")

    def _draw_timestamp(self, c):
        """Draw generation timestamp and tool version at bottom-left corner."""
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.black)
        c.drawString(40, 30, ts)
        c.drawString(40, 21, f"ft_pad_assign : {VERSION}")

    @staticmethod
    def _compute_optimal_pad_size(pads, scale):
        """Compute optimal pad box size from minimum adjacent pad spacing."""
        if len(pads) < 2:
            return 4 * scale * 0.6
        min_dist = float('inf')
        for i in range(len(pads)):
            for j in range(i + 1, len(pads)):
                dx = abs(pads[i]['x'] - pads[j]['x'])
                dy = abs(pads[i]['y'] - pads[j]['y'])
                if dx < 20 or dy < 20:
                    dist = (dx**2 + dy**2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
        if min_dist < float('inf'):
            return max(min_dist * scale * 0.6, 2)
        return 4 * scale * 0.6

    @staticmethod
    def _compute_label_font_size(name_str, size_str, draw_w_pts):
        """Compute max font size so name and size lines fit within frame width."""
        # Helvetica-Bold char width ~0.65 * font_sz, regular ~0.55 * font_sz
        max_name_w = max(len(name_str) * 0.65, 1)
        max_size_w = max(len(size_str) * 0.55, 1)
        font_name = min(7, int(draw_w_pts / max_name_w * 0.85))
        font_size = min(6, int(draw_w_pts / max_size_w * 0.85))
        return max(font_name, 3), max(font_size, 3)

    def _draw_die_overlay(self, c, cx, cy, edge_apr_x, edge_apr_y, die1_size,
                          die_info, die_loc, die_label, color_scheme, apr_coords=None,
                          pad_sz=None, label_font_name=None, label_font_size=None):
        """Draw a die overlay frame, pads, and connection wires.

        Args:
            c: ReportLab canvas
            cx, cy: Center of DIE1 frame in PDF points
            edge_apr_x, edge_apr_y: DIE1 frame dimensions in points
            die1_size: DIE1 die_size tuple (w, h) in um, or None
            die_info: parsed die dict (from parse_die_csv)
            die_loc: (x, y) tuple in um
            die_label: display label string
            color_scheme: dict with 'frame', 'signal', 'wire_power', 'wire_signal' colors
            apr_coords: dict of DIE1 APR pad positions keyed by DIE_NUM (for connection wires)
        """
        die_size = die_info.get('die_size')
        pads = die_info.get('pads', [])
        if not die_size:
            self.logger.error(f"{die_label}: missing DIE_SIZE in spec file.")
            return

        loc_x, loc_y = die_loc
        d_w, d_h = die_size
        rotation = die_info.get('rotation', 0)
        flip_x = die_info.get('flip_x', False)

        # Compute scale: same as DIE1
        if die1_size:
            die1_x, die1_y = die1_size
            scale = edge_apr_x / max(die1_x, die1_y)
        else:
            scale = edge_apr_x / max(d_w, d_h)

        # Convert loc to DIE1-center-relative coords
        # CSV: loc is relative to DIE1 bottom-left (0,0) → subtract half of DIE1
        # MD:  loc is already relative to DIE1 center → no conversion
        if die_info.get('loc_relative') == 'bottom_left' and die1_size:
            loc_x = loc_x - die1_size[0] / 2
            loc_y = loc_y - die1_size[1] / 2

        # Frame dimensions: swap w/h for R90/R270
        if rotation in (90, 270):
            draw_w, draw_h = d_h, d_w
        else:
            draw_w, draw_h = d_w, d_h
        draw_w_pts = draw_w * scale
        draw_h_pts = draw_h * scale

        # Die center stays at loc + half of original size (center doesn't move)
        die_cx = cx + (loc_x + d_w / 2) * scale
        die_cy = cy + (loc_y + d_h / 2) * scale

        # Draw frame (30% transparent)
        frame_color = color_scheme['frame']
        c.saveState()
        c.setStrokeColor(colors.HexColor(frame_color) if isinstance(frame_color, str) else frame_color)
        c.setStrokeAlpha(0.3)
        c.setLineWidth(1.5)
        c.rect(die_cx - draw_w_pts / 2, die_cy - draw_h_pts / 2, draw_w_pts, draw_h_pts, fill=0, stroke=1)
        c.restoreState()

        # Draw label at center — unified font sizes
        name_str = die_info.get('name', die_label)
        size_str = f"{int(d_w)}x{int(d_h)} um"
        fn_name = label_font_name if label_font_name else 7
        fn_size = label_font_size if label_font_size else 6
        c.saveState()
        c.setFillColor(colors.HexColor(frame_color) if isinstance(frame_color, str) else frame_color)
        c.setFont("Helvetica-Bold", fn_name)
        c.drawCentredString(die_cx, die_cy + fn_size * 0.7, name_str)
        c.setFont("Helvetica", fn_size)
        c.drawCentredString(die_cx, die_cy - fn_size * 0.9, size_str)
        c.restoreState()

        # Use provided pad_sz or compute from min spacing
        if pad_sz is None:
            pad_sz = self._compute_optimal_pad_size(pads, scale)

        font_sz = 5  # unified font size for all overlay pad labels
        gap = 2  # gap from frame edge in points

        # Frame edges in PDF coords
        frame_left = die_cx - draw_w_pts / 2
        frame_right = die_cx + draw_w_pts / 2
        frame_bottom = die_cy - draw_h_pts / 2
        frame_top = die_cy + draw_h_pts / 2

        # Draw location at bottom-left corner INSIDE frame
        c.saveState()
        c.setFont("Helvetica", font_sz)
        c.setFillColor(colors.black)
        c.setFillAlpha(0.5)
        orig_loc = die_info.get('loc', (0, 0))
        c.drawString(frame_left + gap + 1, frame_bottom + gap + 1, f"({orig_loc[0]:.0f},{orig_loc[1]:.0f})")
        c.restoreState()

        for pad in pads:
            # Apply rotation then flip_x to pad coords (relative to die center)
            rx, ry = rotate_point(pad['x'], pad['y'], rotation)
            if flip_x:
                ry = -ry
            px = die_cx + rx * scale
            py = die_cy + ry * scale

            # Determine color from pad name (same convention as DIE1)
            name_upper = pad['name'].upper()
            if any(kw in name_upper for kw in ('VDD', 'VCC', 'VDDQ')):
                color = colors.red
            elif any(kw in name_upper for kw in ('VSS', 'GND', 'VSSQ')):
                color = colors.blue
            else:
                color = colors.HexColor(color_scheme['signal'])

            # Draw pad rectangle
            c.saveState()
            c.setStrokeColor(color)
            c.setFillColor(color)
            c.setLineWidth(0.5)
            c.rect(px - pad_sz / 2, py - pad_sz / 2, pad_sz, pad_sz, fill=1, stroke=1)

            # Draw pad label OUTSIDE the frame
            c.setFont("Helvetica", font_sz)
            c.setFillColor(colors.black)
            c.setFillAlpha(0.5)
            label = pad['name']
            label_w = font_sz * 0.6 * len(label)
            # Use TRANSFORMED coords to determine which side the pad is on
            if abs(rx) >= abs(ry):
                side = 'R' if rx >= 0 else 'L'
            else:
                side = 'T' if ry >= 0 else 'B'
            # Position label outside frame, centered on pad
            if side == 'R':
                lx = frame_right + gap
                ly = py - font_sz * 0.35
                label_rot = 0
            elif side == 'L':
                lx = frame_left - gap - label_w
                ly = py - font_sz * 0.35
                label_rot = 0
            elif side == 'T':
                # rot=90: text extends UPWARD from anchor, so anchor at text bottom
                lx = px
                ly = frame_top + gap
                label_rot = 90
            else:  # B
                # rot=-90: text extends DOWNWARD from anchor, so anchor at text top
                lx = px
                ly = frame_bottom - gap - label_w
                label_rot = -90
            c.saveState()
            c.translate(lx, ly)
            c.rotate(label_rot)
            c.drawString(0, 0, label)
            c.restoreState()
            c.restoreState()

        # Draw DIE1 connection wires
        if apr_coords:
            # Build lookup: DIE_PIN_NAME -> DIE_NUM (first match, skip NC/DOWNBOND)
            d1_name_to_num = {}
            for row in self.parser.data:
                pname = row['DIE_PIN_NAME'].upper()
                if pname in ('NC', 'DOWNBOND') or row['DIE_NUM'] in ('0', '-'):
                    continue
                if pname not in d1_name_to_num:
                    d1_name_to_num[pname] = row['DIE_NUM']

            n_wires = 0
            for pad in pads:
                d1_pad_name = pad.get('d1_pad', '').strip()
                if not d1_pad_name:
                    continue
                conn_type = pad.get('type', 'signal').strip().lower()

                # Find DIE1 pad position
                d1_die_num = d1_name_to_num.get(d1_pad_name.upper())
                if not d1_die_num:
                    self.logger.warn(f"{die_label} wire: D1 pad '{d1_pad_name}' not found in DIE1")
                    continue
                a_pt = apr_coords.get(d1_die_num)
                if not a_pt:
                    continue

                # Die pad center (apply rotation + flip)
                rx, ry = rotate_point(pad['x'], pad['y'], rotation)
                if flip_x:
                    ry = -ry
                d_px = die_cx + rx * scale
                d_py = die_cy + ry * scale

                # DIE1 pad center (adjust from frame-edge anchor inward)
                pin_cx, pin_cy = a_pt['pt']
                a_side = a_pt['side']
                a_bw, a_bh = a_pt['bw'], a_pt['bh']
                if a_side == 'L':
                    d1_px, d1_py = pin_cx + a_bw / 2, pin_cy
                elif a_side == 'R':
                    d1_px, d1_py = pin_cx - a_bw / 2, pin_cy
                elif a_side == 'B':
                    d1_px, d1_py = pin_cx, pin_cy + a_bh / 2
                elif a_side == 'T':
                    d1_px, d1_py = pin_cx, pin_cy - a_bh / 2
                else:
                    d1_px, d1_py = pin_cx, pin_cy

                # Wire color by type
                if conn_type == 'power':
                    wire_color = colors.HexColor(color_scheme['wire_power']) if isinstance(color_scheme['wire_power'], str) else color_scheme['wire_power']
                else:
                    wire_color = colors.HexColor(color_scheme['wire_signal'])

                c.saveState()
                c.setStrokeColor(wire_color)
                c.setLineWidth(0.6)
                c.line(d_px, d_py, d1_px, d1_py)
                # Dots at both ends
                c.setFillColor(wire_color)
                c.circle(d_px, d_py, 1.2, stroke=0, fill=1)
                c.circle(d1_px, d1_py, 1.2, stroke=0, fill=1)
                c.restoreState()
                n_wires += 1

            if n_wires:
                self.logger.info(f"  DIE1-{die_label} wires: {n_wires} connections drawn")

# --- Checker Class ---
class Checker:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def check_stagger(self, filename, max_io=8):
        self.logger.info("Running Stagger Density Check...")
        try:
            with open(filename, 'w') as f:
                f.write("STAGGER DENSITY CHECK REPORT\n")
                f.write("=" * 30 + "\n")
                io_count = 0
                for row in self.parser.data:
                    if row['DIRECTION'] in ('I', 'O', 'B', 'IO'):
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
    # Fixed header order for .new / .new.csv output
    HEADER_ORDER = ['PROJECT NO', 'PKG_TOP_LEFT_PIN', 'PACKAGE', 'VERSION', 'PKG_SIZE', 'DIE_SIZE']

    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def _build_ordered_header(self):
        """Build ordered header list with defaults for missing keys."""
        h = dict(self.parser.header)

        # Normalize: PRODUCTION NO → PROJECT NO
        if 'PROJECT NO' not in h and 'PRODUCTION NO' in h:
            h['PROJECT NO'] = h['PRODUCTION NO']

        # Defaults
        h.setdefault('PROJECT NO', 'UNKNOWN')
        h.setdefault('PKG_TOP_LEFT_PIN', '1')
        h.setdefault('VERSION', 'N/A')

        # PKG_SIZE: derive from QFN_BODY_SIZES if missing
        if 'PKG_SIZE' not in h:
            pkg_str = h.get('PACKAGE', '')
            m = re.match(r'(\d+)', pkg_str)
            if m:
                pin_count = int(m.group(1))
                body_mm = QFN_BODY_SIZES.get(pin_count)
                if body_mm:
                    body_um = int(body_mm * 1000)
                    h['PKG_SIZE'] = f"{body_um}x{body_um}"

        result = []
        for k in self.HEADER_ORDER:
            result.append((k, h.get(k, '')))
        return result

    def generate_completed_list(self, filename):
        self.logger.info(f"Generating completed list: {filename}")
        try:
            # Always use canonical headers (not raw_headers which may contain old field names)
            h = ['PKG_NUM', 'PKG_PIN_NAME', 'DIE_NUM', 'DIE_PIN_NAME', 'IO_CELL_NAME', 'PKG_LOC', 'DIE_LOC', 'DIRECTION', 'LOAD', 'SLEW', 'SSO']
            
            with open(filename, 'w') as f:
                for k, v in self._build_ordered_header():
                    f.write(f"{k} : {v}\n")
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

                def norm_pkg(v):
                    return '0' if not v or not v.strip() or v.strip() == '-' else v.strip()

                for r in self.parser.data:
                    # Skip empty rows (no PKG_NUM and no DIE_NUM)
                    if norm(r['PKG_NUM']) == '-' and norm(r['DIE_NUM']) == '-':
                        continue
                    row_str = f"{norm_pkg(r['PKG_NUM']):<8} {norm(r['PKG_PIN_NAME']):<12} {norm(r['DIE_NUM']):<12} {norm(r['DIE_PIN_NAME']):<20} {norm(r['IO_CELL_NAME']):<12} {norm(r['PKG_LOC']):<10} {norm(r['DIE_LOC']):<18} "
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
                for k, v in self._build_ordered_header():
                    f.write(f"{k} : {v}\n")
                f.write("\n")
                writer = csv.DictWriter(f, fieldnames=h)
                writer.writeheader()

                def norm(v):
                    return v if v and v.strip() else '-'

                for r in self.parser.data:
                    if norm(r['PKG_NUM']) == '-' and norm(r['DIE_NUM']) == '-':
                        continue
                    row = {field: norm(r[field]) for field in h}
                    row['PKG_NUM'] = r['PKG_NUM'] if r['PKG_NUM'] and r['PKG_NUM'].strip() and r['PKG_NUM'].strip() != '-' else '0'
                    writer.writerow(row)
        except Exception as e:
            self.logger.error(f"Error in CSV writer: {e}")

    def generate_innovus_io(self, filename):
        self.logger.info(f"Generating Innovus IO Constraint: {filename}")
        try:
            # Sort data by DIE_PAD_NUM for correct ring sequence in constraints
            sorted_data = sorted(
                [r for r in self.parser.data
                 if r['DIE_PIN_NAME'].upper() not in ('NC', 'DOWNBOND')
                 and r['DIE_NUM'] not in ('0', '-', '')
                 and r['PKG_NUM'].upper() != 'INNER_BOND'
                 and r.get('INST_NAME', '-') not in ('-', '')],
                key=lambda x: int(x['DIE_NUM']))
            
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            seen_insts = set()
            for row in sorted_data:
                inst = row['INST_NAME']
                if inst in seen_insts: continue
                seen_insts.add(inst)
                loc = row['DIE_LOC'].upper()
                if loc in sides: sides[loc].append(inst)

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
            sorted_data = sorted(
                [r for r in self.parser.data
                 if r['DIE_PIN_NAME'].upper() not in ('NC', 'DOWNBOND')
                 and r['DIE_NUM'] not in ('0', '-', '')
                 and r['PKG_NUM'].upper() != 'INNER_BOND'
                 and r.get('INST_NAME', '-') not in ('-', '')],
                key=lambda x: int(x['DIE_NUM']))
            
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            seen_insts = set()
            for row in sorted_data:
                inst = row['INST_NAME']
                if inst in seen_insts: continue
                seen_insts.add(inst)
                loc = row['DIE_LOC'].upper()
                if loc in sides: sides[loc].append(inst)

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
    p = argparse.ArgumentParser(description="FT_PAD_ASSIGN Standalone Tool")
    p.add_argument("-list", required=True, help="Pin list file")
    p.add_argument("-v", nargs='*', help="Verilog files")
    p.add_argument("-apr", action="store_true", help="APR Diagram")
    p.add_argument("-pkg", action="store_true", help="PKG Diagram")
    p.add_argument("-combined", action="store_true", help="Combined Diagram with wires")
    p.add_argument("-c", action="store_true", help="Generate .new and .const files")
    p.add_argument("-stagger", action="store_true", help="Stagger check")
    p.add_argument("-stagger-max", type=int, default=8, help="Max consecutive I/O pins before warning (default: 8)")
    p.add_argument("-all", action="store_true", help="All functions")
    p.add_argument("-o", "--outdir", default=".", help="Output folder (default: current directory)")
    p.add_argument("--die2", help="DIE2 spec file (.csv or .md)")
    p.add_argument("--die2-loc", dest="die2_loc", help="DIE2 bottom-left x,y in um, relative to DIE1 center (only for .md)")
    p.add_argument("--die2-label", dest="die2_label", default=None, help="DIE2 label in PDF (default: from CSV or 'DIE2')")
    p.add_argument("--die2-flip-x", dest="die2_flip_x", action="store_true", help="[DEPRECATED] Use PLACEMENT : R0_FLIP_X in CSV instead")
    p.add_argument("--die3", help="DIE3 spec file (.csv only)")
    p.add_argument("--die3-label", dest="die3_label", default=None, help="DIE3 label in PDF (default: from CSV or 'DIE3')")
    args = p.parse_args()
    if args.v is not None and len(args.v) == 0:
        args.v = None

    if args.all: args.apr = args.pkg = args.combined = args.c = args.stagger = True

    # 1. Initial Logger
    logger = Logger() # Defaults to stdout only if no filename
    logger.info("Starting FT_PAD_ASSIGN Standalone Tool...")

    # 2. Pre-scan the pin list for PRODUCTION NO. to set up output early
    proj_no = "fpad_out"
    if os.path.exists(args.list):
        try:
            with open(args.list, 'r') as f:
                for line in f:
                    match = re.search(r'(?:PRODUCTION|PROJECT) NO\.?\s*:\s*([^,\n]+)', line, re.I)
                    if match:
                        proj_no = match.group(1).strip()
                        break
        except Exception: pass
    
    proj_no = re.sub(r'[^\w\-]', '_', proj_no).rstrip(' _')
    if not proj_no: proj_no = "fpad_out"
    
    out_dir = "."
    if args.outdir:
        out_dir = args.outdir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            # We can't log this to the file yet, but it's okay

    # 3. Setup final log file location
    log_path = os.path.join(out_dir, f"{proj_no}.log")
    logger.set_log_file(log_path)
    logger.info(f"Log file initialized: {log_path}")

    # 4. Now run the full parsing and check
    parser = Parser(logger, args.list, args.v)
    logger.indent()
    parser.parse_list()
    logger.dedent()

    if args.v:
        logger.indent()
        parser.parse_verilog()
        parser.bridge_data()
        logger.dedent()
    else:
        logger.warn("No Verilog files, skipping bridging.")

    prefix = os.path.join(out_dir, proj_no)

    if args.stagger:
        logger.section("Stagger Density Check")
        logger.indent()
        Checker(logger, parser).check_stagger(f"{prefix}_stagger.rpt", max_io=args.stagger_max)
        logger.dedent()

    if args.c:
        logger.section("Constraint Files")
        logger.indent()
        w = Writer(logger, parser)
        w.generate_completed_list(f"{prefix}.new")
        w.generate_completed_csv(f"{prefix}.new.csv")
        if args.v:
            w.generate_innovus_io(f"{prefix}_chip.inn.const")
            w.generate_icc2_io(f"{prefix}_chip.icc2.const")
        logger.dedent()

    # Parse DIE2 options
    die2_info = None
    die2_loc = None
    if args.die2:
        logger.section(f"DIE2 Overlay: {args.die2}")
        logger.indent()
        if args.die2.lower().endswith('.csv'):
            die2_info = parse_die_csv(args.die2, 'DIE2', logger)
            if die2_info and die2_info.get('loc'):
                die2_loc = die2_info['loc']
            if die2_info and args.die2_label:
                die2_info['name'] = args.die2_label
        else:
            die2_info = parse_die2_md(args.die2, logger)
            die2_info['placement'] = 'R0'
            die2_info['rotation'] = 0
            die2_info['flip_x'] = False
            if args.die2_loc:
                try:
                    parts = args.die2_loc.split(',')
                    die2_loc = (float(parts[0]), float(parts[1]))
                except (ValueError, IndexError):
                    logger.error(f"Invalid -die2_loc format: '{args.die2_loc}'. Expected 'x,y'.")
                    die2_info = None
        # Backward compat: deprecated --die2-flip-x
        if die2_info and args.die2_flip_x:
            logger.warn("--die2-flip-x is deprecated. Use PLACEMENT : R0_FLIP_X in CSV.")
            die2_info['flip_x'] = True
            die2_info['rotation'] = 0
            die2_info['placement'] = 'R0_FLIP_X'
        logger.dedent()

    # Parse DIE3 options
    die3_info = None
    die3_loc = None
    if args.die3:
        logger.section(f"DIE3 Overlay: {args.die3}")
        logger.indent()
        if not args.die3.lower().endswith('.csv'):
            logger.error("DIE3 only supports .csv format")
        else:
            die3_info = parse_die_csv(args.die3, 'DIE3', logger)
            if die3_info and die3_info.get('loc'):
                die3_loc = die3_info['loc']
            if die3_info and args.die3_label:
                die3_info['name'] = args.die3_label
        logger.dedent()

    if args.apr or args.pkg or args.combined:
        logger.section("PDF Generation")
        die2_label = args.die2_label or (die2_info.get('name') if die2_info else None) or "DIE2"
        die3_label = args.die3_label or (die3_info.get('name') if die3_info else None) or "DIE3"
        pg = PDFGen(logger, parser,
                    die2_info=die2_info, die2_loc=die2_loc, die2_label=die2_label,
                    die3_info=die3_info, die3_loc=die3_loc, die3_label=die3_label)
        logger.indent()
        if args.apr: pg.generate_apr_pdf(f"{prefix}_apr.pdf")
        if args.pkg: pg.generate_pkg_pdf(f"{prefix}_pkg.pdf")
        if args.combined: pg.generate_combined_pdf(f"{prefix}_combined.pdf")
        logger.dedent()

    logger.info("Execution successful.")
    logger.close()

if __name__ == "__main__":
    main()
