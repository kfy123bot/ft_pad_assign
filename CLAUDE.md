# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Test all CSV examples (output to test_out/)
make test_py

# Quick single-file test
make run

# Run single file manually
python3 bin/ft_pad_assign.py -list examples/qfn56.8803.GPIO.0505_v3.pgpin_list.csv -v examples/va8803.vg -all -o output

# Clean generated files
make clean
```

**Dependencies:** `reportlab` (PDF generation), `openpyxl` (Excel generation). Install: `pip3 install reportlab openpyxl`

## Development Workflow

**NEVER** commit or push unless explicitly asked. When making changes:
1. Edit code
2. Run `make test_py` to verify
3. Report results — stop there

## Architecture

Three Python tools in `bin/`:

| Tool | Purpose |
|------|---------|
| `ft_pad_assign.py` (~2740 lines) | Main tool: parse pin lists, generate PDFs and constraint files |
| `gen_spec_pdf.py` | Generate CSV input specification PDF doc |
| `gen_ug_excel.py` | Generate user guide Excel doc |

Main tool data flow:

```
Input File (.csv / .pin_list)
       │
       ▼
   Parser  ──→  self.header  (dict: PRODUCTION NO, PACKAGE, DIE_SIZE, etc.)
    (L96)       self.data    (list[dict]: one dict per pin row)
                self.die_size (tuple[int,int] | None)
       │
       ├──── PDFGen  (L740)  ──→  PKG / APR / Combined PDFs
       ├──── Writer  (L1521) ──→  .new, .new.csv, .inn.const, .icc2.const
       └──── Checker (L1495) ──→  _stagger.rpt
```

**Parse order** (in `parse_list()`):
```
ring_shift → reindex_pkg_num → reassign_pkg_loc → reassign_die_loc → sanity_check → reorder_and_reindex_apr_data → parse_die_size
```

## Pin List Format

CSV or tab-separated. Header section (`KEY : VALUE`), then data table.

### Required Headers
- `PRODUCTION NO` (or `PROJECT NO`) — project name, becomes output filename prefix
- `PACKAGE` — e.g. `48QFN 12 12 12 12` (total L B R T pin counts)
- `VERSION`

### Optional Headers
- `DIE_SIZE : 2500x2000` — die dimensions in um (enables aspect-ratio frame scaling)
- `PKG_SIZE : 7000x7000` — package body in um (overrides QFN lookup table)
- `PKG_TOP_LEFT_PIN : N` — ring shift: pin N becomes L-side pin 1

### Data Columns (10 fields, aliases supported)
`PKG_NUM`, `DIE_NUM`, `PIN_NAME`, `IO_CELL_NAME`, `PKG_LOC`, `DIE_LOC`, `DIRECTION`, `LOAD`, `SLEW`, `SSO`

Field aliases are defined in `FIELD_ALIASES` (L70) — e.g. `PIN_NUM` → `PKG_NUM`, `DIE_PAD_NUM` → `DIE_NUM`.

## Special Pin Types

| Type | Condition | PKG PDF | APR PDF | Combined |
|------|-----------|---------|---------|----------|
| NC | `PIN_NAME=NC` | Black box | Skip | Black box (PKG frame); APR skip |
| DOWNBOND | `PIN_NAME=DOWNBOND` | Blue box | Skip | Blue box (PKG frame only) |
| POWERCUT | `PIN_NAME=POWERCUT` | Skip | Black box | — |
| Invalid PKG | `PKG_NUM='0'` or `'-'` | Skip | — | — |
| Invalid APR | `DIE_NUM='0'` or `'-'` | — | Skip | Skip |
| Inner Bond | `PKG_NUM='D1.xx'` or `(D1.xx)` | — | — | Extended pin + red wire |

### Inner Bond (D1.xx)

Direction: `D1.77` + `DIE_NUM=42` → wire from 77→42. With parens `(D1.77)` → reversed: 42→77.

Symmetry check: if A→B and B→A both exist, draw solid line; otherwise dashed + ERROR log.

Multiple wires on same (src, dst) get parallel offsets of ±2 pts.

### Ground Symbol (DOWNBOND)

When `PKG_NUM=0`, `DIRECTION=G`, valid `DIE_NUM`: draw ground symbol (blue triangle) extending outward from APR pin.

## PDF Generation

Three modes: standalone PKG, standalone APR, Combined (PKG + APR + wires).

### Frame Dimensions
- Default: PKG=280pt square, APR=200pt square (for standalone PDFs); PKG=350pt for Combined
- With `DIE_SIZE`: APR becomes rectangular (preserving die aspect ratio), PKG scales by body/die ratio
- With `PKG_SIZE`: non-square PKG frames supported

### Key Conventions
- Pin side detection: cumulative counts from `PACKAGE` header (L→B→R→T order)
- Wire colors: grey (default), red (Power `DIRECTION=P`), blue (Ground `DIRECTION=G`)
- Label auto-shrink: if PIN_NAME text would exceed frame boundary, font shrinks (max 2pt reduction)
- APR pins in Combined PDF: `label_inside=False` (placed at outer edge of APR frame)
- Scale bar: bottom-right of every PDF, showing physical dimensions in um

### QFN Body Size Lookup (`QFN_BODY_SIZES`, L86)
Maps pin count → body size in mm. Used when `PKG_SIZE` header is absent. 0.5mm pitch assumed; 0.4mm pitch auto-detected when die exceeds standard body.

### QFN Physical Dimensions (`QFN_PHYSICAL_SPECS`, L100)
Source: JEDEC MO-220 specs in `docs/`. Stores `(body_mm, pitch_mm, pin_width_typ_mm, pin_length_typ_mm, exposed_pad_mm)` per body size. Used for accurate pin pad drawing in PDFs.

## DIE2 / DIE3 Overlay

Overlay additional dies (e.g. PSRAM, SRAM) on Combined PDFs. DIE2 uses brown, DIE3 uses teal.

### CLI Usage

```bash
# DIE2 only (CSV)
python3 bin/ft_pad_assign.py -list input.csv --die2 docs/JD1750_PSRAM.csv -combined -o out

