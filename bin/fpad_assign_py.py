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
    def info(self, msg):
        print(f"[INFO ] {msg}")
    def warn(self, msg):
        print(f"[WARN ] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")
    def fatal(self, msg):
        print(f"[FATAL] {msg}")
        sys.exit(1)

class PDFGenerator:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def generate_apr_pdf(self, filename):
        if not HAS_REPORTLAB:
            self.logger.error("ReportLab is not installed. PDF generation skipped. (pip install reportlab)")
            return
        self.logger.info(f"Generating APR Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)
        self._draw_header(c, "APR PIN DIAGRAM", width, height)
        pkg_str = self.parser.header.get("PACKAGE", "64 16 16 16 16")
        parts = pkg_str.split()
        l_cnt = int(parts[1]) if len(parts) > 1 else 16
        b_cnt = int(parts[2]) if len(parts) > 2 else 16
        r_cnt = int(parts[3]) if len(parts) > 3 else 16
        t_cnt = int(parts[4]) if len(parts) > 4 else 16
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for row in self.parser.data:
            if row["PIN_NAME"].upper() == 'NC':
                continue
            loc = row["LOCATION"].upper()
            if loc in data_by_side:
                data_by_side[loc].append(row)
        box_edge = self._calc_box_edge(l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        cx, cy = width/2, height/2 - 37
        c.setLineWidth(2)
        c.setStrokeColor(colors.black)
        c.rect(cx - box_edge/2, cy - box_edge/2, box_edge, box_edge, stroke=1, fill=0)
        self._draw_side_boxes(c, 'L', data_by_side['L'], cx - box_edge/2, cy, box_edge, l_cnt, 'APR')
        self._draw_side_boxes(c, 'B', data_by_side['B'], cx, cy - box_edge/2, box_edge, b_cnt, 'APR')
        self._draw_side_boxes(c, 'R', data_by_side['R'], cx + box_edge/2, cy, box_edge, r_cnt, 'APR')
        self._draw_side_boxes(c, 'T', data_by_side['T'], cx, cy + box_edge/2, box_edge, t_cnt, 'APR')
        c.save()

    def generate_pkg_pdf(self, filename):
        if not HAS_REPORTLAB:
            self.logger.error("ReportLab is not installed. PDF generation skipped. (pip install reportlab)")
            return
        self.logger.info(f"Generating PKG Diagram: {filename}")
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)
        self._draw_header(c, "PACKAGE PIN DIAGRAM", width, height)
        pkg_str = self.parser.header.get("PACKAGE", "64 16 16 16 16")
        parts = pkg_str.split()
        l_cnt = int(parts[1]) if len(parts) > 1 else 16
        b_cnt = int(parts[2]) if len(parts) > 2 else 16
        r_cnt = int(parts[3]) if len(parts) > 3 else 16
        t_cnt = int(parts[4]) if len(parts) > 4 else 16
        pkg_data = {}
        order = []
        for row in self.parser.data:
            pnum = row["PIN_NUM"]
            if pnum in ('0', '-'):
                continue
            if pnum not in pkg_data:
                pkg_data[pnum] = row.copy()
                order.append(pnum)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for pnum in order:
            loc = pkg_data[pnum]["LOCATION"].upper()
            if loc in data_by_side:
                data_by_side[loc].append(pkg_data[pnum])
        box_edge = self._calc_box_edge(l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        cx, cy = width/2, height/2 - 37
        c.setLineWidth(2)
        c.setStrokeColor(colors.black)
        c.rect(cx - box_edge/2, cy - box_edge/2, box_edge, box_edge, stroke=1, fill=0)
        self._draw_side_boxes(c, 'L', data_by_side['L'], cx - box_edge/2, cy, box_edge, l_cnt, 'PKG')
        self._draw_side_boxes(c, 'B', data_by_side['B'], cx, cy - box_edge/2, box_edge, b_cnt, 'PKG')
        self._draw_side_boxes(c, 'R', data_by_side['R'], cx + box_edge/2, cy, box_edge, r_cnt, 'PKG')
        self._draw_side_boxes(c, 'T', data_by_side['T'], cx, cy + box_edge/2, box_edge, t_cnt, 'PKG')
        c.save()

    def _calc_box_edge(self, l, b, r, t, data):
        max_req = max(l, b, r, t)
        max_act = 0
        for s in ['L','B','R','T']:
            max_act = max(max_act, len(data.get(s, [])))
        final_max = max(max_req, max_act)
        edge = (final_max + 1) * 12
        if edge < 250:
            edge = 250
        if edge > 480:
            edge = 480
        return edge

    def _draw_side_boxes(self, c, side, pins, bx, by, length, total, mode):
        if not pins:
            return
        actual_cnt = len(pins)
        calc_total = max(actual_cnt, total)
        step = length / (calc_total + 1)
        box_thickness = max(1, min(6, step * 0.8))
        font_size = max(2, min(7, step * 0.9))
        box_len = 20
        for idx, pin in enumerate(pins, 1):
            pname = pin["PIN_NAME"]
            display_name = pname
            if '%' in pname:
                parts = pname.split('%')
                display_name = parts[-1] if mode == 'APR' else parts[0]
            if side == 'L':
                bw, bh = box_len, box_thickness
                px = bx - bw
                py = (by + length/2) - (idx * step) - (bh/2)
            elif side == 'B':
                bw, bh = box_thickness, box_len
                px = (bx - length/2) + (idx * step) - (bw/2)
                py = by - bh
            elif side == 'R':
                bw, bh = box_len, box_thickness
                px = bx
                py = (by - length/2) + (idx * step) - (bh/2)
            elif side == 'T':
                bw, bh = box_thickness, box_len
                px = (bx + length/2) - (idx * step) - (bw/2)
                py = by
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)
            direction = pin["DIRECTION"]
            if 'POWERCUT' in pname.upper():
                c.setFillColor(colors.black)
                c.rect(px, py, bw, bh, stroke=1, fill=1)
            elif direction == 'P':
                c.setFillColor(colors.red)
                c.rect(px, py, bw, bh, stroke=1, fill=1)
            elif direction == 'G':
                c.setFillColor(colors.blue)
                c.rect(px, py, bw, bh, stroke=1, fill=1)
            else:
                c.rect(px, py, bw, bh, stroke=1, fill=0)
            num = pin["DIE_PAD_NUM"] if mode == 'APR' else pin["PIN_NUM"]
            if num != '-' and (num == '1' or int(num) % 5 == 0 or num == '0'):
                c.setFont("Helvetica", font_size)
                c.setFillColor(colors.black)
                if side == 'L':
                    nx, ny = bx + 2, py
                elif side == 'R':
                    nx, ny = bx - (font_size * 2), py
                elif side == 'T':
                    nx, ny = px, by - (font_size * 2)
                elif side == 'B':
                    nx, ny = px, by + 2
                c.drawString(nx, ny, str(num))
            c.setFont("Helvetica", font_size)
            c.setFillColor(colors.black)
            if side == 'L':
                c.drawRightString(px - 4, py, display_name)
            elif side == 'R':
                c.drawString(px + bw + 4, py, display_name)
            elif side == 'T':
                c.saveState(); c.translate(px + bw/2, py + bh + 2); c.rotate(90); c.drawString(0, 0, display_name); c.restoreState()
            elif side == 'B':
                c.saveState(); c.translate(px + bw/2, py - 2); c.rotate(270); c.drawString(0, 0, display_name); c.restoreState()

    def _draw_header(self, c, title, width, height):
        c.setLineWidth(1)
        c.setStrokeColor(colors.black)
        c.rect(50, height - 85, width - 100, 65)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, height - 45, title)
        c.setFont("Helvetica", 10)
        h = self.parser.header
        proj = h.get('PRODUCTION NO.', h.get('PRODUCTION NO', 'N/A'))
        pkg = h.get('PACKAGE', 'N/A')
        ver = h.get('VERSION', 'N/A')
        c.drawString(60, height - 65, f"Project: {proj}")
        c.drawCentredString(width/2, height - 65, f"Package: {pkg}")
        c.drawRightString(width - 60, height - 65, f"Version: {ver}")

