<!-- Slide number: 1 -->

![](Picture72.jpg)
# fiti Design Handoff Package Introduction

Design Service Division, fiti
http://www.fiti.com
2007/02/13

### Notes:

<!-- Slide number: 2 -->
Design Handoff Package Overview
fiti in-house proprietary design kits for project cowork
Utility
UNS          		:  Netlist screener
UTPG          		:  Test pattern translator
FT_PAD_ASSIGN 	:  Pad assignment file translator

Script
PrimeTime QoR
Design Compiler Naming Rule

Document
Design kit for ASIC Design Service – User’s Manual
fiti Static Timing Analysis User Guide
fiti Spare Cell Guide

Data Exchange / UNS / FT_PAD_ASSIGN will be quickly introduced in this presentation. (Important for project trial run.)

1

<!-- Slide number: 3 -->

![](Picture7.jpg)

![](Picture6.jpg)
# Data Exchange

### Notes:

<!-- Slide number: 4 -->
# Data Exchange for fiti Design Service
Try Run
Final Check
3

<!-- Slide number: 5 -->
# Back-end APR Service
1
Hand-off data at Preliminary Design Handoff
Data Release to Customer after Preliminary Physical Design
Hand-off data at Final Design Handoff
Data Release to Customer after Physical Design Implementation
Exchange Method: Through FTP/e-mail after encript/zip with password
2
3
6
4

<!-- Slide number: 6 -->
# Hand-off data at Preliminary Design Handoff
Customer Deliverable
Initial Netlist (Mandatory)
Netlist is nearly frozen
In Verilog format
Verified by uns
Naming-clean (script to generate naming-clean netlist: <install_dir>/script/dc )
Assign: Customer must use uns to replace it by buffer and run pre-layout simulation before submitting to UniChip.
Spare Cell List (Optional)
Format is defined in “fiti Spare Cell Insertion Guide”
Complete Pin Sequence File (Mandatory)
Format is defined in Design kit for ASIC Design Service – User’s Manual , chapter “FT_PAD_ASSIGN”
 1   Customer->fiti
5

<!-- Slide number: 7 -->
# Hand-off data at Preliminary Design Handoff
 1   Customer->fiti
Customer Deliverable
Layout Constraint File (Mandatory)
Must include floorplan diagram and clock tree diagram
<install_dir>/demo/template/floorplan
<install_dir>/demo/template/constraint
The format is defined in Chapter 3.
Timing Constraint File (Mandatory)
One for APR timing optimization. One in each mode for STA.
In *.sdc and *.wscr format
Include clock definition, input/output delay, input transition, output load, and timing exceptions.

write_script –output < Timing_Constraint_File.wscr >
write_sdc <Timing_Constraint_File.sdc>

6

<!-- Slide number: 8 -->
# Hand-off data at Preliminary Design Handoff
 1   Customer->fiti
Customer Deliverable
Ball Assignment Request (Optional)
special consideration on BGA package (for example, pin location)
Detail in Design kit for ASIC Design Service – User’s Manual, chapter “FT_PAD_ASSIGN”
ROM Code File (Mandatory)
<install_dir>/demo/template/rom
When the customer change the ROM code, it must be delivered again.

7

<!-- Slide number: 9 -->
# Data Release to Customer after Preliminary Physical Design
 2   fiti->Customer
fiti Deliverable
Custom Wire Load Model
For logic re-synthesis
One model for one physical group
A Design Compiler Script to Update the Custom Wire Load Model
Set Load File
For logic re-synthesis
Preliminary SDF File
Clock tree is ideal/propagated depend on try-run stage
8

<!-- Slide number: 10 -->
# Hand-off Data at Final Design Handoff
 3   Customer->fiti
Customer Deliverable
Final Netlist (Mandatory)
In Verilog format.
Must be validated by uns.
Both function and timing must be frozen.
Naming-clean (script to generate naming-clean netlist: <install_dir>/script/dc )
Assign: Customer must use uns to replace it by buffer and run pre-layout simulation before submitting to UniChip.
Spare Cell List (Mandatory)
Format is defined in “fiti Spare Cell Insertion Guide”

9

<!-- Slide number: 11 -->
# Hand-off Data at Final Design Handoff
 3   Customer->fiti
