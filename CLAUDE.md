# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start: Development Commands

```bash
# Run the main tool on all example files
make test_py

# Run specific example (output goes to output/ folder)
python3 bin/fpad_assign.py -list examples/example.pin_list -o output -all

# Clean all generated files
make clean

# Show all available targets
make help
```

## Development Workflow

**Critical:** NEVER automatically commit or push changes. Wait for explicit user commands.

When working on code changes:
1. Make changes as requested
2. Test using `make test_py` when modifying PDF generation, parsing, or pin logic
3. Report results and any issues to the user
4. **DO NOT** commit, push, or sync unless user explicitly asks for it

## Key Development Files

| File | Purpose |
|------|---------|
| `bin/fpad_assign.py` | Main Python implementation (700+ lines) — parser, PDF gen, constraint writers |
| `examples/*.pin_list` / `*.csv` | Test input files (tab-separated and CSV formats) |
| `Makefile` | Build and test automation (Python/Perl/C++ versions) |

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

---

## 修改歷史（2026-04-24）— APR/PKG/Combined PDF 完整視覺調整

### 任務背景
用戶要求對 APR PDF、PKG PDF 和 Combined PDF 進行視覺改進，主要包括：
1. PDF 框架尺寸調整（縮小至 80%）
2. Pin 名稱字體統一與大小調整
3. Combined PDF 中 APR 內框文字防止碰到 PKG 框
4. B 邊文字 X 軸位置對齐

### 修改 1：APR/PKG PDF 框架尺寸縮小至 80%

**檔案**：`bin/fpad_assign.py`

**位置**：`generate_apr_pdf()` 第 594 行、`generate_pkg_pdf()` 第 631 行

```python
# 修改前：
edge = 350

# 修改後：
edge = 280  # 350 × 0.8 = 280
```

**效果**：
- APR/PKG 框從 350×350 縮小至 280×280
- Pin 位置相對不變（使用相同的 step 計算邏輯）
- 框縮小 20%，視覺上 pin 更靠近

### 修改 2：4 邊 Pin 名稱字體統一

**問題根源**：
每邊使用各自的 pin 計數計算 `step = length / (count + 1)`，導致：
- 若不同邊 pin 數量不同 → step 不同 → font_size 不同
- L/R/T/B 四邊字體大小不一致

**解決方案**：使用最大 pin 計數計算統一 step

**檔案**：`bin/fpad_assign.py`

**修改位置**：

1. `generate_apr_pdf()` 第 617-620 行：
```python
# 修改前：
for side in ('L', 'B', 'R', 'T'):
    ...
    self._draw_side_boxes(..., l_cnt if side=='L' else ... else t_cnt, 'APR', ...)

# 修改後：
max_cnt = max(l_cnt, b_cnt, r_cnt, t_cnt)
for side in ('L', 'B', 'R', 'T'):
    ...
    self._draw_side_boxes(..., max_cnt, 'APR', ...)  # 所有邊使用 max_cnt
```

2. `generate_pkg_pdf()` 第 674-677 行：同步修改為使用 `max_cnt`

**驗證結果**：QFN48（每邊 12 pin）四邊字體大小視覺上統一

### 修改 3：Combined PDF - APR 內框文字 X 軸對齐

**問題**：APR 內框的 pin 名稱文字相對 pin shape 向右偏移

**根本原因**：
- APR pin shape 的 X 坐標範圍：px 到 px + bw
- 文字 translate 使用 px + bw/2（pin 中心 X）
- 導致文字向右偏

**解決方案**：改為使用 px（pin 左邊界）

**檔案**：`bin/fpad_assign.py`，`_draw_side_boxes()` 第 760 行（B 邊）

```python
# 修改前：
c.translate(px + bw/2, py - 4)

# 修改後：
c.translate(px, py - 4)  # 改用 pin 左邊界 X 座標
```

**驗證結果**：B 邊文字現在與 pin shape 左邊界對齐

