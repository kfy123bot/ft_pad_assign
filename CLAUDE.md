# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# FPAD_ASSIGN Project Understanding

## Overview
FPAD_ASSIGN is an IC I/O pin assignment tool that reads pin list files and generates:
- PKG PDF: Package pin layout diagram
- APR PDF: Die pad layout diagram
- Combined PDF: PKG + APR with bonding wires
- Constraint files: Innovus (.inn) and ICC2 (.icc2)
- Stagger density report

## Pin List File Formats

### Tab-Separated Format (.pin_list)
```
PKG_NUM  DIE_NUM  PIN_NAME  IO_CELL_NAME  PKG_LOC  DIE_LOC  DIRECTION  LOAD  SLEW  SSO
```
- Headers in first rows before data
- `PKG_LOC` = L/B/R/T (package side location)
- `DIE_LOC` = L/B/R/T (die pad side location)
- `DIRECTION` = P (Power, red), G (Ground, blue), or other (grey)

### CSV Format (.csv)
- Same structure but comma-separated
- Header row: `PKG_NUM,DIE_NUM,PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO`
- May have embedded commas in header (e.g., `PACKAGE,,: 48QFN`)
- Use `csv.DictReader` with proper header handling

## Key Pin Types

### NC (No Connect)
- PIN_NAME = 'NC' or 'NC' in name
- PKG: Black filled rectangle
- APR: Black filled rectangle
- No bonding wire in combined PDF

### DOWNBOND (Bonding Wire Endpoint)
- PIN_NAME = 'DOWNBOND'
- PKG_NUM maps to package pin
- DIE_NUM = 0 (no die pad)
- PKG: Shows on package side, counts in pin sanity check
- APR: Does NOT show (no die pad)
- Combined: No bonding wire drawn

### Power/Ground Pins
- DIRECTION = 'P': Red rectangle (PKG, APR, Combined)
- DIRECTION = 'G': Blue rectangle (PKG, APR, Combined)

### Dynamic References (D1.xx)
- Format: (D1.77), D1.77, D1.91
- Reference other DIE_NUM values
- Resolution happens during re-indexing phase
- Updates `DIE_PAD_NUM` field

## PDF Generation

### Package Dimensions
- `edge_pkg = 350`: Outer PKG frame size (square)
- `edge_apr = 200`: Inner APR frame size (square)
- `box_len_pkg = 25`: PKG pin label box length (set in _draw_side_boxes)
- `box_len_apr = 15`: APR pin label box length (set in _draw_side_boxes)

### Pin Side Detection
Side determined by cumulative PIN_NUM counts from PACKAGE header:
```python
pkg_str = header.get('PACKAGE', '64 16 16 16 16')  # L B R T
pkg_parts = pkg_str.split()
expected = {'L': int(pkg_parts[1]), 'B': int(pkg_parts[2]),
            'R': int(pkg_parts[3]), 'T': int(pkg_parts[4])}
cumulative = 0
for s in ['L', 'B', 'R', 'T']:
    cumulative += expected[s]
    if pnum_int <= cumulative:
        side = s
        break
```

### Combined PDF Wiring (Line ~460-503)
Wire connects PKG pin directly to APR pin:
- `wire_start = p_pt` (PKG pin coordinate from _draw_side_boxes)
- `wire_end = a_pt` (APR pin coordinate from _draw_side_boxes)

Wire colors: grey (default), red (P), blue (G)

**Side detection**: Uses PKG_NUM to determine which side (L/B/R/T) the wire belongs to for color-coding purposes.

### APR Pins Position
Use `label_inside=False` to place APR pins at outer edge of APR frame (outside the frame, not inside).

## Sanity Check (Line ~180)
Validates pin count per side matches PACKAGE header:
- Counts unique PKG_NUM per side
- DOWNBOND PKG_NUM is included in count
- Total must equal sum of L+B+R+T from PACKAGE header

## CSV Parsing Notes
- Use `csv.DictReader` for proper header mapping
- Handle embedded commas in header (PACKAGE line)
- Strip trailing commas from header values
- Empty PIN_NAME shown as '-' in output

## Command Line Usage
```bash
python3 bin/fpad_assign.py -list <pin_list_file> -o <output_folder> -all
```

## Key Code Locations
- `_parse_pin_list_file()`: Line ~100 - Tab-separated parsing
- `_parse_csv()`: Line ~110 - CSV format parsing
- `generate_pkg_pdf()`: Line ~400 - Package PDF
- `generate_apr_pdf()`: Line ~370 - Die PDF
- `generate_combined_pdf()`: Line ~430 - Combined PKG+APR with wires
- `_draw_side_boxes()`: Line ~595 - Draws pins on frame edges
- `_reindex_die_pad_num()`: Line ~165 - Resolves D1.xx references