Customer Deliverable
Complete Pin Sequence File (Mandatory)
Format is defined in Chapter 5.
Layout Constraint File (Mandatory)
Format is defined in Chapter 3.
<install_dir>/demo/template/floorplan
<install_dir>/demo/template/constraint
Complete Timing Constraint File (Mandatory)
In *.sdc and *.wscr format

write_script –output < Timing_Constraint_File.wscr >
write_sdc <Timing_Constraint_File.sdc>

10

<!-- Slide number: 12 -->
# Hand-off Data at Final Design Handoff
Customer Deliverable
ROM Code (Mandatory)
<install_dir>/demo/template/rom
When the customer change the ROM code, it must be delivered again.
UTPG Cycle-Based Test Vectors (Mandatory)
Include a test bench, a test pattern file, an intermediate test pattern file, and a log file.
Refer to Chapter 8.
If ROM code is changed, please update the utpg pattern with new ROM code.
At post-layout simulation phase, can only update the test bench and intermediate test pattern due to strobe time change.

 3   Customer->fiti
11

<!-- Slide number: 13 -->
# Hand-off Data at Final Design Handoff
Customer Deliverable
SDF File for Pre-layout Simulation (Mandatory)
Contain 3 corners timing.
SDF must consistent with the netlist.
Clock network: Must use set_clock_transition for a reasonable transition at the pin of flip-flops.
High fanout net: Must use high_fanout_threshold and high_fanout_net_capacitance to estimate the transition and delay.

Simulation Script and Log Files (Optional)
This will assure the consistency of simulation between fiti and customer.

 3   Customer->fiti

high_fanout_threshold 100
high_fanout_net_capacitance  0.00001
write_sdf –output <SDF File >

12

<!-- Slide number: 14 -->
# Data Release to Customer after Physical Design Implementation
 6   fiti->Customer
fiti Deliverable
Netlist File
Include clock tree and high fanout buffer cells.
For post-layout simulation and STA.
SDF File
Contain all sign-off corners timing.
Consistent with the netlist.
For post-layout simulation and STA.
Set Load File
For STA.

13

<!-- Slide number: 15 -->

![](Picture7.jpg)

![](Picture6.jpg)
# UNS

### Notes:

<!-- Slide number: 16 -->
# Overview
It is a screener in respect of design quality
It is used to identify the potential problems that may violate fiti’s engineering rules
It is used to assist the engineers to fix problems at the early design stage
Customer must use this utility to check gate-level netlist and fix the problems before netlist delivery
15

<!-- Slide number: 17 -->
# Functional Specification
Design Content and Syntax Check
command, syntax, model consistency between verilog and dot library
Design Specification Report
design contents are grabbed in different views of engineers
Engineering Rule Check
it is convenient for the users to identify potential problems and avoid mistake during  service flow
such that designs can enter fiti’s design service flow fast and smoothly
Report Summary
profile of design contents, main findings of possible errors, complexity evaluation and leakage power consumption
16

### Notes:
------------------ Command & Syntax --------------------
Notify:
- error command usage
- syntax error (parsing gate-level netlist or dot library)
- unmapped logic (verilog fail to link with dot library)
-----------------------------------------------------------------
- lengthy module name or signal name
- single bit signal name with bus notation
- assign statement
- modules referenced multiple times
- connection mismatch (e.g. inconsistency on bus width)
- redundant signals or logics (empty module, port)
- inconsistency between netlist and dot library
----------- Design Specification Report --------------
Report:
- referenced module (for I/O pad, hard macro and core cells)
- macro cell instance (memory or hard macro)
- port specification (connectivity and I/O pad utilization)
- fan-out distribution (complexity of internal wire)
- design hierarchy (inst, gate count and FFs for DFT purpose)
- leakage power consumption
------------------ Engineering Rule Check --------------------
Check:
- memory block (incomplete chip enable or clock gating)
- spare cell (profiling and don’t touch SDC constraint)
- sub design block (large/empty/unmapped sub design)
- high fan-out net (into non-clock tree and clock tree)
- timing arcs (feedback, lengthy path, generated clock)
- cell connectivity (floating input, multiple drivers)
- port connectivity (floating and ambiguous connection)
- pad cell (illegal multiple bond pads or used internally)
- constant (signals tied to 1’b0 /1’b1)
- clock domain (non-driven, profiling of clock tree cells)
- analog path (digital cells inserted on analog path)