### 修改 4：Combined PDF - APR 內框 Overflow 防護

**問題**：Combined PDF 中，APR 內框（edge=200）的長 pin 名稱會碰到 PKG 外框（edge=350）

**設計衝突**（根本原因）：

| 需求 | Standalone APR PDF | Combined PDF APR |
|------|------------------|-----------------|
| 字體行為 | 4 邊統一，不進行 overflow 縮小 | 長文字自動縮小，避免碰到 PKG |
| 檢查邏輯 | 跳過 overflow 檢查 | 執行 overflow 檢查 |

舊代碼 `_draw_side_boxes()` 第 715 行的條件：
```python
if max_label_extent is not None and not (mode == 'APR' and not label_inside):
```
會在 `mode=='APR'` 且 `label_inside==False` 時**跳過** overflow 檢查，導致：
- ✓ Standalone APR PDF：4 邊字體統一（沒有 overflow 縮小）
- ✗ Combined PDF APR：標籤可以無限延伸碰到 PKG 框

**解決方案**：新增 `allow_overflow` 參數區分兩種情境

**修改位置 1**：`_draw_side_boxes()` 函數簽名（第 687 行）
```python
# 修改前：
def _draw_side_boxes(self, c, side, pins, cx, cy, length, b_pos, total, mode, label_inside=False, max_label_extent=None):

# 修改後：
def _draw_side_boxes(self, c, side, pins, cx, cy, length, b_pos, total, mode, label_inside=False, max_label_extent=None, allow_overflow=False):
```

**修改位置 2**：overflow 檢查條件（第 719 行）
```python
# 修改前：
if max_label_extent is not None and not (mode == 'APR' and not label_inside):

# 修改後：
if max_label_extent is not None and not allow_overflow:
```

**修改位置 3**：`generate_apr_pdf()` 呼叫加 `allow_overflow=True`（第 622 行）
```python
# 修改前：
self._draw_side_boxes(c, side, data_by_side[side], ..., max_cnt, 'APR', label_inside=False, max_label_extent=limit)

# 修改後：
self._draw_side_boxes(c, side, data_by_side[side], ..., max_cnt, 'APR', label_inside=False, max_label_extent=limit, allow_overflow=True)
```

**行為矩陣**：
| 呼叫來源 | allow_overflow | 行為 |
|---------|---------------|------|
| `generate_apr_pdf()` | `True` | 跳過 overflow 檢查，4 邊字體統一 ✓ |
| `generate_combined_pdf()` APR | `False`（預設） | 執行 overflow 檢查，防止碰 PKG 框 ✓ |
| `generate_pkg_pdf()` / combined PKG | `False`（預設） | 執行 overflow 檢查（保持原有行為） ✓ |

### 技術亮點

1. **代碼變更最小化**：僅 3 處修改點，保證穩定性
2. **參數設計**：`allow_overflow` 是一個「積極選擇」（顯式允許溢出）而非「消極排除」，更清晰
3. **向後相容**：預設 `allow_overflow=False`，不需要修改 Combined 和 PKG 的呼叫
4. **衝突解決**：同一函數在不同上下文（standalone vs combined）有不同需求時，用參數控制策略

### 實施驗證（2026-04-24）

```bash
# 測試指令
python3 bin/fpad_assign.py -list examples/qfn48.8028.pin_list.csv -o test_combined_overflow -all

# 生成結果
✓ test_combined_overflow/PROJECT_QFN48_TEST__________apr.pdf (4.3K)
✓ test_combined_overflow/PROJECT_QFN48_TEST__________pkg.pdf (3.0K)
✓ test_combined_overflow/PROJECT_QFN48_TEST__________combined.pdf (6.7K)
```