class Parser:
    def __init__(self, logger, list_file, v_files):
        self.logger = logger
        self.list_file = list_file
        self.v_files = v_files
        self.header = {}
        self.data = []
        self.v_ports = {}
        self.v_insts = {}
        self.v_net_to_inst = {}
        self.v_raw_insts = {}

    def parse_list(self):
        self.logger.info(f"Parsing Pin List: {self.list_file}")
        try:
            with open(self.list_file, 'r') as fh:
                in_table = False
                for line in fh:
                    line = line.strip()
                    if not line or re.match(r'^-+$', line):
                        continue
                    header_match = re.match(r'^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)\s*:\s*(.*)', line, re.IGNORECASE)
                    if header_match:
                        self.header[header_match.group(1).upper()] = header_match.group(2)
                        continue
                    if line.startswith("PIN_NUM"):
                        in_table = True
                        continue
                    if in_table:
                        cols = line.split()
                        if len(cols) >= 5:
                            row = {
                                "PIN_NUM":      cols[0],
                                "DIE_PAD_NUM":  cols[1],
                                "PIN_NAME":     cols[2],
                                "IO_CELL_NAME": cols[3],
                                "LOCATION":     cols[4],
                                "DIRECTION":    cols[5] if len(cols) > 5 else '-',
                                "LOAD":         cols[6] if len(cols) > 6 else '-',
                                "SLEW":         cols[7] if len(cols) > 7 else '-',
                                "SSO":          cols[8] if len(cols) > 8 else '-',
                                "INST_NAME":    '-'
                            }
                            self.data.append(row)
        except Exception as e:
            self.logger.fatal(f"Cannot open {self.list_file}: {e}")

    def parse_verilog(self):
        for v_file in self.v_files:
            self.logger.info(f"Parsing Verilog: {v_file}")
            try:
                with open(v_file, 'r') as fh:
                    content = fh.read()
                port_matches = re.finditer(r'(input|output|inout)\s+(?:\[.*?\]\s+)?(.*?);', content, re.DOTALL)
                for m in port_matches:
                    direction = m.group(1)[0].upper()
                    ports = [p.strip() for p in m.group(2).split(',')]
                    for p in ports:
                        self.v_ports[p] = direction
                inst_matches = re.finditer(r'(\w+)\s+(\w+)\s*\((.*?)\);', content, re.DOTALL)
                for m in inst_matches:
                    cell, inst, body = m.groups()
                    self.v_raw_insts[inst] = cell
                    pad_match = re.search(r'\.PAD\s*\(\s*(.*?)\s*\)', body, re.DOTALL)
                    if pad_match:
                        net = pad_match.group(1).strip()
                        self.v_insts[net] = cell
                        self.v_net_to_inst[net] = inst
            except Exception as e:
                self.logger.warn(f"Error parsing Verilog {v_file}: {e}")

    def bridge_data(self):
        self.logger.info("Bridging data and extracting Instance Names...")
        for row in self.data:
            pin_name = row["PIN_NAME"]
            if pin_name == 'NC':
                continue
            search_name = pin_name
            power_mode = False
            if re.match(r'^[PG]$', row["DIRECTION"]) or '%' in pin_name or 'POWERCUT' in pin_name.upper():
                power_mode = True
                if '%' in pin_name:
                    search_name = pin_name.split('%')[-1]
            if power_mode:
                if row["IO_CELL_NAME"] == '-':
                    row["IO_CELL_NAME"] = self.v_raw_insts.get(search_name, 'NOT_FOUND')
                row["INST_NAME"] = search_name
            else:
                if row["IO_CELL_NAME"] == '-':
                    row["IO_CELL_NAME"] = self.v_insts.get(search_name, 'NOT_FOUND')
                row["INST_NAME"] = self.v_net_to_inst.get(search_name, search_name)
                if row["DIRECTION"] == '-':
                    row["DIRECTION"] = self.v_ports.get(search_name, 'UNKNOWN')

