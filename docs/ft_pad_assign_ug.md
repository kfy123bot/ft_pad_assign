# FT_PAD_ASSIGN 使用說明書

> 本文檔適用對象：封裝設計工程師、APR 工程師、需要填寫或核對 Pin List 的人員。
> 工具版本：v5（`bin/ft_pad_assign.py`）

---

## 目錄

1. [工具概述](#1-工具概述)
2. [安裝需求](#2-安裝需求)
3. [命令列用法](#3-命令列用法)
4. [Pin List 檔案格式](#4-pin-list-檔案格式)
   - 4.1 [檔案整體結構](#41-檔案整體結構)
   - 4.2 [Header 元資料區](#42-header-元資料區)
   - 4.3 [資料欄位（11 個）](#43-資料欄位11-個)
   - 4.4 [DIE_PIN_NAME 的 % 分隔規則](#44-die_pin_name-的--分隔規則)
5. [特殊列類型](#5-特殊列類型)
6. [輸出檔案說明](#6-輸出檔案說明)
7. [自動處理流程](#7-自動處理流程)
8. [PDF 圖示說明](#8-pdf-圖示說明)
9. [QFN 封裝尺寸對照表](#9-qfn-封裝尺寸對照表)
10. [常見錯誤排除](#10-常見錯誤排除)
11. [完整工作範例](#11-完整工作範例)
12. [欄位別名對照表](#12-欄位別名對照表)

---

## 1. 工具概述

`ft_pad_assign.py` 是一個 QFN 封裝 Pin Assignment 輔助工具，讀取 **Pin List CSV 檔案**，產生以下輸出：

```
Pin List (.csv / .pin_list)
        │
        ▼
  ft_pad_assign.py
        │
        ├──→  PKG PDF         — 封裝腳位示意圖（外觀視角）
        ├──→  APR PDF         — Die Pad 佈局圖（晶片內部視角）
        ├──→  Combined PDF    — PKG + APR 合併圖 + Bonding Wire
        ├──→  .new            — 補齊後的 Pin List（固定寬度文字格式）
        ├──→  .new.csv        — 補齊後的 Pin List（CSV 格式）
        ├──→  .inn.const      — Innovus I/O 擺放約束檔
        ├──→  .icc2.const     — ICC2 I/O 擺放約束檔
        ├──→  _stagger.rpt    — I/O Stagger 密度檢查報告
        └──→  .log            — 執行日誌
```

**核心功能**：
- 自動驗證 Pin 數量（每邊 + 總計）
- 自動計算 PKG_LOC（根據 PACKAGE header）
- 自動重編 PKG_NUM / DIE_NUM
- 支援 Ring Shift（`PKG_TOP_LEFT_PIN`）
- 支援 Inner Bond（D1.xx 語法）
- 支援 DOWNBOND / NC / POWERCUT 特殊 pin 類型
- PDF 含比例尺（µm），支援非正方形 Die / 非正方形 Package

---

## 2. 安裝需求

| 需求 | 說明 |
|------|------|
| Python 3.7+ | 標準安裝 |
| `reportlab` | PDF 產生（**必要**） |
| `openpyxl` | Excel 模板產生（選填，僅 `gen_ug_excel.py` 需要） |

```bash
# 安裝必要套件
pip3 install reportlab

# 選填（產生 Excel 模板）
pip3 install openpyxl
```

---

## 3. 命令列用法

### 3.1 基本語法

```bash
python3 bin/ft_pad_assign.py -list <pin_list_file> [選項]
```

### 3.2 完整選項說明

| 選項 | 類型 | 說明 |
|------|------|------|
| `-list <file>` | **必要** | Pin List 輸入檔（`.csv` 或 `.pin_list`） |
| `-o <目錄>` | 選填 | 輸出目錄（預設：當前目錄） |
| `-all` | 選填 | 產生**所有**輸出（等同於同時指定以下所有旗標） |
| `-apr` | 選填 | 產生 APR PDF（Die Pad 圖） |
| `-pkg` | 選填 | 產生 PKG PDF（封裝腳位圖） |
| `-combined` | 選填 | 產生 Combined PDF（合併圖 + Bonding Wire） |
| `-c` | 選填 | 產生 `.new`、`.new.csv`、`.inn.const`、`.icc2.const` |
| `-stagger` | 選填 | 執行 Stagger 密度檢查，產生 `_stagger.rpt` |
| `-stagger-max <N>` | 選填 | 連續 I/O pin 警告閾值（預設：8） |
| `-v [<file> ...]` | 選填 | Verilog 網表檔（自動填入 IO_CELL_NAME、DIRECTION） |

> **注意**：`.inn.const` 和 `.icc2.const` 只有在同時提供 `-c` 和 `-v` 時才會產生。

### 3.3 常用指令範例

```bash
# 產生所有輸出，輸出到 output/ 目錄
python3 bin/ft_pad_assign.py -list examples/qfn48.8028.pin_list.csv -o output -all

# 只產生 PDF（不產生文字輸出）
python3 bin/ft_pad_assign.py -list my.pin_list.csv -o out -apr -pkg -combined

# 只補齊 Pin List（不產生 PDF）
python3 bin/ft_pad_assign.py -list my.pin_list.csv -o out -c

# 搭配 Verilog 補全 IO_CELL_NAME
python3 bin/ft_pad_assign.py -list my.pin_list.csv -o out -all -v design_top.v

# 跑測試（Makefile）
make test_py
```

---

## 4. Pin List 檔案格式

### 4.1 檔案整體結構

Pin List 檔案（`.csv` 或 `.pin_list`）由三個區塊組成，**順序固定**：

```
┌──────────────────────────────────────────────────────────────┐
│  區塊一：Header 元資料區                                       │
│  每行格式：KEY : VALUE                                         │
│  PRODUCTION NO  : PRJ8028_QFN48_TEST                         │
│  PKG_TOP_LEFT_PIN : 1                                        │
│  PACKAGE : 48QFN 12 12 12 12                                 │
│  VERSION : V1.0_20240418                                     │
│  DIE_SIZE : 2414x1415         ← 選填                         │
│  PKG_SIZE : 6000x6000         ← 選填，不填則查封裝尺寸表       │
├──────────────────────────────────────────────────────────────┤
│  （空白行）                                                    │
├──────────────────────────────────────────────────────────────┤
│  區塊二：CSV 資料表                                            │
│  PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,...  ← 表頭行     │
│  1,,103,SCL,-,L,T,-,-,-,-                                    │
│  2,,104,SDA,-,L,T,-,-,-,-                                    │
│  ...                                                         │
├──────────────────────────────────────────────────────────────┤
│  （空白行）                                                    │
├──────────────────────────────────────────────────────────────┤
│  區塊三：Inner_bond 模板區（選填）                              │
│  Inner_bond,,1,I0 (X.Y),I1 (X.Y)                            │
│  Inner_bond,,2,I2 (X.Y),(X.Y)                               │
└──────────────────────────────────────────────────────────────┘
```

**檔案格式**：
- `.csv` — 逗號分隔，欄位後可有多餘逗號（自動忽略）
- `.pin_list` — Tab 分隔，規則相同

---

### 4.2 Header 元資料區

Header 每行格式：`KEY : VALUE`（冒號前後可有空白）

#### 必要 Header

| Key | 格式 | 範例 | 說明 |
|-----|------|------|------|
| `PRODUCTION NO` | 字串 | `PRJ8028_QFN48_TEST` | 專案代號。決定所有輸出檔名前綴。非字母數字字元自動轉為 `_`。<br>別名：`PROJECT NO`（兩者等價，輸出統一為 `PROJECT NO`） |
| `PACKAGE` | `<類型> <L> <B> <R> <T>` | `48QFN 12 12 12 12` | 封裝類型及四邊 pin 數。工具用此計算 PKG_LOC 及驗證 pin 數 |
| `VERSION` | 字串 | `V1.0_20240418` | 版本號，顯示於 PDF 頁首 |

**PACKAGE 格式說明**：

```
48QFN  12  12  12  12
  │     │   │   │   └── T（Top）邊 pin 數
  │     │   │   └────── R（Right）邊 pin 數
  │     │   └────────── B（Bottom）邊 pin 數
  │     └────────────── L（Left）邊 pin 數
  └──────────────────── 封裝類型（不影響解析，僅做識別）
```

| 範例 | 封裝 | L | B | R | T | 總計 |
|------|------|---|---|---|---|------|
| `48QFN 12 12 12 12` | QFN48 | 12 | 12 | 12 | 12 | 48 |
| `56QFN 14 14 14 14` | QFN56 | 14 | 14 | 14 | 14 | 56 |
| `40QFN 10 10 10 10` | QFN40 | 10 | 10 | 10 | 10 | 40 |

#### 選填 Header

| Key | 格式 | 範例 | 說明 |
|-----|------|------|------|
| `PKG_TOP_LEFT_PIN` | 整數 | `1`（預設）或 `15` | 指定封裝左上角（L 邊第一根）pin 的**原始編號**。不為 1 時觸發 Ring Shift（詳見第 7 節） |
| `DIE_SIZE` | `寬x高`（µm） | `2414x1415` | Die 實際尺寸。啟用後 APR PDF 依比例繪製矩形 die，PKG PDF 等比縮放 |
| `PKG_SIZE` | `寬x高`（µm） | `7000x7000` | Package body 尺寸。若省略，工具從內建封裝尺寸表查詢（見第 9 節） |

> **Header 書寫規則**：
> - Key 不區分大小寫（`production no`、`PRODUCTION NO` 均可）
> - Header 行中可有多餘逗號（CSV 格式中常見，自動去除）
> - Header 行順序不固定
> - 不認識的 Key 會被忽略（不報錯）

---

### 4.3 資料欄位（11 個）

CSV 表頭行範例：
```
PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO
```

欄位順序**不固定**（工具以欄位名稱匹配，非位置）。每個欄位支援別名（見[第 12 節](#12-欄位別名對照表)）。

---

#### PKG_NUM — 封裝腳位編號

| 值 | 含義 | PKG PDF | APR PDF | Combined PDF |
|----|------|---------|---------|-------------|
| 正整數（`1`～`N`） | 正常封裝腳位 | 顯示 | — | 顯示 |
| `0` | 無獨立封裝腳位（共用 die pad 或電源/地） | 跳過（DOWNBOND 例外） | 顯示 | 顯示 wire |
| `-` 或空 | 無效 / 佔位 | 跳過 | 跳過 | 跳過 |
| `D1.xx` | Inner Bond（無括號）源端 xx → 目標 DIE_NUM | 特殊線 | 特殊線 | 特殊線 |
| `(D1.xx)` | Inner Bond（有括號）目標 DIE_NUM → 源端 xx | 特殊線 | 特殊線 | 特殊線 |
| `Inner_bond` | 模板/備注列 | 跳過 | 跳過 | 跳過 |

> **重要**：正整數 PKG_NUM 在 Ring Shift 後會從 1 重新編號。`D1.xx` 中的 xx 也會跟著更新。

---

#### DIE_NUM — 晶粒墊片編號

| 值 | 含義 |
|----|------|
| 正整數 | 正常 die pad，工具會從 L 邊第一個非 NC pin 起重編為 1、2、3... |
| `0` | 無 die pad（NC、DOWNBOND、或純封裝腳位） |
| `-` 或空 | 無效 / 佔位 |

> 相同原始 DIE_NUM 的多列會得到**相同的新編號**（去重），APR PDF 只顯示一次。

---

#### PKG_PIN_NAME — 封裝側 pin 名稱（選填）

- 有值時，PKG PDF 使用此名稱作為標籤
- 空或 `-` 時，fallback 到 `DIE_PIN_NAME`

---

#### DIE_PIN_NAME — 晶粒側 pin 名稱（**最關鍵**）

決定 pin 的類型與 PDF 顯示行為：

| 特殊值 | PKG PDF | APR PDF | Combined PDF |
|--------|---------|---------|-------------|
| `NC` | 黑色實心方塊 | **跳過** | **跳過** |
| `DOWNBOND` | 藍色方塊 | **跳過** | 繪製接地符號（倒 T） |
| 含 `POWERCUT` | **跳過** | 黑色實心方塊 | **跳過** |
| 其他 | 正常顯示 | 正常顯示 | 正常顯示 |

名稱中的 `%` 分隔語法見[第 4.4 節](#44-die_pin_name-的--分隔規則)。

---

#### IO_CELL_NAME — I/O Cell 實例名稱（選填）

- 填入 Verilog hierarchical instance name（如 `U_TOP/U_PAD0`）
- 搭配 `-v` 時，空值或 `NOT_FOUND` 的欄位會自動從 Verilog 查找填入
- 用於產生 `.inn.const` / `.icc2.const`

---

#### PKG_LOC — 封裝側邊位置

| 值 | 說明 |
|----|------|
| `L` | 左邊（Left） |
| `B` | 下邊（Bottom） |
| `R` | 右邊（Right） |
| `T` | 上邊（Top） |
| `-` 或空 | **工具根據 PKG_NUM 自動計算，手動填寫值會被覆蓋** |

分配邏輯（以 `48QFN 12 12 12 12` 為例）：

| PKG_NUM | 分配邊 |
|---------|--------|
| 1 ～ 12 | L |
| 13 ～ 24 | B |
| 25 ～ 36 | R |
| 37 ～ 48 | T |

---

#### DIE_LOC — 晶粒側邊位置

| 值 | 說明 |
|----|------|
| `L` / `B` / `R` / `T` | 晶粒四邊 |
| `-` 或空 | 在 Ring Shift 後自動跟隨 PKG_LOC；Ring Shift 未啟用時需手動填寫 |

---

#### DIRECTION — 腳位方向 / 電源類型

| 值 | 含義 | Combined PDF Wire 顏色 |
|----|------|----------------------|
| `P` | 電源（Power） | 紅色 |
| `G` | 接地（Ground） | 藍色 |
| `I` | 輸入（Input） | 灰色 |
| `O` | 輸出（Output） | 灰色 |
| `B` | 雙向（Bidirectional） | 灰色 |
| `-` 或空 | 未指定 | 灰色 |

> 搭配 `-v` 時，`-` 的 I/O pin 會自動從 Verilog port 方向填入。

---

#### LOAD — 電容值（選填）

- 用於 Stagger 報告，不影響 PDF
- 任意數值或字串，空值填 `-`

---

#### SLEW — 轉換率（選填）

- 用於 Stagger 報告，不影響 PDF
- 任意數值或字串，空值填 `-`

---

#### SSO — SSO 比值 / 功能群組標籤（選填）

- 用於 Stagger 報告及視覺分組，不影響 PDF
- 常用值：`RX`、`TX`、`LDO`、`AUDIO`、`PLL` 等

---

### 4.4 DIE_PIN_NAME 的 `%` 分隔規則

當 DIE_PIN_NAME 包含 `%C%` 時，工具將名稱拆分：前段作為 APR PDF 標籤，後段（含 hierarchical path）直接填入 IO_CELL_NAME。PKG PDF 標籤與此欄位無關，由 PKG_PIN_NAME 決定。

```
格式：<APR 顯示名>%C%<IO_CELL_NAME（含 hierarchical path）>

範例：VDD11%C%U_AIP_TOP/U_VDD11_APR5

APR PDF 標籤：VDD11                        ← 第一段（% 之前）
IO_CELL_NAME：U_AIP_TOP/U_VDD11_APR5      ← 最後一段（完整 hierarchical path）
```

| 輸入值 | APR 顯示 | IO_CELL_NAME |
|--------|---------|--------------|
| `SCL` | `SCL` | （由 IO_CELL_NAME 欄位或 Verilog 決定） |
| `VDD11%C%U_AIP_TOP/U_VDD11_APR5` | `VDD11` | `U_AIP_TOP/U_VDD11_APR5` |
| `VDD33_IOB%IO%U_AIP_TOP/U_VDD33_IOB0` | `VDD33_IOB` | `U_AIP_TOP/U_VDD33_IOB0` |

---

## 5. 特殊列類型

### 5.1 NC（No Connect）

```csv
35,,0,NC,-,R,R,-,-,-,TX
```

封裝腳位存在但無 die pad 連接。

| PDF | 行為 |
|-----|------|
| PKG PDF | 黑色實心方塊 |
| APR PDF | 跳過 |
| Combined | 黑色方塊（PKG 框）；APR 框跳過 |

**規則**：`DIE_NUM` 必須為 `0`；`DIE_PIN_NAME` = `NC`

---

### 5.2 DOWNBOND（下接地）

```csv
17,,0,DOWNBOND,-,B,-,G,-,-,RX
```

封裝腳位直接接地，無 die pad。

| PDF | 行為 |
|-----|------|
| PKG PDF | 藍色實心方塊 |
| APR PDF | 跳過 |
| Combined | 繪製接地符號（藍色倒 T 形） |

**規則**：`DIE_NUM` = `0`；`DIE_PIN_NAME` = `DOWNBOND`；`DIRECTION` = `G`

---

### 5.3 POWERCUT

```csv
0,,84,POWERCUT,-,-,T,-,-,-,-
```

Die 上的電源切割點，無對應封裝腳位。

| PDF | 行為 |
|-----|------|
| PKG PDF | 跳過 |
| APR PDF | 黑色實心方塊 |
| Combined | 跳過 |

**規則**：`PKG_NUM` = `0`；`DIE_PIN_NAME` 含 `POWERCUT`

---

### 5.4 共用 Die Pad（PKG_NUM = 0，有 DIE_NUM）

```csv
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX
```

同一個 die pad 出現 N 次（`DIRECTION=G`）= N 條接地線繪製在 Combined PDF。
APR PDF 去重，只顯示一次。

---

### 5.5 Inner Bond（D1.xx 語法）

跨 die pad 之間的連線（chip-to-chip 或 die pad 間連線），無對應封裝腳位。

**方向規則**（以 DIE_NUM 為基準）：

| PKG_NUM 格式 | DIE_NUM | 連線方向 | 說明 |
|-------------|---------|---------|------|
| `D1.77` | `42` | pad 77 → pad 42 | 無括號：從 xx 到目標 |
| `(D1.77)` | `42` | pad 42 → pad 77 | 有括號：反向，從目標到 xx |

**對稱性驗證**：

| 狀態 | 線條樣式 | Log |
|------|---------|-----|
| A→B 和 B→A 同時存在 | **實線（solid）** | INFO |
| 只有單方向 | **虛線（dashed）** | ERROR |

**多重線**：同一 (src, dst) 出現 N 次時，繪製 N 條平行線，偏移 ±2pt。

```csv
D1.94,,33,VDD11%C%U_AIP_TOP/U_VDD11_APR0,-,-,B,P,-,-,-
D1.84,,35,VDD33_IOB%IO%U_AIP_TOP/U_VDD33_IOB0,-,-,B,-,-,-,-
(D1.35),,84,VDD33_IOT%IO%U_AIP_TOP/U_VDD33_IOT0,-,-,T,P,-,-,-
```

---

### 5.6 Inner_bond 模板列（區塊三）

```csv
Inner_bond,,1,I0 (X.Y),I1 (X.Y),,,,,,,,
Inner_bond,,2,I2 (X.Y),(X.Y),,,,,,,,
```

- 不參與 pin 計數、不出現在 PDF
- 原樣保留到 `.new` 輸出
- 用於記錄設計意圖（X.Y 座標佔位符）

---

## 6. 輸出檔案說明

所有輸出以 `PRODUCTION NO`（或 `PROJECT NO`）值作為檔名前綴，存放於 `-o` 指定目錄。

| 檔案 | 產生條件 | 說明 |
|------|---------|------|
| `<proj>.log` | 始終 | 執行日誌（INFO / WARN / ERROR / FATAL） |
| `<proj>.new` | `-c` 或 `-all` | 補齊後的 Pin List（固定寬度文字格式，含分隔線） |
| `<proj>.new.csv` | `-c` 或 `-all` | 補齊後的 Pin List（CSV 格式，可再次輸入） |
| `<proj>_pkg.pdf` | `-pkg` 或 `-all` | 封裝腳位示意圖（外觀視角） |
| `<proj>_apr.pdf` | `-apr` 或 `-all` | Die Pad 佈局圖（晶片內部視角） |
| `<proj>_combined.pdf` | `-combined` 或 `-all` | PKG + APR 合併 + Bonding Wire |
| `<proj>_chip.inn.const` | `-c` + `-v` + `-all` | Innovus I/O 擺放約束（Tcl 格式） |
| `<proj>_chip.icc2.const` | `-c` + `-v` + `-all` | ICC2 I/O 擺放約束（Tcl 命令格式） |
| `<proj>_stagger.rpt` | `-stagger` 或 `-all` | I/O Stagger 密度警告報告 |

### .new 輸出格式說明

```
PROJECT NO : PRJ8028_QFN48_TEST
PKG_TOP_LEFT_PIN : 1
PACKAGE : 48QFN 12 12 12 12
VERSION : V1.0_20240418
PKG_SIZE : 6000x6000
DIE_SIZE : 2414x1415

PKG_NUM  PKG_PIN_NAME  DIE_NUM      DIE_PIN_NAME         IO_CELL_NAME  PKG_LOC    DIE_LOC
------------------------------------------------------------------------
1        -             103          SCL                  -             L          T          ...
```

`.new.csv` 格式與 `.new` 內容相同，但為 CSV 格式，可直接作為新一輪的輸入使用。

---

## 7. 自動處理流程

工具在載入 CSV 後，依序執行以下六個自動處理步驟：

```
步驟 1：_ring_shift_data()
  │ 觸發條件：PKG_TOP_LEFT_PIN ≠ 1
  │ 作用：將資料列循環重排，使 PKG_TOP_LEFT_PIN 指定的 pin 成為第一列
  ▼

步驟 2：_reindex_pkg_num()
  │ 觸發條件：PKG_TOP_LEFT_PIN ≠ 1
  │ 作用：PKG_NUM 從 1 重新編號（正整數部分），PKG_TOP_LEFT_PIN 重置為 1
  ▼

步驟 3：_reassign_pkg_loc()
  │ 觸發條件：始終執行
  │ 作用：根據 PKG_NUM ring 順序和 PACKAGE L/B/R/T 數量，計算每列的 PKG_LOC
  │ 驗證：有效 PKG_NUM 唯一數 vs L+B+R+T 總數
  ▼

步驟 4：_reassign_die_loc()
  │ 觸發條件：僅在 Ring Shift 執行後（步驟 1 有觸發）
  │ 作用：DIE_LOC 跟隨 PKG_LOC（共用 pad 跟隨最鄰近的 side）
  ▼

步驟 5：_sanity_check_list()
  │ 觸發條件：始終執行
  │ 作用：驗證每邊唯一 PKG_NUM 數量 = PACKAGE header 對應邊的數量
  │ 輸出：每邊 PASS / FAIL + 總計比對
  ▼

步驟 6：_reorder_and_reindex_apr_data()
     觸發條件：始終執行
     作用：
       a) DIE_NUM 從 L 邊第一根非 NC pin 起重編為 1, 2, 3...
       b) 相同原始 DIE_NUM 的列取得相同新編號（去重）
       c) 更新所有 D1.xx 中的 xx 為新 DIE_NUM
```

### Ring Shift 範例

當 `PACKAGE = 56QFN 14 14 14 14`，`PKG_TOP_LEFT_PIN = 15`：

```
原始順序：pin 1, 2, 3, ..., 14, [15], 16, ..., 56
                              ↑ 這裡切斷並循環

重排後：  pin 15, 16, ..., 56, 1, 2, ..., 14
重編後：  1,  2,  ..., 42, 43, 44, ..., 56
         └─────── 新 PKG_NUM ───────┘
```

---

## 8. PDF 圖示說明

### 8.1 PDF 類型對比

| 特性 | PKG PDF | APR PDF | Combined PDF |
|------|---------|---------|-------------|
| 視角 | 封裝外觀 | Die 內部 | 兩者合併 |
| PKG 框大小 | 280pt 正方形 | — | 350pt（含 DIE_SIZE 時等比） |
| APR 框大小 | — | 200pt（含 DIE_SIZE 時等比） | 中央 |
| NC | 黑色方塊 | 跳過 | 黑色方塊（PKG 框）；APR 跳過 |
| DOWNBOND | 藍色方塊 | 跳過 | 藍色方塊（PKG 框） |
| POWERCUT | 跳過 | 黑色方塊 | 跳過 |
| Inner Bond | — | 延伸線 | 紅色 wire |
| 比例尺 | 右下角 µm | 右下角 µm | 兩框各自 |

### 8.2 Wire 顏色

| DIRECTION | Combined PDF Wire 顏色 |
|-----------|----------------------|
| `P` | 紅色 |
| `G` | 藍色 |
| `I` / `O` / `B` / 空 | 灰色 |

### 8.3 PKG frame 尺寸（有 DIE_SIZE 時）

- APR frame 依 die aspect ratio 縮放為矩形
- PKG frame 依 `PKG body / die` 比例縮放
- 若有 `PKG_SIZE` header，PKG frame 也支援非正方形

---

## 9. QFN 封裝尺寸對照表

當未填 `PKG_SIZE` Header 時，工具查詢以下表格（來源：JEDEC MO-220）：

| Pin 數 | Body Size (mm) | Pitch (mm) | Pin Width (mm) | Pin Length (mm) | E-pad (mm) |
|--------|----------------|------------|----------------|-----------------|------------|
| 12 | 3.0 | — | — | — | — |
| 16 | 3.0 | — | — | — | — |
| 20 | 3.0 | — | — | — | — |
| 24 | 4.0 | — | — | — | — |
| 28 | 4.0 | — | — | — | — |
| 32 | 5.0 | 0.4 | 0.20 | 0.40 | 3.30 |
| 40 | 5.0 | 0.4 | 0.20 | 0.40 | 3.30 |
| 44 | 6.0 | 0.4 | 0.20 | 0.40 | 4.30 |
| 48 | 6.0 | 0.4 | 0.20 | 0.40 | 4.30 |
| 56 | 6.0 | 0.4 | 0.20 | 0.40 | 4.30 |
| 64 | 7.0 | 0.4 | 0.20 | 0.40 | 5.30 |
| 76 | 9.0 | 0.5 | 0.25 | 0.50 | 7.00 |
| 88 | 9.0 | 0.5 | 0.25 | 0.50 | 7.00 |

> 0.4mm pitch 為預設；若 die 尺寸超出標準 body，工具自動偵測並切換為 0.4mm pitch。
> 如需自訂封裝尺寸，在 Header 填入 `PKG_SIZE : <寬um>x<高um>`。

---

## 10. 常見錯誤排除

### 10.1 FATAL 級別（工具停止執行）

| 訊息 | 原因 | 解決 |
|------|------|------|
| `File not found: xxx` | `-list` 指定的檔案不存在 | 確認路徑正確 |
| `Error parsing list: ...` | CSV 格式嚴重錯誤 | 檢查檔案編碼（需 UTF-8）與欄位數 |

### 10.2 ERROR 級別（繼續執行但結果可能不正確）

| 訊息 | 原因 | 解決 |
|------|------|------|
| `Side X check FAILED: Found N, expected M` | 某邊實際 pin 數 ≠ PACKAGE header | 確認 PKG_NUM 連續且無多餘/遺漏 |
| `TOTAL PIN COUNT MISMATCH` | 四邊總計 ≠ L+B+R+T | 同上 |
| `Inner Bond ASYMMETRIC: D1.A→B but no D1.B→A` | Inner Bond 只有單方向 | 補上反向的 D1.xx 列 |
| `PKG_LOC reassign TOTAL MISMATCH` | 有效 PKG_NUM 數量 ≠ L+B+R+T | 確認 PKG_NUM 正整數編號是否重複或跳號 |
| `D1.xx reference target not found` | D1.xx 的目標 DIE_NUM 不存在 | 確認目標 die pad 的原始 DIE_NUM 是否正確 |

### 10.3 WARN 級別（提示，不影響主要功能）

| 訊息 | 原因 | 影響 |
|------|------|------|
| `PACKAGE definition missing` | Header 缺少 PACKAGE | 無法進行 pin 分配和驗證 |
| `No L-side signal pin found for DIE reindex` | 沒有 L 邊的非 NC pin | DIE_NUM 重編被跳過 |
| `No Verilog files, skipping bridging` | 未提供 `-v`，正常情況 | IO_CELL_NAME 不自動填入 |

### 10.4 常見陷阱

1. **PKG_LOC 不需要手動填寫**：工具根據 PKG_NUM 自動計算，手動值會被覆蓋
2. **DIE_LOC 在非 Ring Shift 情況需手動填寫**：`PKG_TOP_LEFT_PIN=1` 時工具不自動補全
3. **DIE_NUM 會被重編**：原始值僅用於 D1.xx 解析，最終值由工具決定；輸出的 `.new` 用新編號
4. **相同 DIE_NUM 的列共享 APR pin**：多列相同 DIE_NUM 在 APR PDF 只顯示一次
5. **NC 和 DOWNBOND 的 DIE_NUM 必須為 `0`**：否則會被誤計為正常 die pad
6. **`%` 在 DIE_PIN_NAME 中有特殊含義**：區分 PKG 標籤與 APR 標籤
7. **`0` 和 `-` 含義不同**：`0` = 共用/無 pad；`-` = 無效/空白

---

## 11. 完整工作範例

### 11.1 情境

產品代號 PRJ8028，48 腳 QFN 封裝（6×6mm，12-12-12-12），Die 尺寸 2414×1415µm。

### 11.2 建立 Pin List

建立 `my_project.pin_list.csv`：

```csv
PRODUCTION NO  : PRJ8028_QFN48,,,,,,,,,,,,
PKG_TOP_LEFT_PIN : 1,,,,,,,,,,,,
PACKAGE : 48QFN 12 12 12 12,,,,,,,,,,,,
VERSION : V1.0_20260507,,,,,,,,,,,,
DIE_SIZE : 2414x1415,,,,,,,,,,,,

PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO
1,,103,SCL,-,L,T,-,-,-,-
2,,104,SDA,-,L,T,-,-,-,-
3,,105,BIST,-,L,T,-,-,-,-
4,,106,GPIO16,-,L,T,-,-,-,-
0,,107,GND%C%U_AIP_TOP/U_GND_APR8,-,-,T,G,-,-,-
5,,2,VDD33%IO%U_AIP_TOP/U_VDD33_INTPLL,-,L,L,P,-,-,-
6,,4,PAD_RX_IN0_P1,-,L,L,-,-,-,RX
7,,5,PAD_RX_IP0_P1,-,L,L,-,-,-,RX
8,,6,PAD_RX_IN1_P1,-,L,L,-,-,-,RX
9,,7,PAD_RX_IP1_P1,-,L,L,-,-,-,RX
10,,8,PAD_RX_IN2_P1,-,L,L,-,-,-,RX
11,,9,PAD_RX_IP2_P1,-,L,L,-,-,-,RX
12,,10,PAD_RX_CKN_P1,-,L,L,-,-,-,RX
13,,11,PAD_RX_CKP_P1,-,B,L,-,-,-,RX
...（其餘 pin 省略）...
35,,0,NC,-,R,R,-,-,-,TX
17,,0,DOWNBOND,-,B,-,G,-,-,RX
D1.94,,33,VDD11%C%U_AIP_TOP/U_VDD11_APR0,-,-,B,P,-,-,-
(D1.94),,1,VDD11%C%U_AIP_TOP/U_VDD11_APR5,-,-,L,P,-,-,-
```

### 11.3 執行工具

```bash
# 產生所有輸出到 output/ 目錄
python3 bin/ft_pad_assign.py \
    -list my_project.pin_list.csv \
    -o output \
    -all

# 查看日誌確認無 ERROR
cat output/PRJ8028_QFN48.log
```

### 11.4 確認輸出

```
output/
├── PRJ8028_QFN48.log           ← 執行日誌
├── PRJ8028_QFN48.new           ← 補齊後的 Pin List（文字格式）
├── PRJ8028_QFN48.new.csv       ← 補齊後的 Pin List（CSV 格式）
├── PRJ8028_QFN48_pkg.pdf       ← 封裝腳位圖
├── PRJ8028_QFN48_apr.pdf       ← Die Pad 佈局圖
├── PRJ8028_QFN48_combined.pdf  ← 合併圖 + Bonding Wire
└── PRJ8028_QFN48_stagger.rpt   ← Stagger 密度報告
```

### 11.5 Log 正常輸出範例

```
[INFO] Starting FT_PAD_ASSIGN Standalone Tool...
[INFO] Reading Pin List: my_project.pin_list.csv
[INFO] Loaded 78 entries from pin list.
[INFO] Side L check PASS: 12 unique PKG_NUMs
[INFO] Side B check PASS: 12 unique PKG_NUMs
[INFO] Side R check PASS: 12 unique PKG_NUMs
[INFO] Side T check PASS: 12 unique PKG_NUMs
[INFO] TOTAL PIN COUNT: 48 ✓
[INFO] Generating PKG PDF...
[INFO] Generating APR PDF...
[INFO] Generating Combined PDF...
[INFO] Done.
```

---

## 12. 欄位別名對照表

CSV 表頭行中，每個欄位可使用以下任一名稱（不區分大小寫）：

| 正式名稱 | 別名 1 | 別名 2 | 別名 3 | 別名 4 |
|---------|--------|--------|--------|--------|
| `PKG_NUM` | `PIN_NUM` | — | — | — |
| `PKG_PIN_NAME` | `PACKAGE_PIN` | `PKG_PIN` | — | — |
| `DIE_NUM` | `DIE_PAD_NUM` | — | — | — |
| `DIE_PIN_NAME` | `PIN_NAME` | — | — | — |
| `IO_CELL_NAME` | `CELL_NAME` | `IO_CELL` | `IOCELL` | — |
| `PKG_LOC` | `LOCATION` | `PIN_LOCA` | — | — |
| `DIE_LOC` | `DIE_PAD_NUM_LOC` | `DIE_LOCA` | — | — |
| `DIRECTION` | `IO_DIRECTION` | `IO_TYPE` | `DIR` | — |
| `LOAD` | `CAP` | `CAPACITANCE` | — | — |
| `SLEW` | `TRANSITION` | `SLEW_RATE` | — | — |
| `SSO` | `SSO_RATIO` | — | — | — |

> 工具內部統一使用左欄正式名稱，輸出的 `.new` 和 `.new.csv` 也使用正式名稱。

---

*文件產生時間：2026-05-07 | 工具版本：v5*
*詳細格式規格請參閱 `docs/CSV_INPUT_SPEC.md`*
