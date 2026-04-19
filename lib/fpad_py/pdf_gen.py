# lib/fpad_py/pdf_gen.py

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
import re

class PDFGen:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def generate_apr_pdf(self, filename):
        self.logger.info("Generating APR Diagram (Auto-scaling enabled)...")
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)

        self._draw_header(c, "APR PIN DIAGRAM")

        # 1. Parsing package specs
        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        if len(parts) >= 5:
            pkg_type = parts[0]
            l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5])
        else:
            l_cnt = b_cnt = r_cnt = t_cnt = 16

        # 2. Grouping data by side (APR skips NC)
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for row in self.parser.data:
            pname = row['PIN_NAME'].strip()
            if pname.upper() == 'NC':
                continue
            loc = row['LOCATION'].upper()
            if loc in data_by_side:
                data_by_side[loc].append(row)

        # 3. Calculate dynamic box edge
        box_edge = self._calc_box_edge(l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        cx, cy = width / 2, 260

        # Draw central box
        c.setLineWidth(2)
        c.setStrokeColor(colors.black)
        c.rect(cx - box_edge/2, cy - box_edge/2, box_edge, box_edge)

        self._draw_center_info(c, cx, cy, box_edge, l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)

        self._draw_side_boxes(c, 'L', data_by_side['L'], cx - box_edge/2, cy, box_edge, l_cnt, 'APR')
        self._draw_side_boxes(c, 'B', data_by_side['B'], cx, cy - box_edge/2, box_edge, b_cnt, 'APR')
        self._draw_side_boxes(c, 'R', data_by_side['R'], cx + box_edge/2, cy, box_edge, r_cnt, 'APR')
        self._draw_side_boxes(c, 'T', data_by_side['T'], cx, cy + box_edge/2, box_edge, t_cnt, 'APR')

        c.save()

    def generate_pkg_pdf(self, filename):
        self.logger.info("Generating PKG Diagram (Auto-scaling enabled)...")
        c = canvas.Canvas(filename, pagesize=landscape(A4))
        width, height = landscape(A4)

        self._draw_header(c, "PACKAGE PIN DIAGRAM")

        pkg_str = self.parser.header.get('PACKAGE', '64 16 16 16 16')
        parts = pkg_str.split()
        if len(parts) >= 5:
            pkg_type = parts[0]
            l_cnt, b_cnt, r_cnt, t_cnt = map(int, parts[1:5])
        else:
            l_cnt = b_cnt = r_cnt = t_cnt = 16

        # 1. De-duplication for PKG view (keep only unique PIN_NUMs)
        pkg_data = {}
        order = []
        for row in self.parser.data:
            pnum = row['PIN_NUM']
            if pnum in ('0', '-'):
                continue
            if pnum not in pkg_data:
                pkg_data[pnum] = row.copy()
                order.append(pnum)
        
        data_by_side = {'L': [], 'B': [], 'R': [], 'T': []}
        for pnum in order:
            loc = pkg_data[pnum]['LOCATION'].upper()
            if loc in data_by_side:
                data_by_side[loc].append(pkg_data[pnum])

        # 2. Calculate dynamic box edge
        box_edge = self._calc_box_edge(l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)
        cx, cy = width / 2, 260

        # Draw central box
        c.setLineWidth(2)
        c.setStrokeColor(colors.black)
        c.rect(cx - box_edge/2, cy - box_edge/2, box_edge, box_edge)

        self._draw_center_info(c, cx, cy, box_edge, l_cnt, b_cnt, r_cnt, t_cnt, data_by_side)

        self._draw_side_boxes(c, 'L', data_by_side['L'], cx - box_edge/2, cy, box_edge, l_cnt, 'PKG')
        self._draw_side_boxes(c, 'B', data_by_side['B'], cx, cy - box_edge/2, box_edge, b_cnt, 'PKG')
        self._draw_side_boxes(c, 'R', data_by_side['R'], cx + box_edge/2, cy, box_edge, r_cnt, 'PKG')
        self._draw_side_boxes(c, 'T', data_by_side['T'], cx, cy + box_edge/2, box_edge, t_cnt, 'PKG')

        c.save()

    def _calc_box_edge(self, l, b, r, t, data):
        max_req = max(l, b, r, t)
        max_act = 0
        for s in ('L', 'B', 'R', 'T'):
            cnt = len(data.get(s, []))
            if cnt > max_act:
                max_act = cnt
        
        final_max = max(max_req, max_act)
        edge = (final_max + 1) * 12 # 12pt per pin scaling
        edge = max(250, min(edge, 480))
        return edge

    def _draw_side_boxes(self, c, side, pins, bx, by, length, total, mode):
        if not pins:
            return
        
        actual_cnt = len(pins)
        calc_total = max(actual_cnt, total)
        step = length / (calc_total + 1)
        
        # Smart scaling for box and font
        box_thickness = max(1, min(step * 0.8, 6))
        font_size = max(2, min(step * 0.9, 7))
        box_len = 20

        for idx, pin in enumerate(pins, 1):
            pname = pin['PIN_NAME']
            display_name = pname
            if '%' in pname:
                parts = pname.split('%')
                display_name = parts[-1] if mode == 'APR' else parts[0]
            
            # Positioning
            px, py = 0, 0
            bw, bh = 0, 0
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

            # Coloring
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)
            direction = pin['DIRECTION']
            
            if 'POWERCUT' in pname.upper():
                c.setFillColor(colors.black)
                c.rect(px, py, bw, bh, fill=1)
            elif direction == 'P':
                c.setFillColor(colors.red)
                c.rect(px, py, bw, bh, fill=1)
            elif direction == 'G':
                c.setFillColor(colors.blue)
                c.rect(px, py, bw, bh, fill=1)
            else:
                c.rect(px, py, bw, bh, fill=0)

            # Pin numbers
            num = pin['DIE_PAD_NUM'] if mode == 'APR' else pin['PIN_NUM']
            try:
                num_int = int(num)
                if num_int == 1 or num_int % 5 == 0 or num_int == 0:
                    c.setFont("Helvetica", font_size)
                    c.setFillColor(colors.black)
                    if side == 'L': c.drawString(bx + 2, py, num)
                    elif side == 'R': c.drawRightString(bx - 2, py, num)
                    elif side == 'T': c.drawCentredString(px + bw/2, by - font_size * 2, num)
                    elif side == 'B': c.drawCentredString(px + bw/2, by + 2, num)
            except ValueError:
                pass

            # Pin names with rotation
            c.setFont("Helvetica", font_size)
            c.setFillColor(colors.black)
            if side == 'L':
                c.drawRightString(px - 4, py + (bh/2) - (font_size/2), display_name)
            elif side == 'R':
                c.drawString(px + bw + 4, py + (bh/2) - (font_size/2), display_name)
            elif side == 'T':
                c.saveState()
                c.translate(px + (bw/2), py + bh + 2)
                c.rotate(90)
                c.drawString(0, -font_size/2, display_name)
                c.restoreState()
            elif side == 'B':
                c.saveState()
                c.translate(px + (bw/2), py - 2)
                c.rotate(270)
                c.drawRightString(0, -font_size/2, display_name)
                c.restoreState()

    def _draw_header(self, c, title):
        c.setLineWidth(1)
        c.setStrokeColor(colors.black)
        c.rect(50, 510, 742, 65)
        
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(421, 550, title)
        
        c.setFont("Helvetica", 10)
        h = self.parser.header
        project = h.get('PRODUCTION NO.', h.get('PRODUCTION NO', 'N/A'))
        c.drawString(60, 530, f"Project: {project}")
        c.drawCentredString(421, 530, f"Package: {h.get('PACKAGE', 'N/A')}")
        c.drawRightString(782, 530, f"Version: {h.get('VERSION', 'N/A')}")

    def _draw_center_info(self, c, cx, cy, box_edge, l, b, r, t, data):
        final_max = max(l, b, r, t)
        for s in ('L', 'B', 'R', 'T'):
            final_max = max(final_max, len(data.get(s, [])))
        
        step = box_edge / (final_max + 1)
        font_size = max(2, min(step * 0.9, 7))
        spacing = font_size * 1.5
        
        c.setFont("Helvetica", font_size)
        c.setFillColor(colors.black)
        
        h = self.parser.header
        project = h.get('PRODUCTION NO.', h.get('PRODUCTION NO', 'N/A'))
        c.drawCentredString(cx, cy + spacing, f"Project: {project}")
        c.drawCentredString(cx, cy, f"Package: {h.get('PACKAGE', 'N/A')}")
        c.drawCentredString(cx, cy - spacing, f"Version: {h.get('VERSION', 'N/A')}")
