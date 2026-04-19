# lib/fpad_py/parser.py

import re
import os

class Parser:
    def __init__(self, logger, list_file, v_files=None):
        self.logger = logger
        self.list_file = list_file
        self.v_files = v_files if v_files else []
        self.header = {}
        self.data = []
        self.v_ports = {}
        self.v_insts = {}       # Net -> Cell_Type
        self.v_net_to_inst = {} # Net -> Instance_Name
        self.v_raw_insts = {}   # Instance_Name -> Cell_Type

    def parse_list(self):
        if not os.path.exists(self.list_file):
            self.logger.fatal(f"Cannot open {self.list_file}")
            
        self.logger.info(f"Parsing Pin List: {self.list_file}")
        in_table = False
        with open(self.list_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('-'):
                    continue
                
                # Header info
                match = re.search(r'^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)\s*:\s*(.*)', line, re.I)
                if match:
                    self.header[match.group(1).upper()] = match.group(2)
                    continue
                
                # Table header
                if line.startswith('PIN_NUM') and 'DIE_PAD_NUM' in line:
                    in_table = True
                    continue
                
                if in_table:
                    cols = line.split()
                    if len(cols) >= 5:
                        row = {
                            'PIN_NUM':      cols[0],
                            'DIE_PAD_NUM':  cols[1],
                            'PIN_NAME':     cols[2],
                            'IO_CELL_NAME': cols[3],
                            'LOCATION':     cols[4],
                            'DIRECTION':    cols[5] if len(cols) > 5 else '-',
                            'LOAD':         cols[6] if len(cols) > 6 else '-',
                            'SLEW':         cols[7] if len(cols) > 7 else '-',
                            'SSO':          cols[8] if len(cols) > 8 else '-',
                            'INST_NAME':    '-'
                        }
                        self.data.append(row)

    def parse_verilog(self):
        for v_file in self.v_files:
            if not os.path.exists(v_file):
                self.logger.warn(f"Verilog file not found: {v_file}")
                continue
                
            self.logger.info(f"Parsing Verilog: {v_file}")
            with open(v_file, 'r') as f:
                content = f.read()

            # Parse ports
            port_matches = re.finditer(r'(input|output|inout)\s+(?:\[.*?\]\s+)?(.*?);', content, re.S)
            for m in port_matches:
                direction = m.group(1)[0].upper()
                ports = [p.strip() for p in m.group(2).split(',')]
                for p in ports:
                    self.v_ports[p] = direction

            # Parse instances
            inst_matches = re.finditer(r'(\w+)\s+(\w+)\s*\((.*?)\);', content, re.S)
            for m in inst_matches:
                cell_type, inst_name, body = m.groups()
                self.v_raw_insts[inst_name] = cell_type
                
                pad_match = re.search(r'\.PAD\s*\(\s*(.*?)\s*\)', body)
                if pad_match:
                    net = pad_match.group(1).strip()
                    self.v_insts[net] = cell_type
                    self.v_net_to_inst[net] = inst_name

    def bridge_data(self):
        self.logger.info("Bridging data and extracting Instance Names...")
        for row in self.data:
            pin_name = row['PIN_NAME']
            if pin_name == 'NC':
                continue
            
            search_name = pin_name
            power_mode = False
            
            # Power/Ground check logic
            if row['DIRECTION'] in ('P', 'G') or '%' in pin_name or 'POWERCUT' in pin_name.upper():
                power_mode = True
                if '%' in pin_name:
                    search_name = pin_name.split('%')[-1]
            
            if power_mode:
                if row['IO_CELL_NAME'] == '-':
                    row['IO_CELL_NAME'] = self.v_raw_insts.get(search_name, 'NOT_FOUND')
                row['INST_NAME'] = search_name
            else:
                if row['IO_CELL_NAME'] == '-':
                    row['IO_CELL_NAME'] = self.v_insts.get(search_name, 'NOT_FOUND')
                row['INST_NAME'] = self.v_net_to_inst.get(search_name, search_name)
                if row['DIRECTION'] == '-':
                    row['DIRECTION'] = self.v_ports.get(search_name, 'UNKNOWN')