class Checker:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def check_stagger(self, filename):
        self.logger.info("Running Stagger Check...")
        try:
            with open(filename, 'w') as fh:
                fh.write("STAGGER CHECK REPORT\n")
                fh.write("=" * 30 + "\n")
                io_count = 0
                max_io_consecutive = 8
                for row in self.parser.data:
                    direction = row["DIRECTION"]
                    if direction in ('I', 'O', 'B'):
                        io_count += 1
                        if io_count > max_io_consecutive:
                            msg = f"[WARN] Too many consecutive I/Os at Pin {row['PIN_NUM']} ({row['PIN_NAME']})"
                            fh.write(msg + "\n")
                            self.logger.warn(msg)
                    elif direction in ('P', 'G'):
                        io_count = 0
            self.logger.info(f"Stagger report generated: {filename}")
        except Exception as e:
            self.logger.error(f"Error generating stagger report: {e}")

class Writer:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def generate_innovus_io(self, filename):
        self.logger.info(f"Generating Innovus IO Constraint: {filename}")
        try:
            sides = {'L': [], 'B': [], 'R': [], 'T': []}
            for row in self.parser.data:
                if row["PIN_NAME"].upper() == 'NC':
                    continue
                loc = row["LOCATION"].upper()
                if loc in sides:
                    sides[loc].append(row["INST_NAME"])
            with open(filename, 'w') as fh:
                fh.write("# Innovus IO Assignment File\n")
                fh.write("# Generated by FPAD_ASSIGN (Python Version)\n")
                fh.write("Version: 2\n\n")
                side_map = {'L': 'left', 'B': 'bottom', 'R': 'right', 'T': 'top'}
                for code in ['L', 'B', 'R', 'T']:
                    side_name = side_map[code]
                    fh.write(f"{side_name}:\n")
                    for inst in sides[code]:
                        fh.write(f"    (inst name=\"{inst}\")\n")
                    fh.write("\n")
            self.logger.info("Innovus IO file saved.")
        except Exception as e:
            self.logger.error(f"Error generating Innovus IO file: {e}")

