# 00README — 2026-05-12 Session Changes (v3.3)

## Bug Fix + ICC2 Format Update

1. 修正 P/G inst missed in i/o const file — `%` 分隔符 pin 的 `INST_NAME` 未设值，导致 constraint 生成器过滤掉 power/ground pad instance
2. ICC2 pin list in clockwise — `set_io_pad_constraints` 改为 `set_signal_io_constraints`，每个 side 内 instance 顺序反转（逆时钟→顺时钟）
3. DIE overlay pad label 框外修正 — `parse_die_csv()` 改用 regex wildcard 匹配 `DIE\d+_NAME`/`DIE\d+_LOC`/`D\d+_NUM`，取代硬编码 DIE2/DIE3 前缀
4. Pad label 超出 PKG 框修正 — T/B side label 的 X 坐标及 L/R side label 的 Y 坐标加 clamp，确保不超出 frame 范围

---

# 00README — 2026-05-11 Session Changes

## DIE3 Overlay + PLACEMENT Header

### 新增功能
- 新增 `--die3` CLI 參數，支援第三顆 die overlay（僅 CSV 格式）
- DIE3 使用 teal 色系（`#008080`），DIE2 維持 brown（`#8B4513`）
- DIE3 CSV 格式與 DIE2 相同，使用 `D3_NUM`、`D3_PAD_NAME`、`DIE3_NAME`、`DIE3_LOC` 前綴
- DIE3 只連接到 DIE1 pad（與 DIE2 相同）

### PLACEMENT 標頭
- 新增 `PLACEMENT` CSV 標頭，取代 `--die2-flip-x` CLI 參數
- 支援值：`R0`、`R90`、`R180`、`R270`、`R0_FLIP_X`、`R90_FLIP_X`、`R180_FLIP_X`、`R270_FLIP_X`
- 預設為 `R0`（無旋轉、無翻轉）
- 旋轉影響整顆 die（frame + pad + label），以 die 中心為旋轉點
- R90/R270 會交換 frame 的寬高
- `--die2-flip-x` 標記為 deprecated，仍可使用但會顯示警告

### 程式碼重構
- 新增 `parse_die_csv()` 統一解析器，支援 DIE2 和 DIE3 CSV
- `parse_die2_csv()` 改為 thin wrapper
- `_draw_die2_overlay()` 重構為 `_draw_die_overlay()`，支援 color scheme 參數
- PDFGen 使用 `self.overlays` list 管理多顆 die overlay
- 新增 `rotate_point()` 輔助函數
- 新增 `PLACEMENT_TRANSFORMS`、`DIE2_COLORS`、`DIE3_COLORS` 常數

### 新增檔案
- `examples/DIE3_example.csv` — DIE3 範例檔案
- Makefile 新增 `test_die3` target

---

# 00README — 2026-05-04 Session Changes

## DIE_SIZE 標頭支援

新增 `DIE_SIZE : AxB` 標頭欄位（單位 um，A=x 寬，B=y 高），用於指定晶粒尺寸。

```
DIE_SIZE : 2414x1415,,,,,,,,,,,,
```

- A 和 B 可以不同（支援長方形 die）
- 為可選欄位，不影響現有 pin list（向後相容）

## QFN 封裝 Body Size 查找表

新增 `QFN_BODY_SIZES` 常數，根據 pin count 查表得封裝 body size（mm）：

| Pin 數 | Body Size |
|--------|-----------|
| 16/20 | 3x3 |
| 24/28 | 4x4 |
| 32/36 | 5x5 |
| 40/44 | 6x6 |
| 48/52 | 7x7 |
| 56 | 8x8 |
| 64/68 | 9x9 |
| 72/76 | 10x10 |
| 88/100 | 12x12 |

預設 0.5mm pitch，0.4mm pitch 由 DIE_SIZE 自動推斷。

## PDF 框架比例縮放

根據 die size 和 package body size 的比例，動態調整 PDF 框架尺寸：

| 情境 | APR 框 | PKG 框 |
|------|--------|--------|
| 有 DIE_SIZE | 長方形（保持 die aspect ratio） | 正方形（按 body/die 比例縮放） |
| 無 DIE_SIZE | 正方形（原始固定尺寸） | 正方形（原始固定尺寸） |

**新增方法**：
- `_parse_die_size()` — 解析 `AxB` 格式
- `_get_package_body_mm()` — 從 PACKAGE 查表得 body size
- `_compute_frame_dimensions(apr_base, pkg_base)` — 計算四個邊長 (apr_x, apr_y, pkg_x, pkg_y)
- `_side_length(side, edge_x, edge_y)` — L/R 用 edge_y，B/T 用 edge_x