<!-- Slide number: 18 -->
# Application Flow

If one of the following command options is given:
-spare_spec <file>
-analog_libpin <list>
17

<!-- Slide number: 19 -->
# Input/Output Files
Input Files
Gate-level Netlist
Synopsys Dot Library
Output Files
Execution Log
Validated Netlist
SDC Constraint Files (Optional)
Report

It is quite different from the previous one
If one of the following command options is given:
-spare_spec <file>
-analog_libpin <list>
18

<!-- Slide number: 20 -->
# Command Usage (1/5)
Command Usage
uns [options]
Official Command Options
-lib <file>
Read dot library (.lib) model for standard core cell. This command option can be specified multiple times with a proper file path. Multiple dot library files can also be designated within braces per this command option.
-iolib <file>
Read dot library (.lib) model for I/O cell. This command option can be specified multiple times with a proper file path. Multiple dot library files can also be designated within braces per this command option.
-mlib <file>
Read dot library (.lib) model for memory and hard-macro. This command option can be specified multiple times with a proper file path. Multiple dot library files can also be designated within braces per this command option.
those command options will affect the calculation for cell area
19

<!-- Slide number: 21 -->
# Command Usage (2/5)
-netlist <file>
Read gate-level verilog netlist. This command option can be specified multiple times with a proper file path. Multiple gate-level netlist files can also be designated within braces per this command option.
-ref <module>
Specify a basis gate for computing equivalent gate count. Please specify the smallest 2-input NAND gate as the reference cell. If the reference cell is not well specified, the equivalent gate count will be wrong.
-buf <module>
Replace the assign statement with the specified buffer. In fiti design service flow, “assign” statement is not allowed in the validated netlist. One should clean up the “assign” statement either through this option or refer to Chapter 2 to avoid “assign” statement during synthesis. If customer uses this option to clean up the “assign” statement, he/she should pay more attention to the gate count and timing increase due to buffer replacement.
20

<!-- Slide number: 22 -->
# Command Usage (3/5)
-top <module>
Specify the top module name.
-file <command_file>
Read and perform the host command options from the specified command file.
-skip_escape_char
Skip escape character '\' check (used for post-layout only). After performing P&R, the post-layout netlist may have back-slash characters. Customer can use this option to skip the checking of escape character during ECO flow. In fiti design service flow, back-slash characters are not allowed in pre-layout netlist. Customer can refer to Chapter 2 to remove the back-slash character in pre-layout stage.
-clock < list >
Specify a list of hierarchical pin, port or net name as the clock roots for analyzing clock domain and identifying non-driven clock pins. A detail report ‘clock_tree_cell.rpt’ for clock tree cells will be generated automatically.
21

<!-- Slide number: 23 -->
# Command Usage (4/5)
-max_block_size <digit>
Specify a threshold for identifying the large sub-block; the default value is 300,000 instances.
-max_logic_level <digit>
Specify a threshold for identifying the long path whose logic level is larger than the threshold. The default value is 50.
-max_fanout <digit>
Specify a high fan-out threshold. The default value is 100.
-analog_libpin <list>
Specify a list of library pin of analog design for recognizing the analog instances and identifying those illegal insertions of digital cells on analog path. A don’t touch SDC constraint ‘analog_path.sdc’ for those enumerated analog designs will also be generated automatically. One can use the SDC constraint during P&R to set don’t touch for the connections between analog macros.
22

<!-- Slide number: 24 -->
# Command Usage (5/5)
-spare_spec <spare_list>
An example of <spare_list> file is shown below, where the hierarchical instance name of spare cells and their corresponding referenced library cell types are specified. If this command option is specified, UNS enumerates those spare cells described in the spare_list and summarizes the checking result in check_spare_cell section of the UNS report. A don’t touch SDC constraint ‘spare_cell.sdc’ for those enumerated spare cells will also be generated automatically.
-opath <directory>
Specify the output directory.
-verbose
This option will lead the UNS to generate detail report.
-help
Show command usage.
u_mck/UF5_spare      (DFFX1)
u_mck/US01_spare     (AND2X1)
u_uck/m4/US01_spare  (INVX1)
u_uck/m4/US04_spare  (INVX1)
u_uck/m2/UX1         (XOR2X1)
u_uck/U1/U2          (INVX1)
u_uck/U1/U3          (INVX1)
23

