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
- Empty cells `""` are preserved as empty string (not converted to "-")
- When writing to .new file, empty strings are converted to "-"

## PIN_NUM / DIE_PAD_NUM 處理規則

| 條件 | PKG PDF | APR PDF | Combined PDF | 說明 |
|------|---------|---------|--------------|------|
| `PIN_NUM='0'` 或 `'-'` | **跳過** (不顯示) | - | - | PKG 無效腳位 |
| `DIE_PAD_NUM='0'` 或 `'-'` | - | **跳過** | **跳過** (無 APR pin) | APR 無效腳位 |
| `PIN_NAME=NC` | **顯示** (黑色方塊) | **跳過** | **跳過** | 無連接 |
| `PIN_NAME=DOWNBOUND` | **顯示** (藍色方塊) | **跳過** | **跳過** | 接地/bonding 端點 |
| `PIN_NAME=POWERCUT` | **跳過** (不顯示) | **顯示** (黑色方塊) | - | Power cut |
| `PIN_NUM='D1.xx'` | 不顯示 | 不顯示 | **延伸 APR pin 並用紅線連接** | Inner bound 連接 |

### Inner Bound (D1.xx) 處理

**核心規則**：xx 和 yy 都代表 DIE_NUM（晶粒墊片編號）

#### 方向規則

| 格式 | PIN_NUM | DIE_PAD_NUM | 連接方向 |
|------|---------|-------------|--------|
| `D1.xx` | `D1.77` | `42` | DIE_NUM(77) → DIE_NUM(42) |
| `(D1.xx)` | `(D1.77)` | `42` | DIE_NUM(42) → DIE_NUM(77) |

**詳細流程**：
1. 從 PIN_NUM 中提取 xx（DIE_NUM）
2. 使用 DIE_PAD_NUM 欄位的值作為 yy（另一個 DIE_NUM）
3. 根據括號判斷連接方向（無括號：xx→yy；有括號：yy→xx）
4. 兩個 DIE_NUM 對應的 APR pin shape 向 chip 中心延伸
5. 延伸 pin 保持原始形狀（空心），寬度縮小到 80%
6. 紅線連接兩個延伸後的端點
7. 僅在 Combined PDF 中顯示

#### Pin 延伸規則（L/R/B/T 四邊）

| Side | 原始形狀 | 延伸方向 | 座標計算 | 寬度 | 線寬 |
|------|---------|---------|--------|------|------|
| **L** | 水平 (len×th) | →（向右） | (x+th, y) | 100% | 0.5 |
| **R** | 水平 (len×th) | ←（向左） | (x-th, y) | 100% | 0.5 |
| **B** | 竖直 (th×len) | ↑（向上） | (x, y+len) | 80% | 0.5 |
| **T** | 竖直 (th×len) | ↓（向下） | (x, y-len) | 80% | 0.5 |

**B/T side 特殊處理**：
- 原始 pin 寬度 = box_thickness（水平）
- 原始 pin 高度 = box_len（竖直）
- 延伸後寬度 = box_thickness × 0.8（避免超過標準寬度）
- 延伸後高度 = box_len（保持原始）
- 線寬 = 0.5（比 L/R 的 0.5 相同，確保視覺一致）
- 形狀 = 空心矩形（fill=0, stroke=1）

**連接範例（10 條線）：**
| Wire | Source | Dest | Side |
|------|--------|------|------|
| 1 → 85 | 1(L) | 85(R) | L→R |
| 85 → 41 | 85(R) | 41(B) | R→B |
| 85 → 42 | 85(R) | 42(B) | R→B |
| 69 → 51 | 69(R) | 51(B) | R→B |
| 86 → 32 | 86(T) | 32(B) | T→B |
| 91 → 22 | 91(T) | 22(B) | T→B |
| 93 → 22 | 93(T) | 22(B) | T→B |
| 104 → 16 | 104(T) | 16(L) | T→L |
| 105 → 16 | 105(T) | 16(L) | T→L |
| 101 → 106 | 101(T) | 106(T) | T→T |

### 代碼位置

| 功能 | 函數 | 行號 |
|------|------|------|
| PKG 跳過 | `generate_pkg_pdf()` | 549-550 |
| PKG 黑色方塊 | `_draw_side_boxes()` | 616-620 |
| APR 跳過 | `generate_apr_pdf()` | 519 |
| D1.xx 識別 | `generate_combined_pdf()` | 444-446 |
| Inner bound 連接邏輯 | `generate_combined_pdf()` | 514-583 |
| 座標延伸計算 | `_extend_point_toward_center()` | 789-800 |
| **Pin 延伸繪製（關鍵）** | **`_draw_extended_pin()`** | **802-832** |
| 合唱線繪製 | `generate_combined_pdf()` | 581-582 |

### Label 字體縮小
所有 PDF（PKG、APR、Combined）的 PIN_NAME 標籤如果會超出邊界或 header，自動縮小字體：
- 參數：`max_label_extent` 傳入 `_draw_side_boxes()`
- 邊界計算：根據字串長度和字體大小估算標籤範圍
- T side 特別處理：同時檢查 header 邊界（y < 510）
- 縮小：最大減少 2pt 字體大小（最小 2pt）
- 適用於：所有 PDF 的 L/B/R/T 四邊

## Key Pin Types

