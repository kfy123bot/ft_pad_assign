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