<!-- Slide number: 25 -->
# Command File Example
# import dot library (standard and I/O cell)
-lib {
    /testcase/uck/lib/tsmc25.lib
}
-iolib {
    /testcase/uck/lib/tpz873n.lib
    /testcase/uck/lib/tpd773sn_analogwc.lib
    /testcase/uck/lib/tcb013ghpwc.lib
}
# import dot library (memory and hard-macro)
-mlib {
    /testcase/uck/lib/ta25sd8k_8.lib
    /testcase/uck/lib/AVA2RAM8X2.lib
    /testcase/uck/lib/ARS2REG64X16C2.lib
}
# import gate-level netlist
-netlist {
    /testcase/uck/netlist/uck.v
    /testcase/uck/netlist/module.v
}

# specify top module
-top top

# constraint design
-max_fanout 20
-max_logic_level 40
-max_block_size 100000
-buf BUFX1
-ref NAND2X1
-skip_escape_char

# specify spare spec.
-spare_spec /testcase/uck/spare_list

# specify clock roots
-clock {
    UCK
    MCK
}

#specify analog library pin
-analog_libpin {
    PDIANA2PU/C
    UBGR_3311_180_FLAT/VBG
    UBGR_3311_180_FLAT/BGOK
}
One can apply this command file with ‘uns –f sample.cmd’ command
24

<!-- Slide number: 26 -->
# UNS Log (1/2)
The default file name is <top>_uns.log, where <top> is the top module name of the specified design
This file shows the invalidated command usages, execution time, commands that are performed progressively and possible errors in design content
such as inconsistency with library, one bit signal with bus notation, inconsistency on pin connection, unmapped logic or combinational feedback loop, …
Finally, a summary of the existing problems is provided and the associated sections are designated indirectly
25

<!-- Slide number: 27 -->
# UNS Log (2/2)
Netlist screener v3.0b6 2006/01/11
Copyright (C) 2006, fiti Corp.
All Rights Reserved.

(2006/01/11-15:55:54) import design ...
import library /testcase/uck/lib/tsmc25.lib ...
import /testcase/uck/netlist/module.v ...
import /testcase/uck/netlist/uck.v ...
…
warning: cell 'm1' reference to 'LOOP' multiple times (LNT-20)
warning: cell 'm2' reference to 'MBRANCH' multiple times (LNT-20)
…
initiate annotator ...
initiate case analysis ...
info: apply 'NAND2X1(area:17.28)' as the base gate for computing equivalent gate count
info: set high_fanout_threshold = 10
info: set high_fanout_capacitance = 0.200000
info: set max_logic_level = 10
…
(2006/01/11-15:55:59) check design rule ...
warning: detect feedback loop at 'u_mck/u_tmod/m0/U1/A' (CHK-05)
warning: detect feedback loop at 'u_uck/m4/m0/U1/A (CHK-04)'
…
(2006/01/11-15:56:00) summary ...
fatal: identify 2 instantiated pins violate library port spec., see uns log file (CHK-10)
fatal: identify 4 mismatched port connection, see uns log file (CHK-11)
error: identify 1 dot library issues, see uns log file (CHK-13)
error: identify 4 unmapped logics, see 'check_sub_design' section on uns report (CHK-15)
error: identify 12 error pad connection, see 'check_pad_cell' section on uns report (CHK-23)
error: identify 5 error spare cell, see 'check_spare_cell' section on uns report (CHK-26)
warning: identify 2 incomplete clock gating, see 'check_memory' section on uns report (CHK-27)
…
total 16 error, 31 warning statements
You should clarify those warning and error issues first before you use the UNS report!

26