# DIE2 + DIE3
python3 bin/ft_pad_assign.py -list input.csv --die2 docs/JD1750_PSRAM.csv --die3 examples/DIE3_example.csv -combined -o out

# DIE2 markdown (legacy) — requires --die2-loc
python3 bin/ft_pad_assign.py -list input.csv --die2 docs/JD1750_PSRAM.md --die2-loc="750,514" -combined -o out
```

### DIE2 CSV Format (`docs/JD1750_PSRAM.csv`)

```csv
DIE2_NAME : PSRAM_4MB
DIE_SIZE : 1000x972
DIE2_LOC : 750,514
PLACEMENT : R0

D2_NUM,D2_PAD_NAME,X,Y,D1_PAD,TYPE
D2.1,VSSQ,450.074,424.188,VSS_IOB,power
D2.2,DQS,450.074,359.188,PIO_24,signal
...
```

### DIE3 CSV Format (`examples/DIE3_example.csv`)

Same structure with `D3_NUM`, `D3_PAD_NAME`, `DIE3_NAME`, `DIE3_LOC` prefixes.

### CSV Header Fields

- `DIE2_NAME` / `DIE3_NAME`: display name in PDF (optional, defaults to "DIE2"/"DIE3")
- `DIE_SIZE`: die dimensions in um, WxH (required)
- `DIE2_LOC` / `DIE3_LOC`: bottom-left relative to DIE1 bottom-left (0,0) in um (required)
- `PLACEMENT`: rotation and flip, one of `R0`, `R90`, `R180`, `R270`, `R0_FLIP_X`, `R90_FLIP_X`, `R180_FLIP_X`, `R270_FLIP_X` (optional, default `R0`)
- Pad X,Y: relative to die center in um
- `D1_PAD`: connected DIE1 pad name (optional, empty = no connection)
- `TYPE`: connection type `signal`/`power` (optional, empty = no connection)

### Placement Behavior

- R0: no rotation (default)
- R90/R180/R270: entire die (frame + pads) rotates around die center
- FLIP_X: negates pad Y coordinates (mirrors B/T sides)
- `--die2-flip-x` CLI flag is **deprecated** — use `PLACEMENT : R0_FLIP_X` in CSV instead

## Output Files

| Flag | Outputs |
|------|---------|
| `-apr` | `*_apr.pdf` |
| `-pkg` | `*_pkg.pdf` |
| `-combined` | `*_combined.pdf` |
| `-c` | `*.new`, `*.new.csv`, `*_chip.inn.const`, `*_chip.icc2.const` |
| `-stagger` | `*_stagger.rpt` |
| `-all` | All of the above |

Innovus/ICC2 constraint files only generated when `-v` (verilog) is provided.

## Key Conventions

- Internal field name is always `DIE_PAD_NUM` regardless of whether input uses `DIE_NUM` or `DIE_PAD_NUM`
- Empty cells in CSV preserved as `""` internally; written as `"-"` in `.new` output
- `PKG_LOC` auto-filled when set to `"-"` — uses PACKAGE header counts
- `DIE_LOC` follows `PKG_LOC` pattern only when ring is shifted (`PKG_TOP_LEFT_PIN != 1`)
- All PDF text in the tool uses ReportLab's built-in Helvetica font

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make test_py` | Test Python version against all examples in `examples/` |
| `make test_die2` | Test DIE2 overlay on all examples |
| `make test_die3` | Test DIE2+DIE3 overlay on all examples |
| `make run` | Quick single-file test (qfn56 GPIO with verilog) |
| `make build` | Compile C++ version |
| `make test_cpp` | Compile and test C++ version |
| `make test_pl` | Test Perl version |
| `make test_all` | Test all three language versions |
| `make clean` | Remove binaries and `test_out/` |

## Documentation

- `docs/CSV_INPUT_SPEC.md` / `.pdf` — formal input format specification
- `docs/ft_pad_assign_ug.md` / `.xlsx` — user guide (Chinese)
- `00README.md` — modification changelog (session-by-session notes)