### NC (No Connect)
- PKG: 黑色方塊顯示
- APR: 跳過不顯示
- Wire: 不繪製

### DOWNBOUND
- PKG: 藍色方塊顯示
- APR: 跳過不顯示
- Wire: 不繪製

### POWERCUT
- PKG: 跳過不顯示
- APR: 黑色方塊顯示
- Wire: 不繪製

### Power/Ground Pins
- DIRECTION = 'P': 紅色方塊
- DIRECTION = 'G': 藍色方塊

### Dynamic References (D1.xx)
- Format: (D1.77), D1.77, D1.91
- Reference other DIE_NUM values
- Resolution happens during re-indexing phase
- Updates `DIE_PAD_NUM` field

## PDF Generation

### Package Dimensions
- `edge_pkg = 350`: Outer PKG frame size (square)
- `edge_apr = 200`: Inner APR frame size (square)
- `box_len_pkg = 25`: PKG pin label box length
- `box_len_apr = 15`: APR pin label box length

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

### Combined PDF Wiring
Wire connects PKG pin directly to APR pin:
- `wire_start = p_pt` (PKG pin coordinate)
- `wire_end = a_pt` (APR pin coordinate)

Wire colors: grey (default), red (P), blue (G)

### APR Pins Position
Use `label_inside=False` to place APR pins at outer edge of APR frame (outside the frame).

## Sanity Check
Validates pin count per side matches PACKAGE header:
- Counts unique PKG_NUM per side
- DOWNBOUND PKG_NUM is included in count
- Total must equal sum of L+B+R+T from PACKAGE header

## CSV Parsing Notes
- Use `csv.DictReader` for proper header mapping
- Handle embedded commas in header (PACKAGE line)
- Empty PIN_NAME shown as '-' in output (when writing .new)
- Internal data keeps empty strings as "" for processing

## Command Line Usage
```bash
python3 bin/fpad_assign.py -list <pin_list_file> -o <output_folder> -all
```

## Key Code Locations

| 函數 | 行號 | 說明 |
|------|------|------|
| `_parse_csv()` | ~110 | CSV 格式解析 |
| `_parse_txt()` | ~138 | Tab-separated 解析 |
| `_reorder_and_reindex_apr_data()` | ~169 | D1.xx 動態參考解析 |
| `_sanity_check()` | ~220 | 腳位數量驗證 |
| `generate_apr_pdf()` | ~588 | APR PDF 生成 |
| `generate_pkg_pdf()` | ~623 | PKG PDF 生成 |
| `generate_combined_pdf()` | ~399 | Combined PDF + Inner bound |
| `_draw_side_boxes()` | ~683 | 繪製框架邊緣腳位 |
| `_extend_point_toward_center()` | ~789 | 座標向中心延伸 |
| **`_draw_extended_pin()`** | **~802** | **延伸 pin 形狀繪製（B/T 寬度 80%）** |
| `Writer.generate_completed_list()` | ~885 | 寫入 .new 檔案 |

### _draw_extended_pin() 實現細節

```python
def _draw_extended_pin(self, c, frame_edge_pt, side, box_len, box_thickness, color):
    """
    參數說明（注意：B/T side 時參數含義會交換）：
    - frame_edge_pt: (x, y) APR frame 邊界上的點
    - side: 'L', 'B', 'R', 'T'
    - box_len: 水平寬度（L/R side）或垂直寬度（B/T side）
    - box_thickness: 垂直厚度（L/R side）或垂直高度（B/T side）
    - color: 填充顏色（基於 DIRECTION：P=紅, G=藍, 其他=黑）
    
    實現：
    - L/R side: 寬度 100%，線寬 0.5，空心矩形
    - B/T side: 寬度 80%（縮小以符合標準），線寬 0.5，空心矩形
    """
```

## Data Field Names
Internal field names use `DIE_PAD_NUM` (not `DIE_NUM`), regardless of input format:
- CSV column 1 → `DIE_PAD_NUM`
- .pin_list column 1 → `DIE_PAD_NUM`
- CSV header `DIE_NUM` or `DIE_PAD_NUM` both map to `DIE_PAD_NUM` field

---

## 修改歷史（2026-04-23）

### Inner Bound Pin 延伸修正

**問題 1：B/T side 方向反向**
- 修正前：B side 向下延伸，T side 向上延伸
- 修正後：B side 向上延伸，T side 向下延伸（都指向 chip 中心）
- 代碼改動：第 824-832 行，交換 B/T 的座標計算

**問題 2：B/T side Pin 形狀"躺下來"**
- 修正前：Pin 形狀變成水平（寬 > 高）
- 修正後：Pin 形狀保持竖直（高 > 寬）
- 根本原因：參數傳入時 box_len 和 box_thickness 含義交換
- 代碼改動：第 826 和 832 行，交換寬度計算：`box_len` ↔ `box_thickness`

**問題 3：延伸 Pin 寬度超標**
- 修正前：寬度 = 100% 原始寬度，線寬 = 2（太粗）
- 修正後：寬度 = 80% 原始寬度，線寬 = 0.5（細緻）
- 代碼改動：第 815 行線寬改為 0.5；第 826、832 行寬度乘以 0.8

### 修改驗證
```
測試檔案：examples/qfn48.8028.pin_list.csv
輸出 PDF：combined_test_v4_80percent.pdf
內部連接：12 條紅線，全部正確繪製
```