<!-- Slide number: 28 -->
# UNS Report (1/4)
Design Content
Analysis of Module Reference
Analysis of Cell Reference
Analysis of Primary Port
Analysis of Fan-out Distribution
Analysis of Design Hierarchy
Analysis of Memory (Incomplete Clock Gating on Memory Block)
Analysis Spare Cell (Enumeration of Spare Cell)
27

<!-- Slide number: 29 -->
# UNS Report (2/4)
Engineering Rule Check
Check Sub Block
Check High Fan-out Net
Check Timing Arc
Check Cell Connectivity
Check Sub-module Port Connectivity
Check Pad Cell
Check Constant Signal
Check Clock Domain
Check Analog Path
28

<!-- Slide number: 30 -->
# UNS Report (3/4)
Report Summary
provides a guide to each section that may indicate the potential problems
29

<!-- Slide number: 31 -->
# Report File Format
File Header

Profiling
***************************************************************************
Report : port
          -flatten
Design : top
Version: Sep 13 2005
Date   : Tue Sep 13 13:35:50 2005
Comment:
    port - primary port name
    dir  - port direction
    num  - number of connection
    attr - attribute
             b block level
             n non pad cell
             m multi-bond port
             f floating
    conn - connected pin
***************************************************************************
report type
top design
execution time

description of profiling

description of attribute
port                        dir   num attr  conn
-------------------------------------------------------------------------
EMPTY                        in     1 f      (floating)
MCK                          in     2       pin_MCK/XIN (PDXOE3DG)
UCK                          in     2       pin_UCK/PAD (PDUDGZ)
MSI                          in     2       pin_MSI/PAD (PDUDGZ)
MBOND1                       in     3 mn    u_assign_1/Y (BUFX1)
MBOND2                       in     2 n     u_assign_1/A (BUFX1)...
-------------------------------------------------------------------------
total 22 ports
floating
multi-bound port & non-pad cell
non-pad cell
30

<!-- Slide number: 32 -->
# Design Summary (1/3)
UNS first summarizes design content info, engineering rule check and clock domain analysis, then classifies them into several groups associated with proper section labels respectively.
Finally it designates the analyzed coverage, the interconnected congestion and leakage power consumption
base gate for computing equivalent gate: NAND2X1

Description                          Value           Section
----------------------------------------------------------------------
eq. gates of macro cells:            198116.05       [reference,cell]
eq. gates of pad cells:              47513.55        [reference]
eq. gates of standard cells:         868.26          [reference]
eq. gates of sequential cells:       455.68          [reference]
eq. gates of combinational cells:    412.58          [reference]

You may lookup to those sections for more detail
Command option ‘-lib’, ‘-iolib’ and ‘-mlib’ will affect the computing of area and gate count
31

<!-- Slide number: 33 -->
# Design Summary (2/3)

You may lookup to those sections for more detail
number of macro cells:               10              [reference,cell]
number of pad cells:                 24              [reference]
number of standard cells:            420             [reference]
number of sequential cells:          80              [reference]
number of combinational cells:       340             [reference]
number of bufs for assign statement: 5               [reference]
number of sub designs:               21              [hierarchy,check_sub_design]
number of large sub designs:         2 (>=100)       [hierarchy,check_sub_design]
number of empty sub designs:         4               [hierarchy,check_sub_design]
number of internal nets:             361             [fanout_distribution]
number of flattened primary ports:   22              [port,check_port_connection]
number of signals driven by tie-hi:  6               [check_constant]
number of signals driven by tie-lo:  13              [check_constant]
number of signals tied to 1'b1:      59              [check_constant]
number of signals tied to 1'b0:      134             [check_constant]
number of combinational feedbacks:   4               [check_timing_arcs]
number of high fanout exclude CKT:   15 (>=5)        [check_high_fanout_net]
number of high fanout on CKT:        5 (>=5)         [check_high_fanout_net]
number of high logic level:          23 (>=10)       [check_timing_arcs]
number of possible generated clocks: 15              [check_timing_arcs]
number of clock tree cells:          177             [check_clock_domain]
number of spare cells:               5               [check_spare_cell]
number of tri-state buses:           4               [check_cell_connection]
number of incomplete clock gating:   2               [check_memory]
32