def main():
    parser_arg = argparse.ArgumentParser(description="FPAD_ASSIGN Tool - Python Version (Bin)")
    parser_arg.add_argument("-list", required=True, help="Pin Sequence list file")
    parser_arg.add_argument("-v", nargs='+', required=True, help="Verilog Netlist files")
    parser_arg.add_argument("-apr", action="store_true", help="Generate APR PDF")
    parser_arg.add_argument("-pkg", action="store_true", help="Generate PKG PDF")
    parser_arg.add_argument("-c", action="store_true", help="Generate completed list (.new)")
    parser_arg.add_argument("-stagger", action="store_true", help="Run stagger check")
    parser_arg.add_argument("-all", action="store_true", help="Run all functions")

    args = parser_arg.parse_args()
    if args.all:
        args.apr = args.pkg = True
        args.c = True
        args.stagger = True

    logger = Logger()
    logger.info("Starting FPAD_ASSIGN tool (Python Version, bin script)...")
    parser_obj = Parser(logger, args.list, args.v)
    parser_obj.parse_list()
    parser_obj.parse_verilog()
    parser_obj.bridge_data()
    if args.c:
        new_list_path = args.list + ".new"
        logger.info(f"Generating completed list: {new_list_path}")
        with open(new_list_path, 'w') as ofh:
            for k, v in sorted(parser_obj.header.items()):
                ofh.write(f"{k:<20} : {v}\n")
            ofh.write("\n")
            ofh.write(f"{'PIN_NUM':<8} {'DIE_PAD_NUM':<12} {'PIN_NAME':<20} {'IO_CELL_NAME':<12} {'LOCATION':<8} {'DIRECTION':<10} {'LOAD':<6} {'SLEW':<6} {'SSO':<6}\n")
            ofh.write("-" * 100 + "\n")
            for row in parser_obj.data:
                ofh.write(f"{row['PIN_NUM']:<8} {row['DIE_PAD_NUM']:<12} {row['PIN_NAME']:<20} {row['IO_CELL_NAME']:<12} {row['LOCATION']:<8} {row['DIRECTION']:<10} {row['LOAD']:<6} {row['SLEW']:<6} {row['SSO']:<6}\n")
    pdf_gen = PDFGenerator(logger, parser_obj)
    if args.apr:
        pdf_gen.generate_apr_pdf(args.list + "_apr.pdf")
    if args.pkg:
        pdf_gen.generate_pkg_pdf(args.list + "_pkg.pdf")
    if args.stagger:
        checker = Checker(logger, parser_obj)
        checker.check_stagger(args.list + "_stagger.rpt")
    if args.all:
        writer = Writer(logger, parser_obj)
        writer.generate_innovus_io(args.list + "_chip.const")
    logger.info("Execution completed successfully.")

if __name__ == "__main__":
    main()
