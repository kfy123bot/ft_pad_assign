#!/usr/bin/env python3
"""
FPAD_ASSIGN - Standalone Version
A tool for IC I/O assignment, visualization, and validation.
Usage: python3 fpad_assign.py -list <pin_list> -v <verilog_files> [options]
"""

import argparse
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
        
        try:
            with open(self.list_file, 'r') as f:
                in_table = False
                for line in f:
                    line = line.strip()
                    if not line or re.match(r'^-+$', line): continue
                    match = re.search(r'^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)\s*:\s*(.*)', line, re.I)
                    if match:
                        self.header[match.group(1).upper()] = match.group(2)
                        continue
                    if line.startswith('PIN_NUM') and 'DIE_PAD_NUM' in line:
                        in_table = True
                        continue
                    if in_table:
                        cols = line.split()
                        if len(cols) >= 5:
                            row = {
                                'PIN_NUM':          cols[0],
                                'DIE_PAD_NUM':      cols[1],
                                'PIN_NAME':         cols[2],
                                'IO_CELL_NAME':     cols[3],
                                'LOCATION':         cols[4],
                                'DIE_PAD_NUM_LOC':  cols[5] if len(cols) > 5 else cols[4],
                                'DIRECTION':        cols[6] if len(cols) > 6 else '-',
                                'LOAD':             cols[7] if len(cols) > 7 else '-',
                                'SLEW':             cols[8] if len(cols) > 8 else '-',
                                'SSO':              cols[9] if len(cols) > 9 else '-',
                                'INST_NAME':    '-'
                            }
                            self.data.append(row)
            self.logger.info(f"Loaded {len(self.data)} entries from pin list.")
            self._sanity_check_list()
        except Exception as e:
            self.logger.fatal(f"Error parsing list: {e}")

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
        actual_pnums = {'L': set(), 'B': set(), 'R': set(), 'T': set()}

        for row in self.data:
            loc = row['LOCATION'].upper()
            pnum = row['PIN_NUM']
            pname = row['PIN_NAME'].upper()
            
            # Filter out special marks
            if pnum in ('0', '-', 'NC') or 'POWERCUT' in pname:
                continue
            
            if loc in actual_pnums:
                actual_pnums[loc].add(pnum)

        for side in ('L', 'B', 'R', 'T'):
            act_cnt = len(actual_pnums[side])
            exp_cnt = expected[side]
            if act_cnt != exp_cnt:
                self.logger.error(f"Sanity Check Failed for Side {side}:")
                self.logger.error(f"  - Expected from PACKAGE definition: {exp_cnt}")
                self.logger.error(f"  - Actual unique PIN_NUMs in list:   {act_cnt}")
                self.logger.error(f"  - Missing or extra pins on Side {side} detected!")
            else:
                self.logger.info(f"Side {side} check passed: {act_cnt} pins.")
        
        # If any side failed, we should probably let the user know this is a critical issue
        total_exp = sum(expected.values())
        total_act = sum(len(s) for s in actual_pnums.values())
        if total_exp != total_act:
             self.logger.error(f"TOTAL PIN COUNT MISMATCH: PACKAGE expects {total_exp}, List has {total_act} unique pins.")
        
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
        self.logger.info("Bridging data and re-indexing DIE_PAD_NUM...")
        pad_idx = 1
        for row in self.data:
            pname = row['PIN_NAME']
            pname_upper = pname.upper()
            
            # --- Re-indexing DIE_PAD_NUM ONLY ---
            # If NC, set to 0. Otherwise, sequential from 1.
            if pname_upper == 'NC':
                row['DIE_PAD_NUM'] = '0'
            else:
                row['DIE_PAD_NUM'] = str(pad_idx)
                pad_idx += 1

            # --- Original Bridging Logic (keep PIN_NUM as is) ---
            if pname_upper == 'NC': continue
            sn = pname
            p_mode = False
            if row['DIRECTION'] in ('P', 'G') or '%' in pname or 'POWERCUT' in pname_upper:
                p_mode = True
                if '%' in pname: sn = pname.split('%')[-1]
            if p_mode:
                if row['IO_CELL_NAME'] == '-': row['IO_CELL_NAME'] = self.v_raw_insts.get(sn, 'NOT_FOUND')
                row['INST_NAME'] = sn
            else:
                if row['IO_CELL_NAME'] == '-': row['IO_CELL_NAME'] = self.v_insts.get(sn, 'NOT_FOUND')
                row['INST_NAME'] = self.v_net_to_inst.get(sn, sn)
                if row['DIRECTION'] == '-': row['DIRECTION'] = self.v_ports.get(sn, 'UNKNOWN')

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
        t_pins_early = []
        found_other_side = False
        seen_pnums = set()
        
        for row in self.parser.data:
            p_loc = row['LOCATION'].upper()
            a_loc = row['DIE_PAD_NUM_LOC'].upper()
            pnum = row['PIN_NUM']
            pname = row['PIN_NAME'].upper()
            
            # PKG side: Original logic (L,B,R,T order of appearance)
            if p_loc in pkg_data_by_side:
                if pnum not in ('0', '-', 'NC') and 'POWERCUT' not in pname and pnum not in seen_pnums:
                    pkg_data_by_side[p_loc].append(row)
                    seen_pnums.add(pnum)
            
            # APR side: Special logic for 'T' pins at the beginning
            if pname != 'NC' and a_loc in apr_data_by_side:
                if a_loc != 'T':
                    found_other_side = True
                    apr_data_by_side[a_loc].append(row)
                else:
                    if not found_other_side:
                        t_pins_early.append(row)
                    else:
                        apr_data_by_side['T'].append(row)
        
        # Append early T pins to the end of APR T side
        apr_data_by_side['T'].extend(t_pins_early)

        edge_pkg, edge_apr = 350, 200
        c.setLineWidth(2)
        c.rect(cx - edge_pkg/2, cy - edge_pkg/2, edge_pkg, edge_pkg)
        c.setDash(4, 2); c.rect(cx - edge_apr/2, cy - edge_apr/2, edge_apr, edge_apr); c.setDash()

        pkg_coords, apr_coords = {}, {}
        for side in ('L', 'B', 'R', 'T'):
            p_coords = self._draw_side_boxes(c, side, pkg_data_by_side[side], cx, cy, edge_pkg, getattr(self, f"_{side}_pos")(cx, cy, edge_pkg), l_cnt if side=='L' else b_cnt if side=='B' else r_cnt if side=='R' else t_cnt, 'PKG', label_inside=False)
            pkg_coords.update(p_coords)
            a_coords = self._draw_side_boxes(c, side, apr_data_by_side[side], cx, cy, edge_apr, getattr(self, f"_{side}_pos")(cx, cy, edge_apr), l_cnt if side=='L' else b_cnt if side=='B' else r_cnt if side=='R' else t_cnt, 'APR', label_inside=True)
            apr_coords.update(a_coords)

        c.setLineWidth(0.3)
        for row in self.parser.data:
            if row['PIN_NAME'].upper() == 'NC': continue
            p_pt, a_pt = pkg_coords.get(row['PIN_NUM']), apr_coords.get(row['DIE_PAD_NUM'])
            if p_pt and a_pt:
                dir_color = colors.grey
                if row['DIRECTION'] == 'P': dir_color = colors.red
                elif row['DIRECTION'] == 'G': dir_color = colors.blue
                c.setStrokeColor(dir_color); c.line(p_pt[0], p_pt[1], a_pt[0], a_pt[1])

        self._draw_center_info(c, cx, cy, edge_apr, l_cnt, b_cnt, r_cnt, t_cnt, apr_data_by_side)
        c.save()

    def generate_apr_pdf(self, filename):
        if not HAS_REPORTLAB: return
        self.logger.info(f"Generating APR Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4)); width, height = landscape(A4)
        cx, cy = width/2, 240; self._draw_header(c, "APR PIN DIAGRAM", width, height)
        edge = 350
        c.setLineWidth(2); c.rect(cx - edge/2, cy - edge/2, edge, edge)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        t_pins_early = []
        found_other_side = False
        for row in self.parser.data:
            if row['PIN_NAME'].upper() == 'NC': continue
            loc = row['DIE_PAD_NUM_LOC'].upper()
            if loc in data_by_side:
                if loc != 'T':
                    found_other_side = True
                    data_by_side[loc].append(row)
                else:
                    if not found_other_side:
                        t_pins_early.append(row)
                    else:
                        data_by_side['T'].append(row)
        data_by_side['T'].extend(t_pins_early)
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)
        self._draw_center_info(c, cx, cy, edge, l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        for side in ('L', 'B', 'R', 'T'):
            self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, getattr(self, f"_{side}_pos")(cx, cy, edge), l_cnt if side=='L' else b_cnt if side=='B' else r_cnt if side=='R' else t_cnt, 'APR', label_inside=False)
        c.save()

    def generate_pkg_pdf(self, filename):
        if not HAS_REPORTLAB: return
        self.logger.info(f"Generating PKG Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4)); width, height = landscape(A4)
        cx, cy = width/2, 240; self._draw_header(c, "PACKAGE PIN DIAGRAM", width, height)
        edge = 350
        c.setLineWidth(2); c.rect(cx - edge/2, cy - edge/2, edge, edge)
        pkg_data = {}; order = []
        for row in self.parser.data:
            pnum = row['PIN_NUM']
            pname = row['PIN_NAME'].upper()
            if pnum in ('0', '-', 'NC') or 'POWERCUT' in pname: continue
            if pnum not in pkg_data: pkg_data[pnum] = row.copy(); order.append(pnum)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for pnum in order:
            loc = pkg_data[pnum]['LOCATION'].upper()
            if loc in data_by_side: data_by_side[loc].append(pkg_data[pnum])
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)
        self._draw_center_info(c, cx, cy, edge, l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        for side in ('L', 'B', 'R', 'T'):
            self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, getattr(self, f"_{side}_pos")(cx, cy, edge), l_cnt if side=='L' else b_cnt if side=='B' else r_cnt if side=='R' else t_cnt, 'PKG', label_inside=False)
        c.save()

    def _L_pos(self, cx, cy, edge): return (cx - edge/2, cy)
    def _B_pos(self, cx, cy, edge): return (cx, cy - edge/2)
    def _R_pos(self, cx, cy, edge): return (cx + edge/2, cy)
    def _T_pos(self, cx, cy, edge): return (cx, cy + edge/2)

    def _draw_side_boxes(self, c, side, pins, cx, cy, length, b_pos, total, mode, label_inside=False):
        bx, by = b_pos; coords = {}
        if not pins: return coords
        actual_cnt = len(pins); calc_total = max(actual_cnt, total); step = length / (calc_total + 1)
        box_thickness = max(1, min(step * 0.8, 6)); font_size = max(2, min(step * 0.9, 7))
        box_len = 15 if mode == 'APR' else 25
        for idx, pin in enumerate(pins, 1):
            pname = pin['PIN_NAME']; display_name = pname
            if '%' in pname: display_name = pname.split('%')[-1] if mode == 'APR' else pname.split('%')[0]
            px, py = 0, 0; bw, bh = 0, 0
            if side == 'L':
                bw, bh = box_len, box_thickness; px = bx - (0 if label_inside else bw); py = (by + length/2) - (idx * step) - (bh/2)
                coords[pin['PIN_NUM'] if mode == 'PKG' else pin['DIE_PAD_NUM']] = (bx, py + bh/2)
            elif side == 'B':
                bw, bh = box_thickness, box_len; px = (bx - length/2) + (idx * step) - (bw/2); py = by - (0 if label_inside else bh)
                coords[pin['PIN_NUM'] if mode == 'PKG' else pin['DIE_PAD_NUM']] = (px + bw/2, by)
            elif side == 'R':
                bw, bh = box_len, box_thickness; px = bx - (bw if label_inside else 0); py = (by - length/2) + (idx * step) - (bh/2)
                coords[pin['PIN_NUM'] if mode == 'PKG' else pin['DIE_PAD_NUM']] = (bx, py + bh/2)
            elif side == 'T':
                bw, bh = box_thickness, box_len; px = (bx + length/2) - (idx * step) - (bw/2); py = by - (bh if label_inside else 0)
                coords[pin['PIN_NUM'] if mode == 'PKG' else pin['DIE_PAD_NUM']] = (px + bw/2, by)
            c.setLineWidth(0.5); c.setStrokeColor(colors.black); direction = pin['DIRECTION']
            if 'POWERCUT' in pname.upper(): c.setFillColor(colors.black); c.rect(px, py, bw, bh, fill=1)
            elif direction == 'P': c.setFillColor(colors.red); c.rect(px, py, bw, bh, fill=1)
            elif direction == 'G': c.setFillColor(colors.blue); c.rect(px, py, bw, bh, fill=1)
            else: c.rect(px, py, bw, bh, fill=0)
            c.setFont("Helvetica", font_size); c.setFillColor(colors.black)
            if side == 'L':
                c.drawRightString(px - 4, py + (bh/2) - (font_size/2), display_name)
            elif side == 'R':
                c.drawString(px + bw + 4, py + (bh/2) - (font_size/2), display_name)
            elif side == 'T':
                c.saveState()
                c.translate(px + bw/2, py + bh + 2)
                c.rotate(90); c.drawString(0, -font_size/2, display_name)
                c.restoreState()
            elif side == 'B':
                c.saveState()
                c.translate(px + bw/2, py - 4) # Increase gap and anchor
                c.rotate(270); c.drawString(0, -font_size/2, display_name) # Use drawString to grow DOWN
                c.restoreState()

            # --- Pin Numbering (1, 5, 10...) and Start Dot (Pin 1) ---
            num_str = pin['DIE_PAD_NUM'] if mode == 'APR' else pin['PIN_NUM']
            try:
                n_int = int(num_str)
                # 1. Draw Start Dot (PKG uses Pin 1, APR uses first pin of Side L)
                draw_dot = False
                if mode == 'PKG':
                    if n_int == 1: draw_dot = True
                else: # APR mode
                    if side == 'L' and idx == 1: draw_dot = True

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
                            msg = f"[WARN] Consecutive I/O at Pin {row['PIN_NUM']} ({row['PIN_NAME']})"
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
            with open(filename, 'w') as f:
                for k, v in sorted(self.parser.header.items()):
                    f.write(f"{k:<20} : {v}\n")
                f.write("\n")
                f.write(f"{'PIN_NUM':<8} {'DIE_PAD_NUM':<12} {'PIN_NAME':<20} {'IO_CELL_NAME':<12} {'LOCATION':<10} {'DIE_PAD_NUM_LOC':<18} {'DIRECTION':<10} {'LOAD':<6} {'SLEW':<6} {'SSO':<6}\n")
                f.write("-" * 120 + "\n")
                for r in self.parser.data:
                    f.write(f"{r['PIN_NUM']:<8} {r['DIE_PAD_NUM']:<12} {r['PIN_NAME']:<20} {r['IO_CELL_NAME']:<12} {r['LOCATION']:<10} {r['DIE_PAD_NUM_LOC']:<18} {r['DIRECTION']:<10} {r['LOAD']:<6} {r['SLEW']:<6} {r['SSO']:<6}\n")
        except Exception as e:
            self.logger.error(f"Error in writer: {e}")

    def generate_innovus_io(self, filename):
        self.logger.info(f"Generating Innovus IO Constraint: {filename}")
        try:
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            for row in self.parser.data:
                if row['PIN_NAME'].upper() == 'NC': continue
                loc = row['LOCATION'].upper()
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
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            for row in self.parser.data:
                if row['PIN_NAME'].upper() == 'NC': continue
                loc = row['LOCATION'].upper()
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
    p.add_argument("-o", "--outdir", help="Output folder")
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