**Position helpers** 改為支援矩形：`_L_pos(cx, cy, edge_x, edge_y=None)`

## PDF 比例尺

每個 PDF（APR、PKG、Combined）右下角新增比例尺：

- 比例尺線段（自動選擇 0.5/1/2/5/10 mm 合適長度）
- `PKG: 7000x7000 um` — 封裝 body size
- `Die: 2414x1415 um` — 晶粒尺寸（有 DIE_SIZE 時才顯示）

所有單位統一為 um。

## PDF Header 增強

PDF 標題列中間顯示封裝和晶粒的實際物理尺寸：

```
Package: 48QFN 12 12 12 12 (7000x7000 um) , Die: 2414x1415 um
```

## 術語修正：bound → bond

全專案統一修正拼寫錯誤：

| 舊 | 新 |
|----|-----|
| `DOWNBOUND` | `DOWNBOND` |
| `Inner_bound` / `INNER_BOUND` | `Inner_bond` / `INNER_BOND` |
| `Inner Bound` | `Inner Bond` |

**修改檔案**：
- `bin/ft_pad_assign.py` — 所有字串比較和註解
- `bin/gen_spec_pdf.py` — spec PDF 文件內容
- `examples/*.csv`（4 個）— CSV 資料列
- `CLAUDE.md` — 開發文件
- `docs/CSV_INPUT_SPEC.md` — 輸入格式規格

第三方 EDA 文件（icc2dp.md、innovusUG.md 等）中的 "bound" 為正確用語，不修改。

## CSV 解析修正

`_parse_csv()` 的 header 檢查條件從 `startswith('D')` 改為 `startswith('D1')`，避免誤排除 `DIE_SIZE` 開頭的行。

## 測試結果

4 個 example 檔案全部通過：
- `qfn40.8803` — 無 DIE_SIZE，向後相容 ✓
- `qfn48.8028` — 有 DIE_SIZE (2414x1415)，矩形 APR 框 ✓
- `qfn56.8803.GPIO` — 無 DIE_SIZE ✓
- `qfn56.8803.PSRAM` — 有 DIE_SIZE (4000x3000) ✓

---

# 00README — 2026-05-05 Session Changes

## QFN_BODY_SIZES 查找表更新

根據實際封裝規格更新查找表，重複腳位取最小尺寸：

| Body Size | Pin 數 |
|-----------|--------|
| 3x3 | 12, 16, 20 |
| 4x4 | 24, 28 |
| 5x5 | 32, 40 |
| 6x6 | 44, 48, 56 |
| 7x7 | 64 |
| 9x9 | 76, 88 |

**變更影響**：
- QFN40：6mm → **5mm**（`5x5: 32, 40`）
- QFN56：8mm → **6mm**（`6x6: 44, 48, 56`）

## PKG_SIZE 標頭支援（um）

新增 `PKG_SIZE` 標頭欄位，單位 **um**，優先於 pin count 查表：

```
PKG_SIZE : 7000x7000,,,,,,,,,,,,
```

**優先順序**：
1. `PKG_SIZE` header（um）→ 除以 1000 轉 mm 內部使用
2. pin count 查 `QFN_BODY_SIZES`（mm）

**支援非正方形**：`PKG_SIZE : 7000x8000` → PKG 框為矩形。

**向後相容**：無 `PKG_SIZE` 時行為不變。

## 比例尺單位統一為 um

比例尺標籤從 `mm` 改為 `um`：

| 舊 | 新 |
|----|-----|
| `0.5 mm` | `500 um` |
| `1 mm` | `1000 um` |
| `2 mm` | `2000 um` |
| `5 mm` | `5000 um` |
| `10 mm` | `10000 um` |

候選值：`[500, 1000, 2000, 5000, 10000]` um，自動選擇 30-120 pts 範圍內合適長度。

## _compute_frame_dimensions 支援非正方形 PKG 框

`pkg_x` 和 `pkg_y` 獨立計算（舊版取 max 後強制正方形），使 `PKG_SIZE` 非正方形時 PKG 框也為矩形。

## 測試結果

2 個 example 檔案通過：
- `qfn40.8803` — PKG=5000x5000um, Die=4000x3500um ✓
- `qfn56.8803.PSRAM` — PKG=6000x6000um, Die=4000x3500um ✓
