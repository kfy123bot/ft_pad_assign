#!/usr/bin/env python3
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

class Logger:
    def info(self, msg): print(f"[INFO ] {msg}")
    def warn(self, msg): print(f"[WARN ] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def fatal(self, msg):
        print(f"[FATAL] {msg}")
        sys.exit(1)

class PDFGenerator:
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
        cx, cy = width / 2, 260
        self._draw_header(c, "COMBINED BONDING DIAGRAM", width, height)

        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5]) if len(parts) >= 5 else (16, 16, 16, 16)

        pkg_data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        apr_data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        seen_pnums = set()
        for row in self.parser.data:
            loc = row['LOCATION'].upper()
            if loc not in pkg_data_by_side: continue
            pnum = row['PIN_NUM']
            if pnum not in ('0', '-', 'NC') and pnum not in seen_pnums:
                pkg_data_by_side[loc].append(row)
                seen_pnums.add(pnum)
            if row['PIN_NAME'].upper() != 'NC':
                apr_data_by_side[loc].append(row)

        edge_pkg, edge_apr = 400, 220
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
        cx, cy = width/2, 260; self._draw_header(c, "APR PIN DIAGRAM", width, height)
        edge = 350
        c.setLineWidth(2); c.rect(cx - edge/2, cy - edge/2, edge, edge)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for row in self.parser.data:
            if row['PIN_NAME'].upper() == 'NC': continue
            loc = row['LOCATION'].upper()
            if loc in data_by_side: data_by_side[loc].append(row)
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
        cx, cy = width/2, 260; self._draw_header(c, "PACKAGE PIN DIAGRAM", width, height)
        edge = 350
        c.setLineWidth(2); c.rect(cx - edge/2, cy - edge/2, edge, edge)
        pkg_data = {}; order = []
        for row in self.parser.data:
            pnum = row['PIN_NUM']
            if pnum in ('0', '-', 'NC'): continue
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
                if label_inside: c.drawString(px + bw + 2, py + (bh/2) - (font_size/2), display_name)
                else: c.drawRightString(px - 4, py + (bh/2) - (font_size/2), display_name)
            elif side == 'R':
                if label_inside: c.drawRightString(px - 2, py + (bh/2) - (font_size/2), display_name)
                else: c.drawString(px + bw + 4, py + (bh/2) - (font_size/2), display_name)
            elif side == 'T':
                c.saveState()
                if label_inside: c.translate(px + bw/2, py - 2); c.rotate(270); c.drawRightString(0, -font_size/2, display_name)
                else: c.translate(px + bw/2, py + bh + 2); c.rotate(90); c.drawString(0, -font_size/2, display_name)
                c.restoreState()
            elif side == 'B':
                c.saveState()
                if label_inside: c.translate(px + bw/2, py + bh + 2); c.rotate(90); c.drawString(0, -font_size/2, display_name)
                else: c.translate(px + bw/2, py - 2); c.rotate(270); c.drawRightString(0, -font_size/2, display_name)
                c.restoreState()
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

class Parser:
    def __init__(self, logger, list_file, v_files):
        self.logger, self.list_file, self.v_files = logger, list_file, v_files
        self.header, self.data = {}, []
        self.v_ports, self.v_insts, self.v_net_to_inst, self.v_raw_insts = {}, {}, {}, {}

    def parse_list(self):
        self.logger.info(f"Parsing Pin List: {self.list_file}")
        try:
            with open(self.list_file, 'r') as fh:
                in_table = False
                for line in fh:
                    line = line.strip()
                    if not line or re.match(r'^-+$', line): continue
                    hm = re.match(r'^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)\s*:\s*(.*)', line, re.I)
                    if hm: self.header[hm.group(1).upper()] = hm.group(2); continue
                    if line.startswith("PIN_NUM"): in_table = True; continue
                    if in_table:
                        cols = line.split()
                        if len(cols) >= 5:
                            self.data.append({
                                "PIN_NUM": cols[0], "DIE_PAD_NUM": cols[1], "PIN_NAME": cols[2], "IO_CELL_NAME": cols[3],
                                "LOCATION": cols[4], "DIRECTION": cols[5] if len(cols) > 5 else '-',
                                "LOAD": cols[6] if len(cols) > 6 else '-', "SLEW": cols[7] if len(cols) > 7 else '-',
                                "SSO": cols[8] if len(cols) > 8 else '-', "INST_NAME": '-'
                            })
        except Exception as e: self.logger.fatal(f"Cannot open {self.list_file}: {e}")

    def parse_verilog(self):
        for v_file in self.v_files:
            self.logger.info(f"Parsing Verilog: {v_file}")
            try:
                with open(v_file, 'r') as fh: content = fh.read()
                pm = re.finditer(r'(input|output|inout)\s+(?:\[.*?\]\s+)?(.*?);', content, re.S)
                for m in pm:
                    dir = m.group(1)[0].upper()
                    for p in [x.strip() for x in m.group(2).split(',')]: self.v_ports[p] = dir
                im = re.finditer(r'(\w+)\s+(\w+)\s*\((.*?)\);', content, re.S)
                for m in im:
                    cell, inst, body = m.groups(); self.v_raw_insts[inst] = cell
                    pad_m = re.search(r'\.PAD\s*\(\s*(.*?)\s*\)', body, re.S)
                    if pad_m: net = pad_m.group(1).strip(); self.v_insts[net] = cell; self.v_net_to_inst[net] = inst
            except Exception as e: self.logger.warn(f"Error parsing Verilog {v_file}: {e}")

    def bridge_data(self):
        self.logger.info("Bridging data...")
        for row in self.data:
            if row["PIN_NAME"] == 'NC': continue
            sn = row["PIN_NAME"]; pm = False
            if re.match(r'^[PG]$', row["DIRECTION"]) or '%' in sn or 'POWERCUT' in sn.upper():
                pm = True; sn = sn.split('%')[-1] if '%' in sn else sn
            if pm:
                if row["IO_CELL_NAME"] == '-': row["IO_CELL_NAME"] = self.v_raw_insts.get(sn, 'NOT_FOUND')
                row["INST_NAME"] = sn
            else:
                if row["IO_CELL_NAME"] == '-': row["IO_CELL_NAME"] = self.v_insts.get(sn, 'NOT_FOUND')
                row["INST_NAME"] = self.v_net_to_inst.get(sn, sn)
                if row["DIRECTION"] == '-': row["DIRECTION"] = self.v_ports.get(sn, 'UNKNOWN')

def main():
    p = argparse.ArgumentParser(description="FT_PAD_ASSIGN Tool")
    p.add_argument("-list", required=True); p.add_argument("-v", nargs='+', required=True)
    p.add_argument("-apr", action="store_true"); p.add_argument("-pkg", action="store_true")
    p.add_argument("-combined", action="store_true", help="Generate combined PDF with wires")
    p.add_argument("-all", action="store_true")
    args = p.parse_args()
    if args.all: args.apr = args.pkg = args.combined = True
    
    logger = Logger(); logger.info("Starting FT_PAD_ASSIGN...")
    parser = Parser(logger, args.list, args.v); parser.parse_list(); parser.parse_verilog(); parser.bridge_data()
    
    pdf = PDFGenerator(logger, parser)
    if args.apr: pdf.generate_apr_pdf(args.list + "_apr.pdf")
    if args.pkg: pdf.generate_pkg_pdf(args.list + "_pkg.pdf")
    if args.combined: pdf.generate_combined_pdf(args.list + "_combined.pdf")
    logger.info("Done.")

if __name__ == "__main__":
    main()