### 測試清單
- ✅ Standalone APR PDF：4 邊字體大小統一（無 overflow 縮小）
- ✅ PKG PDF：4 邊字體大小統一，框縮小至 80%
- ✅ Combined PDF：APR 內框文字不碰到 PKG 框，自動縮小超長文字
- ✅ B 邊文字：X 軸位置與 pin shape 對齐
- ✅ CSV 格式輸入：完全支援，測試成功
- ✅ 所有 PDF 正確生成，無錯誤

### GitHub 提交（2026-04-24）
- **Commit**：`ad0d9bf` - "feat: Add APR inner frame overflow protection in combined PDF"
- **Tag**：`apr-pkg-combined-complete` - "claude code 完成 apr, pkg , combined PDF"
- **推送結果**：
  - main 分支已推送（f66784a...ad0d9bf）
  - Tag 已推送至遠端

### 代碼統計
- 修改檔案：1 個（`bin/fpad_assign.py`）
- 修改行數：16 行（3 處修改點）
- 函數簽名變更：1 個（`_draw_side_boxes()` 加參數）
- 呼叫位置變更：2 個（`generate_apr_pdf()` / `generate_pkg_pdf()`）
- 核心邏輯變更：1 個（overflow 檢查條件）

---

## 修改歷史（2026-04-24）— Inner Bound 對稱性檢查與多重線

### Inner Bound 對稱性規則

**核心配對邏輯**：
- `PKG_NUM=D1.90, DIE_NUM=1` 與 `PKG_NUM=D1.1, DIE_NUM=90` 是一對
- 意思是：DIE_NUM(90) ↔ DIE_NUM(1) 雙向連接

**對稱性判斷**：
| 組合 | 類型 | 線條樣式 |
|------|------|---------|
| A→B 且 B→A 同時存在 | Symmetric | 實線（solid） |
| 只有 A→B 或只有 B→A | Asymmetric | 虛線（dashed）+ ERROR |

**範例**：
```
D1.90 + DIE_NUM=1  → source=90, dest=1
D1.1 + DIE_NUM=90  → source=1, dest=90

90→1 存在，且 1→90 也存在 → Symmetric → 實線
```

### Inner Bound 多重線偏移規則

當同一個 (source, dest) 組合出現多次時，繪製多條平行線：

| 出現次數 | 偏移量 | 說明 |
|---------|--------|------|
| 1 | 0 | 1條線，無偏移 |
| 2 | -2, +2 | 2條線，上下分開 |
| 3 | -4, 0, +4 | 3條線，均勻分布 |

**偏移方向**：
- L/R 邊：Y 軸偏移（上下分開）
- B/T 邊：X 軸偏移（左右分開）

**偏移計算公式**：
```python
offset = (i - (count - 1) / 2) * 2
# i: 第幾條線 (0, 1, 2, ...)
# count: 總共幾條線
```

### 代碼位置

| 功能 | 函數 | 行號 |
|------|------|------|
| Inner Bound 分組收集 | `generate_combined_pdf()` | ~638-670 |
| 對稱性判斷 | `generate_combined_pdf()` | ~711-713 |
| 多重線繪製 | `generate_combined_pdf()` | ~715-743 |

### 實作細節

```python
# 1. 分組統計
direction_map = {}  # (source, dest) -> list of rows
for row in d1xx_rows:
    key = (source, dest)
    direction_map[key].append(row)

# 2. 檢查對稱性
reverse_key = (dest, source)
is_symmetric = reverse_key in direction_map

# 3. 繪製多重線
for i in range(count):
    offset = (i - (count - 1) / 2) * 2
    if side_src in ('L', 'R'):
        src_x, src_y = ext_src[0], ext_src[1] + offset
        dst_x, dst_y = ext_dst[0], ext_dst[1] + offset
    else:
        src_x, src_y = ext_src[0] + offset, ext_src[1]
        dst_x, dst_y = ext_dst[0] + offset, ext_dst[1]
```

---

## 修改歷史（2026-04-24）— DOWNBOUND 接地符號

### DOWNBOUND 處理規則