<!-- Slide number: 34 -->
# Design Summary (3/3)
error floating input pins:           210             [check_cell_connection]
error floating inout pins:           4               [check_cell_connection]
error output tie to constant:        11              [check_cell_connection]
error unmapped logics:               4               [check_sub_design]
error inference in assign statement: 0               [reference]
error non tri-state buses:           16              [check_cell_connection]
error tri-state bus:                 1               [check_cell_connection]
error port connection:               14              [port,check_port_connection]
error pad connection:                12              [check_pad_cell]
error spare cell:                    5               [check_spare_cell]
error non-driven clock pins:         45              [check_clock_domain]
error digital/analog connection:     1               [check_analog_path]
ratio of reached_cells/leaf_cells:   83.46%          [check_timing_arcs,check_cell_connection]
ratio of internal_nets/leaf_cells:   0.80            [fanout_distribution,check_cell_connection]
ratio of connections/internal_nets:  3.41            [fanout_distribution]
leakage power consumption:     480.44(nW)/437.46(nW) [leakage_power]

imply the testability and design complexity
worst case
consider native constant propagation that will affect those timing/power libraries with conditional leakage table (e.g. TSMC .13um)
33

<!-- Slide number: 35 -->

![](Picture6.jpg)

![](Picture7.jpg)
# FT_PAD_ASSIGN

### Notes:

<!-- Slide number: 36 -->
# Overview
Check the format of pin sequence file
Check the consistency of IO cells between pin sequence file and verilog netlist
Generate APR/PACKAGE diagram
Generate IO constraint file for APR tools
Generate Block constraint file for APR tools

For fiti Internal Use
35

<!-- Slide number: 37 -->
# Flow Diagram

1. APR Pad Diagram
2. Package Diagram
3. Stagger I/O power & ground check
    (for BGA package)
4. Log file
5. Block I/O Constraint file
6. Chip I/O Constraint file

Pin Sequence file  <project>.list

Verilog Netlist
Upad_Assign

Configuration file

Pin Sequence file (complete) <project>.list.new

36

<!-- Slide number: 38 -->
# Command Usage
ft_pad_assign [Options] configuration_file
Options:
  -apr_diagram		: generate pin diagram for APR.
  -c				: Check the consistency of IO cells between pin  sequence 			  file and verilog netlist and generate complete pin 				  sequence file.
  -package_diagram	: generate pin diagram for package.
  -stagger		: stagger IO pad.
  -help			: print this help message.
Configuration_file  file format:
  PIN_SEQUENCE <FILE_NAME>
  VLOG_NETLIST <file_name1> <file_name2>…

				Example:
					PIN_SEQUENCE pin.list
					VLOG_NETLIST apr.v

37

<!-- Slide number: 39 -->
# Command Usage (cont.)
Generate APR Diagram
Command: ft_pad_assign  -apr_diagram  <configuration_file>

![](Picture4.jpg)
  pad8 , 32 ,48 are   powercut cells
  pad10 ,11 are
   double bonded to
   pin 9
  pad20 , 21 are
   double bonded to
   pin 18
38

<!-- Slide number: 40 -->
# Command Usage (cont.)
Generate PKG Diagram
Command: ft_pad_assign  -package_diagram  <configuration_file>

![](Picture6.jpg)
9
18
31
-  pin 31 is a
   No Connection pin
39

<!-- Slide number: 41 -->
# Pin Sequence File Example
PRODUCTION NO.:PROJECT0001A_A4APKG_TOP_LEFT_PIN : 1PACKAGE : 64PQFP 16 16 16 16VERSION: A1_060303PIN_NUM 	DIE_PAD_NUM 	PIN_NAME	 IO_CELL_NAME 	LOCATION    DIRECTION    LOAD    SLEW    SSO1 	0 		NC 	- 		L 	- 	-         - 	-2 	1 		MCK 	PDXOE3DG 		L 	I 	-         2.0 	-3 	2 		MSI 	PDUDGZ 		L 	I 	-         2.0 	-4 	3 		MSO 	PDO08CDG 		L 	O 	50.0    - 	A5 	4 	VDD%C%VDDC01 	PVDD1DG 		L 	P 	-         - 	-6 	5 		MBS 	PDUDGZ 		L 	I 	-         2.0 	-7 	6 		MBC 	PDUDGZ 		L 	I 	-         2.0 	-8 	7 	VDDIO%IO%VDDIO01 	PVDD2DG 		L 	P 	-         - 	-8	8 	VDDIO%IO%VDDIO02 	PVDD2DG 		L 	P 	-         - 	-9 	9 		MBR 	PDUDGZ 		L 	I 	-         2.0 	-10 	10 	VSSCIO%CIO%VSSCIO01 	PVSS3DG 		L 	G 	-         - 	-11 	11 		MRD 	PDO08CDG 		L 	O 	50.0    - 	A12 	12 		MBO 	PDO08CDG 		L 	O 	50.0    - 	A13 	13 	VSSIO%IO%VSSIO01 	PVSS2DG 		L 	G 	-         - 	-14	14	 	WEB 	PDUDGZ 		L 	I 	-         2.0 	A15	15 		CSB 	PDUDGZ 		L 	I 	-         2.0 	A0	16 	                   POWERCUT01 	PRDIODE 		L 	- 	-         - 	-16	17 		D7 	PDUDGZ 		L 	I 	-         2.0 	B17	18 		D6 	PDUDGZ 		B 	I 	-         2.0 	B18	19 		D5 	PDUDGZ 		B 	I 	-         2.0 	B19 	20 		D4 	PDUDGZ 		B 	I 	-         2.0 	B20	21 	VDDIO%IO%VDDIO03 	PVDD2DG 		B 	P 	-         - 	-21 	22 		D3 	PDUDGZ 		B 	I 	-         2.0 	B22 	23 		D2 	PDUDGZ 		B 	I 	-         2.0 	B23 	24 	VSS%C%VSSC01 	PVSS1DG 		B 	G 	-         - 	-23 	25 	VSSIO%IO%VSSIO02 	PVSS2DG 		B 	G 	-         - 	-24 	26 		D1 	PDUDGZ 		B 	I 	-         2.0 	B

Not connection Pin
Double
Bound
Pin

Don’t
Bound
Pad

40

<!-- Slide number: 42 -->
# How to write pin sequence file
General Notices
-  All statements are case sensitive.
  The default time & capacitance units are (ns) & (pf) ,
    respectively.
-  Reserved keywords :
   PACKAGE_TOP_LEFT_PIN, PACKAGE , VERSION, PIN_NUM , DIE_PAD_NUMBER, PIN_NAME , IO_CELL_NAME , LOCATION , DIRECTION , LOAD , SLEW , SSO , POWERCUT , NC.
-  Reserved character: “ % ” , “ / ”.

For power & ground
Ex:VDDIO%IO%VDDIO01
For muxed pin
Ex: BIST_E/RTE_HL
41

<!-- Slide number: 43 -->
# How to write pin sequence file (cont.)
PKG_TOP_LEFT_PIN & PACKAGE
  PKG_TOP_LEFT_PIN: <num>    the topmost pin in the left side

  PACKAGE:    <pin number> <type> <pin number of L> <pin number of B>
    <pin number of R> <pin number of T>    ex: PACKAGE:208QFP 52 52 52 52
Top
Top_Left

 1 2 352

Left
Right
…
Bottom
42

<!-- Slide number: 44 -->
# How to write pin sequence file (cont.)
LOAD & SLEW & SSO
-  LOAD :    The default value is 50 (pf)	ps : specify a dash (-) for  non-output pins
-  SLEW :    The default value is 2(ns)	ps : specify a dash (-) for  non-intput pins
-  SSO (for power check):
   Simultaneously Switching Output needs to be grouped together by
    labeling them with the same character.	ps : specify a dash (-) for  non-output pins

43

<!-- Slide number: 45 -->
# How to write pin sequence file (cont.)
power_ground_type
Power (Ground) Types:
Type1: Power (Ground) cell for Core        C            ex: PVDD1DG
Type2: Power (Ground) cell for  I/O         IO           ex: PVDD2DG
Type3: Power (Ground) cell for Core & I/OCIO     ex: PVDD3DG
44

<!-- Slide number: 46 -->
# How to write pin sequence file (cont.)
Power/Ground Pad instance name
<instance name> : the instance name of the corresponding
                                 power/ground or powercut cell declared in the Verilog netlist.