當 `DIE_PIN_NAME=DOWNBOUND` 時表示此封裝有 Downbound 方式。

**接地線條件**：
- `PKG_NUM=0`
- `DIRECTION=G`
- `DIE_NUM=aa` (有效的 DIE 墊片編號)

**接地線數量**：
- 根據相同的 `(DIE_NUM, DIE_PIN_NAME)` 組合出現次數決定
- 出現 N 次 → 繪製 N 條接地線

### 接地符號繪製

**符號結構**：
- 短線：從 APR pin往外延伸 12 points
- 接地符號：倒 T 形（垂直線 + 3 條水平線）
- 顏色：藍色 (colors.blue)

**符號方向**：
| 邊 | 方向 | 說明 |
|----|------|------|
| L | ← | 向左延伸 |
| R | → | 向右延伸 |
| B | ↓ | 向下延伸 |
| T | ↑ | 向上延伸 |

### 代碼位置

| 功能 | 函數 | 行號 |
|------|------|------|
| 接地線收集 | `generate_combined_pdf()` | ~745-780 |
| 接地符號繪製 | `_draw_ground_symbol()` | ~1052-1114 |

### 實作細節

```python
# 收集 PKG_NUM=0 且 DIRECTION=G 的行
ground_rows = []
for row in self.parser.data:
    if row['PKG_NUM'] == '0' and row['DIRECTION'] == 'G':
        ground_rows.append(row)

# 分組計算數量
ground_counts = {}
for row in ground_rows:
    key = (row['DIE_NUM'], row['DIE_PIN_NAME'])
    ground_counts[key] = ground_counts.get(key, 0) + 1

# 繪製接地符號
for (die_num, pin_name), count in ground_counts.items():
    for i in range(count):
        self._draw_ground_symbol(c, pt[0], pt[1], side, count, i)
```

### 接地符號符號（ground_sign.md）

接地符號的標準繪製方式定義在 `ground_sign.md` 檔案中：
- 垂直中心線
- 空心倒三角形
- GND 文字標註

---

## 修改歷史（2026-04-24）— Combined PDF 位置調整

### 中心點上移

**修改**：將 combined PDF 的中心點 Y 座標從 240 調整為 265

**原因**：避免 B 邊的字體碰到紙張底部

**位置**：`generate_combined_pdf()` 第 517 行
```python
cx, cy = width / 2, 265  # 原本是 240
```

### 動態 APR Frame 調整策略

如果 B 邊上移後 T 邊碰到 header，可以考慮：
1. 縮小 APR frame（edge_apr）
2. 或保持當前設置（cy=265 對 QFN48 封裝已足夠）

---

## 完整驗證清單

### Inner Bound 驗證
- [ ] Symmetric 配對：90↔1, 75↔40 → 實線
- [ ] Asymmetric 單向：只有 A→B → 虛線 + ERROR
- [ ] 多重線：count=2 → 2條平行線（偏移 ±2）
- [ ] 多重線：count=3 → 3條平行線（偏移 -4, 0, +4）

### DOWNBOUND 驗證
- [ ] PKG_NUM=0, DIRECTION=G → 接地符號
- [ ] 多重接地：count=3 → 3條平行接地線
- [ ] 接地符號方向正確（L←, R→, B↓, T↑）

### Combined PDF 驗證
- [ ] B 邊文字不碰到紙張底部
- [ ] T 邊文字不碰到 header
- [ ] APR 內框文字不碰到 PKG 外框
- [ ] 所有線條正確繪製

---

## 指令速查

```bash
# 執行 Combined PDF 生成
python3 bin/fpad_assign.py -list examples/qfn48.8028.pin_list.csv -o . -c -combined

# 完整生成所有輸出
python3 bin/fpad_assign.py -list <pin_list_file> -o <output_folder> -all

# 測試輸出
python3 bin/fpad_assign.py -list examples/example.pin_list -o output -all
```