(Verilog netlist)

![](Picture5.jpg)

should be empty !

45

<!-- Slide number: 47 -->

![](Picture5.jpg)

![](Picture6.jpg)
Coding Guidelines for Gate-level Verilog Netlist &Design Compiler Naming Rule

<!-- Slide number: 48 -->
# General Rules (1/2)
All names must begin with an alphabetical character.
No back-slash char (“\”)
No “assign” statement
Use “1’b0” and “1’b1” instead of “supply0” and “supply1”.
All I/O cells must be declared in the top module, but the top module port list MUST NOT include any power and ground pins.
Use “call by reference” instead of “call by position” when invoking a cell library or a module. For example, use “BUF1 U001 (.I(net1), .Z(net2))” instead of “BUF1 U001 (net1, net2)”.

47

<!-- Slide number: 49 -->
# General Rules (2/2)
Neither behavioral statement nor module in the gate-level netlist. With exception in hard-macros. Adding “`celldefine” and “`endcelldefine” at the top and bottom, respectively.

48

<!-- Slide number: 50 -->
# How to Declare the I/O Cells Used in the Verilog Netlist (1/3)
General Input, Output, and Bi-Direction Cells
To facilitate debugging, each instance of an I/O cell is better named as PIN_<io>_<pin_name>, e.g.  in the page 51., where <io> must be one of I, O, B and X.
All I/O cells must be declared in the top module, e.g.  in the page 51.
Except power/ground and power cut cells, all pin names of all remaining I/O cells specified in the pin sequence file must have corresponding port names declared in the top module, e.g.  in the page 51 and  in the page 52.

49

<!-- Slide number: 51 -->
# How to Declare the I/O Cells Used in the Verilog Netlist (2/3)
Power/Ground and Special I/O cells
No naming restriction on the instance name of a power/ground pad. A power/ground pin must be named as: <pkg_apr_text>%<power_ground_type>%<instance name>, e.g.  in the page 51 and  in the page 52.
Multiple power (ground) pads bonded together should be declared multiple times, e.g.  in the page 51 and 52.
For power/ground pads, the arguments of the corresponding I/O cells must be empty, e.g.  in the page 51.
For the analog I/O input, output and bi-direction cells, the declaration scheme is the same as general input, output, and bi-direction cells.

50

<!-- Slide number: 52 -->
# Top Module Example

![](Picture13.jpg)
51

<!-- Slide number: 53 -->
# Simple Pin Sequence Mapping

![](Picture4.jpg)
52

<!-- Slide number: 54 -->
# Naming Rule Script and Setting in Synopsys Design Compiler (1/2)
Setting for eliminating the netlist “assign” problem in Synopsys Design Compiler before compile:
	      dc_shell> verilogout_single_bit = “false”
	      dc_shell> verilogout_equation = “false”
	      dc_shell> verilogout_no_tri = “true”
	      dc_shell> set_fix_multiple_port_nets -all -buffer_constants
fiti provides the Design Compiler naming rule scripts called UniChip _name_rule.scr, UniChip_name_rule_before_dc20030312.scr and UniChip _name_rule_after_dc20030312.scr in the $UNICHIP_HOME/script/dc directory. The UniChip _name_rule.scr refers to the default script UniChip _name_rule_after_dc20030312.scr.

53

<!-- Slide number: 55 -->
# Naming Rule Script and Setting in Synopsys Design Compiler (2/2)
Before write out netlist (DC version after 20030312):
	dc_shell> include $UNICHIP_HOME/script/dc/unichip_name_rule.scr

54

<!-- Slide number: 56 -->
Summary
fiti in-house proprietary design kits for project cowork
Utility
UNS          		:  Netlist screener
UTPG          		:  Test pattern translator
FT_PAD_ASSIGN 	:  Pad assignment file translator

Script
PrimeTime QoR
Design Compiler Naming Rule

Document
Design kit for ASIC Design Service – User’s Manual
fiti Static Timing Analysis User Guide
fiti Spare Cell Guide

fiti will delivery the fiti Design Handoff Package to SONY after kick-off
meeting. UNS/FT_PAD_ASSIGN’s detail are described in Design kit for ASIC
Design Service – User’s Manual

55
