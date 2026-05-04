# FT_PAD_ASSIGN CSV 輸入規格說明書

> 本文檔說明 `bin/ft_pad_assign.py` 的 `-list xx.csv` 輸入檔案格式規範。
> 基於源碼分析，涵蓋所有欄位（必要/選填）、特殊列類型、欄位別名、自動處理規則。

---

## 目錄

1. [檔案整體結構](#1-檔案整體結構)
2. [Header 元資料區](#2-header-元資料區)
3. [CSV 資料表頭行](#3-csv-資料表頭行)
4. [11 個資料欄位詳解](#4-11-個資料欄位詳解)
5. [特殊列類型](#5-特殊列類型)
6. [自動處理流程](#6-自動處理流程)
7. [完整範例](#7-完整範例)
8. [常見錯誤與注意事項](#8-常見錯誤與注意事項)
9. [附錄：欄位別名對照表](#9-附錄欄位別名對照表)

---

## 1. 檔案整體結構

CSV 檔案由三個區塊組成，順序固定：

```
┌─────────────────────────────────┐
│  Header 元資料區（key : value）  │  ← 必要
│  PRODUCTION NO / PROJECT NO     │
│  PKG_TOP_LEFT_PIN               │
│  PACKAGE                        │
│  VERSION                        │
├─────────────────────────────────┤
│  （空白行分隔）                   │
├─────────────────────────────────┤
│  CSV 資料表頭行                   │  ← 必要（欄位名稱）
├─────────────────────────────────┤
│  資料列 1                        │
│  資料列 2                        │
│  ...                            │
│  資料列 N                        │
├─────────────────────────────────┤
│  （空白行）                       │
├─────────────────────────────────┤
│  Inner_bond 模板區（選填）       │
└─────────────────────────────────┘
```

### 檔案副檔名

- `.csv` — 以逗號分隔，使用 `csv.DictReader` 解析
- `.pin_list` — 以 Tab 分隔，逐行解析（規則相同，僅分隔符不同）

本文檔以 `.csv` 格式為主進行說明。

---

## 2. Header 元資料區

位於檔案最上方，每行格式為 `KEY : VALUE`。CSV 格式中，VALUE 後方可帶多餘逗號（會被自動去除）。

### 2.1 必要欄位

#### PRODUCTION NO / PROJECT NO

```
PRODUCTION NO  : PRJ8028_QFN48_TEST,,,,,,,,,,,,
```

| 項目 | 說明 |
|------|------|
| **用途** | 專案代號，用於產生所有輸出檔名（`.log`、`.new`、`.pdf` 等） |
| **別名** | `PRODUCTION NO`、`PRODUCTION NO.`、`PROJECT NO`、`PROJECT NO.` 四種寫法等價 |
| **正規化** | 代碼自動將 `PROJECT NO` 統一為 `PRODUCTION NO` |
| **檔名處理** | 非字母數字字元（底線和連字號除外）轉為 `_`，尾端空白/底線去除 |
| **空值處理** | 若缺失，檔名 fallback 為 `fpad_out` |

#### PACKAGE

```
PACKAGE : 48QFN 12 12 12 12,,,,,,,,,,,,
```

| 項目 | 說明 |
|------|------|
| **用途** | 定義封裝類型及四邊 pin 數量 |
| **格式** | `<封裝類型> <L數量> <B數量> <R數量> <T數量>` |
| **要求** | 至少 5 個以空白分隔的欄位，後四個必須為正整數 |
| **驗證** | `L + B + R + T` 必須等於資料列中有效 `PKG_NUM`（正整數）的唯一數量 |

**範例**：

| 值 | 封裝 | L | B | R | T | 總計 |
|----|------|---|---|---|---|------|
| `48QFN 12 12 12 12` | QFN48 | 12 | 12 | 12 | 12 | 48 |
| `56QFN 14 14 14 14` | QFN56 | 14 | 14 | 14 | 14 | 56 |
| `40QFN 10 10 10 10` | QFN40 | 10 | 10 | 10 | 10 | 40 |

### 2.2 選填欄位

#### PKG_TOP_LEFT_PIN

```
PKG_TOP_LEFT_PIN : 15,,,,,,,,,,,,
```

| 項目 | 說明 |
|------|------|
| **用途** | 指定 L 邊第一根 pin 的起始編號 |
| **預設值** | `1`（L 邊從 pin 1 開始） |
| **觸發條件** | 若值不為 `1`，會觸發 **ring shift** 重排（詳見[第 6 節](#6-自動處理流程)） |
| **重排後** | PKG_NUM 從 1 重新編號，此值被重置為 `1` |

**範例**：`PKG_TOP_LEFT_PIN : 15` 表示原始 pin 15 應為 L 邊第一根 pin。

#### VERSION

```
VERSION : V1.0_20240418,,,,,,,,,,,,
```

| 項目 | 說明 |
|------|------|
| **用途** | 版本資訊，顯示於 PDF header |
| **限制** | 無，任意字串 |

### 2.3 Header 書寫注意事項

1. **Key 不區分大小寫**：`production no`、`PRODUCTION NO`、`Production No` 均可
2. **冒號前可有逗號**：CSV 格式中常見 `PRODUCTION NO  : value,,,,,,,,,,,`，代碼會自動處理
3. **Header 行識別依據**：行內包含 `:` 且不以數字、`(` 或 `D` 開頭
4. **行順序不固定**：四個 Header 欄位可任意排列
5. **可額外增加欄位**：非上述四個的 Header 行會被忽略（不報錯）

---

## 3. CSV 資料表頭行

### 3.1 識別方式

代碼透過掃描所有行，找到包含 `PKG_NUM`（或其別名）的行作為表頭行。表頭行之前的所有行視為 Header 元資料。

### 3.2 欄位名稱

表頭行使用逗號分隔的欄位名稱。欄位名稱支援 **別名匹配**（詳見[第 9 節](#9-附錄欄位別名對照表)）。

**標準寫法**：

```
PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO
```

**其他合法寫法**（使用別名）：

```
PIN_NUM,PACKAGE_PIN,DIE_PAD_NUM,PIN_NAME,CELL_NAME,LOCATION,DIE_LOCA,DIR,CAP,TRANSITION,SSO_RATIO
```

### 3.3 欄位順序

欄位順序 **不固定**。代碼使用 `csv.DictReader` 按名稱匹配，而非按位置。

### 3.4 多餘欄位

表頭行可包含額外欄位（如末尾的多餘逗號產生的空欄位），代碼會忽略不在 `FIELD_ALIASES` 中的欄位。

---

## 4. 11 個資料欄位詳解

### 4.1 必要欄位

#### PKG_NUM — 封裝腳位編號

| 值類型 | 範例 | 行為 |
|--------|------|------|
| **正整數** | `1`, `2`, `48` | 正常封裝腳位。按數值順序分配到 L→B→R→T 四邊 |
| **`0`** | `0` | 共用 die pad（無獨立封裝腳位）。PKG PDF 不顯示；若 DIRECTION=G 則繪製接地符號 |
| **`D1.xx`** | `D1.94` | Inner Bond 動態參考（無括號）。方向：xx → 當前列的 DIE_NUM |
| **`(D1.xx)`** | `(D1.35)` | Inner Bond 動態參考（有括號）。方向：當列 DIE_NUM → xx |
| **`Inner_bond`** | `Inner_bond` | 註解/模板列，不參與 pin 計數和 PDF 繪製 |
| **`-` 或空** | `-`, `` | 無效/佔位列，PKG PDF 不顯示 |

**重要規則**：
- 正整數的 PKG_NUM 會在 `PKG_TOP_LEFT_PIN != 1` 時被 **重新編號**（從 1 開始）
- `D1.xx` 中的 `xx` 會在 DIE_NUM 重編後 **動態更新**

#### DIE_NUM — 晶粒墊片編號

| 值類型 | 範例 | 行為 |
|--------|------|------|
| **正整數** | `1`, `103`, `72` | 正常 die pad。會被重新編號（從 L 邊第一根非 NC pin 開始為 1） |
| **`0`** | `0` | 無 die pad（NC、DOWNBOND、或共用 pad），APR PDF 不顯示 |
| **`-` 或空** | `-`, `` | 視為無效列，不參與 DIE_NUM 重編 |

**重編規則**：
- 從資料中第一根 L 邊非 NC、非 `0` 的 pin 開始，編號為 1
- 相同原始 DIE_NUM 的列會被賦予相同的新編號（去重）
- NC 和 DIE_NUM=0 的列統一設為 `0`

#### DIE_PIN_NAME — 晶粒側 pin 名稱

**最關鍵的欄位**，決定 pin 的類型和 PDF 顯示行為。

| 特殊值 | PKG PDF | APR PDF | Combined PDF | 說明 |
|--------|---------|---------|-------------|------|
| `NC` | 黑色實心方塊 | **跳過** | **跳過** | No Connect |
| `DOWNBOND` | 藍色方塊 | **跳過** | **跳過**（繪製接地符號） | 接地/bonding 端點 |
| `POWERCUT` | **跳過** | 黑色實心方塊 | **跳過** | Power cut |
| 其他值 | 正常顯示 | 正常顯示 | 正常顯示 | 一般 pin |

**名稱格式**：

| 格式 | 範例 | PKG 顯示 | APR 顯示 |
|------|------|---------|---------|
| 一般名稱 | `MIPI_CSI_RX_L0P` | `MIPI_CSI_RX_L0P` | `MIPI_CSI_RX_L0P` |
| 帶 `%` 分隔 | `VDD11%C%U_AIP_TOP/U_VDD11_APR5` | `VDD11`（第一段） | `U_VDD11_APR5`（最後一段） |
| 帶 `%`（多段） | `VDD33_IOB%IO%U_AIP_TOP/U_VDD33_IOB0` | `VDD33_IOB` | `U_VDD33_IOB0` |

**`%` 分隔規則**：
- PKG PDF：取 `%` 之前的第一段
- APR PDF：取 `%` 之後的最後一段
- 若分割後為空，則使用完整名稱

#### PKG_LOC — 封裝側邊位置

| 值 | 說明 |
|----|------|
| `L` | 左邊（Left） |
| `B` | 下邊（Bottom） |
| `R` | 右邊（Right） |
| `T` | 上邊（Top） |
| `-` 或空 | **會被自動補上** |

**自動計算規則**：`PKG_LOC` 由 `_reassign_pkg_loc()` 根據 PKG_NUM 的 ring 順序和 PACKAGE header 的 L/B/R/T 數量自動計算。**手動填寫的值會被覆蓋**。

分配邏輯（以 `PACKAGE : 48QFN 12 12 12 12` 為例）：

| PKG_NUM 範圍 | 分配邊 |
|-------------|--------|
| 1 ~ 12 | L |
| 13 ~ 24 | B |
| 25 ~ 36 | R |
| 37 ~ 48 | T |

#### DIE_LOC — 晶粒側邊位置

| 值 | 說明 |
|----|------|
| `L` / `B` / `R` / `T` | 晶粒四邊 |
| `-` 或空 | 在特定條件下會被自動補上 |

**自動補全條件**：僅在 `PKG_TOP_LEFT_PIN != 1`（ring 被 shift）時，`_reassign_die_loc()` 才會將 DIE_LOC 設為與 PKG_LOC 相同。若 `PKG_TOP_LEFT_PIN = 1`，則維持手動填寫的原始值。

### 4.2 選填欄位

#### PKG_PIN_NAME — 封裝側 pin 名稱

| 值 | 行為 |
|----|------|
| 有值（如 `VDD33_ANA`） | PKG PDF 上顯示此名稱 |
| 空或 `-` | fallback 到 `DIE_PIN_NAME` |

**影響範圍**：僅影響 PKG PDF（standalone + combined 的外框）的 pin 標籤文字。

#### IO_CELL_NAME — IO Cell 名稱

| 值 | 行為 |
|----|------|
| 有值 | 直接使用 |
| 空、`-`、`NOT_FOUND` | 若有提供 Verilog（`-v` 參數），會自動從 Verilog 中查找填入 |

**Verilog bridging 邏輯**：
- 一般訊號 pin：從 `.PAD(net)` 連接查找 cell name
- 電源/接地 pin（含 `%` 或 DIRECTION=P/G）：從 instance name 查找

#### DIRECTION — 腳位方向

| 值 | 行為 | PDF 顏色 |
|----|------|---------|
| `P` | 電源（Power） | 紅色 |
| `G` | 接地（Ground） | 藍色 |
| `-` 或空 | 一般訊號 | 灰色（wire）/ 空心矩形（pin） |

**自動填入**：若有提供 Verilog，方向為 `-` 的一般訊號 pin 會嘗試從 Verilog 的 port direction 自動填入（`I`→input, `O`→output, `B`→inout）。

#### LOAD — 電容值

| 項目 | 說明 |
|------|------|
| **用途** | Stagger check 報告使用 |
| **影響** | 不影響 PDF 顯示 |
| **格式** | 任意字串或數值 |

#### SLEW — 轉換率

| 項目 | 說明 |
|------|------|
| **用途** | Stagger check 報告使用 |
| **影響** | 不影響 PDF 顯示 |
| **格式** | 任意字串或數值 |

#### SSO — SSO 比值

| 項目 | 說明 |
|------|------|
| **用途** | Stagger check 報告使用 |
| **影響** | 不影響 PDF 顯示 |
| **格式** | 任意字串（可含附註如 `RX`、`TX`） |

---

## 5. 特殊列類型

### 5.1 共用 Die Pad 列（PKG_NUM = 0）

多個封裝 pin 對應同一個 die pad，或無獨立封裝 pin 的 die pad：

```csv
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX
```

**規則**：
- 同一個 `DIE_NUM` 可出現 N 次
- `PKG_NUM` 必須為 `0`
- 接地線數量 = 出現次數（上例 = 3 條接地線）
- APR PDF 中該 die pad 只顯示一次（去重）

### 5.2 Inner Bond 動態參考列

用於連接不同邊的 die pad（跨邊連接）：

```csv
D1.94,,33,VDD11%C%U_AIP_TOP/U_VDD11_APR5,-,-,B,P,-,-,-
(D1.35),,84,VDD33_IOT%IO%U_AIP_TOP/U_VDD33_IOT0,-,-,T,P,-,-,-
```

**方向規則**（以 DIE_NUM 為基準）：

| 格式 | PKG_NUM | DIE_NUM | 連接方向 |
|------|---------|---------|---------|
| `D1.xx` | `D1.77` | `42` | DIE_NUM(77) → DIE_NUM(42) |
| `(D1.xx)` | `(D1.77)` | `42` | DIE_NUM(42) → DIE_NUM(77) |

**對稱性判定**：

| 結果 | 線條樣式 | Log |
|------|---------|-----|
| A→B 且 B→A 同時存在 | 實線（solid） | INFO |
| 只有 A→B 或只有 B→A | 虛線（dashed） | ERROR |

**多重線偏移**：同一 (source, dest) 出現 N 次時，繪製 N 條平行線，偏移量 = `(i - (N-1)/2) * 2`。

**D1.xx 動態更新**：DIE_NUM 重編後，`D1.xx` 中的 `xx` 會自動更新為新的 DIE_NUM。

### 5.3 DOWNBOND 列

```csv
17,,0,DOWNBOND,-,B,-,G,-,-,RX
```

| 欄位 | 值 | 說明 |
|------|-----|------|
| `PKG_NUM` | 正整數 | 有封裝腳位 |
| `DIE_NUM` | `0` | 無 die pad |
| `DIE_PIN_NAME` | `DOWNBOND` | 特殊名稱 |
| `DIRECTION` | `G` | 接地 |

**PDF 行為**：
- PKG PDF：藍色方塊
- APR PDF：跳過
- Combined PDF：跳過，繪製接地符號（倒 T 形）

### 5.4 NC 列

```csv
35,,0,NC,-,R,R,-,-,-,TX
```

| 欄位 | 值 | 說明 |
|------|-----|------|
| `PKG_NUM` | 正整數 | 有封裝腳位 |
| `DIE_NUM` | `0` | 無 die pad |
| `DIE_PIN_NAME` | `NC` | No Connect |

**PDF 行為**：
- PKG PDF：黑色實心方塊
- APR PDF：跳過
- Combined PDF：跳過

### 5.5 POWERCUT 列

```csv
0,,84,POWERCUT,-,-,T,-,-,-,-
```

| 欄位 | 值 | 說明 |
|------|-----|------|
| `PKG_NUM` | `0` | 無封裝腳位 |
| `DIE_NUM` | 正整數 | 有 die pad |
| `DIE_PIN_NAME` | 含 `POWERCUT` | 特殊名稱 |

**PDF 行為**：
- PKG PDF：跳過
- APR PDF：黑色實心方塊
- Combined PDF：跳過

### 5.6 Inner_bond 模板列（檔案尾部）

```csv
Inner_bond,,1,I0 (X.Y),I1 (X.Y),,,,,,,,
Inner_bond,,2,I2 (X.Y),(X.Y),,,,,,,,
```

**規則**：
- 不參與 pin 計數和 PDF 繪製
- 原樣保留到 `.new` 輸出
- 用於記錄設計意圖（佔位符）
- `DIE_NUM` 欄位用於序號

### 5.7 空列 / 佔位列

```csv
0,,0,-,-,-,B,-,-,-,-
```

- `PKG_NUM` = `0`，`DIE_NUM` = `0`，`DIE_PIN_NAME` = `-`
- 無實際意義，可用於分隔或佔位
- 在 `.new` 輸出中會被跳過（PKG_NUM 和 DIE_NUM 同時為 `-`）

### 5.8 無 PKG_NUM 的共享 Die Pad 列

```csv
,,21,VBAT_PIO_0,-,,B,,,,
,,22,VBAT_PIO_1,-,,B,,,,
```

- `PKG_NUM` 為空
- `DIE_NUM` 有值
- 表示此 die pad 無獨立封裝 pin，但有 die pad
- APR PDF 會顯示，PKG PDF 不顯示

---

## 6. 自動處理流程

解析完成後，代碼按以下順序自動處理 `self.data`：

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. _ring_shift_data()                                           │
│    條件：PKG_TOP_LEFT_PIN != 1                                   │
│    作用：重排 self.data，使 PKG_TOP_LEFT_PIN 指定的 pin 成為第一列 │
├─────────────────────────────────────────────────────────────────┤
│ 2. _reindex_pkg_num()                                           │
│    條件：PKG_TOP_LEFT_PIN != 1                                   │
│    作用：PKG_NUM 從 1 重新編號，PKG_TOP_LEFT_PIN 重置為 1        │
├─────────────────────────────────────────────────────────────────┤
│ 3. _reassign_pkg_loc()                                          │
│    條件：始終執行                                                 │
│    作用：根據 PKG_NUM ring 順序重新計算四邊 PKG_LOC              │
│    驗證：L+B+R+T 總數 vs 有效 PKG_NUM 唯一數量                   │
├─────────────────────────────────────────────────────────────────┤
│ 4. _reassign_die_loc()                                          │
│    條件：僅在 ring 被 shift（步驟 1 執行過）時                   │
│    作用：DIE_LOC 跟隨 PKG_LOC（共用 pad 跟隨最近的 side）        │
├─────────────────────────────────────────────────────────────────┤
│ 5. _sanity_check_list()                                         │
│    條件：始終執行                                                 │
│    作用：驗證四邊 pin 數 = PACKAGE header 定義                   │
│    輸出：每邊通過/失敗 + 總數校驗                                │
├─────────────────────────────────────────────────────────────────┤
│ 6. _reorder_and_reindex_apr_data()                              │
│    條件：始終執行                                                 │
│    作用：                                                         │
│    a) DIE_NUM 從 L 邊第一根非 NC pin 重編為 1                   │
│    b) 更新所有 D1.xx 參照中的 xx 為新 DIE_NUM                   │
│    c) 相同原始 DIE_NUM → 相同新編號（去重）                      │
└─────────────────────────────────────────────────────────────────┘
```

### 6.1 Ring Shift 詳解（步驟 1）

當 `PKG_TOP_LEFT_PIN = 15` 且 `PACKAGE = 56QFN 14 14 14 14` 時：

- 原始順序：pin 1, 2, 3, ..., 56
- Ring 位置計算：`ring_pos = (pin_num - offset - 1) % total`，其中 `offset = 15 - 1 = 14`
- 重排後：pin 15 成為第一列（L 邊起點），pin 14 成為最後一列

### 6.2 PKG_NUM 重編（步驟 2）

Ring shift 後，PKG_NUM 從 1 重新編號：
- 正整數 PKG_NUM：依序改為 1, 2, 3, ...
- `0`、`-`、`D1.xx`、`Inner_bond`：不參與重編

### 6.3 PKG_LOC 重算（步驟 3）

根據 PKG_NUM 和 PACKAGE header 的 L/B/R/T 數量，按 ring 順序分配：
- PKG_NUM 1 ~ L數量 → L
- PKG_NUM L+1 ~ L+B數量 → B
- 以此類推

### 6.4 Sanity Check（步驟 5）

驗證項目：
1. 每邊的唯一 PKG_NUM 數量 = PACKAGE header 對應邊的數量
2. 四邊總計 = L + B + R + T
3. DOWNBOND 的 PKG_NUM 計入對應邊
4. `0`、`D1.xx`、`Inner_bond` 不計入

---

## 7. 完整範例

### 7.1 最小範例（QFN40）

```csv
PRODUCTION NO  : PRJ8803_QFN40_TEST,,,,,,,,,,
PKG_TOP_LEFT_PIN : 1,,,,,,,,,,
PACKAGE : 40QFN 10 10 10 10,,,,,,,,,,
VERSION : V1.0_20260428,,,,,,,,,,
,,,,,,,,,,
PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO
1,VDD33_ANA,1,,-,L,L,P,,,
2,MIPI_CSI_RX_L0P,2,MIPI_CSI_RX_L0P,-,L,L,,,,
3,MIPI_CSI_RX_L0N,3,MIPI_CSI_RX_L0N,-,L,L,,,,
4,MIPI_CSI_RX_L1P,4,MIPI_CSI_RX_L1P,-,L,L,,,,
5,MIPI_CSI_RX_L1N,5,MIPI_CSI_RX_L1N,-,L,L,,,,
6,MIPI_CSI_RX_CLKP,6,MIPI_CSI_RX_CLKP,-,L,L,,,,
7,MIPI_CSI_RX_CLKN,7,MIPI_CSI_RX_CLKN,-,L,L,,,,
8,VDD11,8,,-,L,L,P,,,
9,VDD33,9,,-,L,L,P,,,
10,BOOT0_PIO_0,10,PIO_0,-,L,L,,,,
11,BOOT1_PIO_1,11,PIO_1,-,B,L,,,,
12,BOOT2_PIO_2,12,PIO_2,-,B,L,,,,
13,TEST,13,TEST,-,B,L,,,,
14,RESETN,14,RESETN,-,B,L,,,,
15,LDO_EN,15,LDO_EN,-,B,B,,,,
16,PIO_3,16,PIO_3,-,B,B,,,,
17,PIO_4,17,PIO_4,-,B,B,,,,
18,PIO_5,18,PIO_5,-,B,B,,,,
19,PIO_6,19,PIO_6,-,B,B,,,,
0,,20,,-,,B,,,,
...
40,PIO_21,72,PIO_31,-,T,T,,,,
,,,,,,,,,,
Inner_bond,,1,I0 (X.Y),I1 (X.Y),,,,,,
```

### 7.2 完整範例（含特殊列）

```csv
PRODUCTION NO  : PRJ8028_QFN48_TEST,,,,,,,,,,,,
PKG_TOP_LEFT_PIN : 1,,,,,,,,,,,,
PACKAGE : 48QFN 12 12 12 12,,,,,,,,,,,,
VERSION : V1.0_20240418,,,,,,,,,,,,
,,,,,,,,,,,,
PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO,,
1,,103,SCL,-,L,T,-,-,-,-,,
2,,104,SDA,-,L,T,-,-,-,-,,
0,,107,GND%C%U_AIP_TOP/U_GND_APR8,-,-,T,G,-,-,-,,    ← 共用接地 pad
0,,107,GND%C%U_AIP_TOP/U_GND_APR8,-,-,T,G,-,-,-,,    ← 重複出現（2 條接地線）
(D1.94),,1,VDD11%C%U_AIP_TOP/U_VDD11_APR5,-,-,L,P,-,-,-,,  ← Inner Bond（有括號）
5,,2,VDD33%IO%U_AIP_TOP/U_VDD33_INTPLL,-,L,L,P,-,-,-,,
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX,X,Y                ← 共用接地（3 條）
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX,X,Y
0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX,X,Y
35,,0,NC,-,R,R,-,-,-,TX,,                            ← NC 列
17,,0,DOWNBOND,-,B,-,G,-,-,RX,,                     ← DOWNBOND 列
D1.94,,33,VDD11%C%U_AIP_TOP/U_VDD11_APR0,-,-,B,P,-,-,-,,  ← Inner Bond（無括號）
D1.84,,35,VDD33_IOB%IO%U_AIP_TOP/U_VDD33_IOB0,-,-,B,-,-,-,-,,
...
```

---

## 8. 常見錯誤與注意事項

### 8.1 ERROR 級別

| 錯誤 | 原因 | 解決方式 |
|------|------|---------|
| `Side X check FAILED` | 某邊實際 pin 數 ≠ PACKAGE header 定義 | 檢查 PKG_NUM 是否正確、是否有遺漏或多餘 |
| `TOTAL PIN COUNT MISMATCH` | 四邊總計 ≠ PACKAGE header 總和 | 同上 |
| `Inner Bond ASYMMETRIC` | 只有 A→B 沒有 B→A | 補上反向的 D1.xx 列 |
| `PKG_LOC reassign TOTAL MISMATCH` | 有效 PKG_NUM 數量 ≠ L+B+R+T | 檢查 PKG_NUM 編號是否連續、是否有重複 |

### 8.2 WARN 級別

| 警告 | 原因 | 影響 |
|------|------|------|
| `PACKAGE definition missing` | Header 缺少 PACKAGE | 無法進行 pin 分配和驗證 |
| `No L-side signal pin found` | 沒有 L 邊的非 NC pin | DIE_NUM 重編被跳過 |
| `D1.xx reference target not found` | D1.xx 的目標 DIE_NUM 不存在 | 該 Inner Bond 連接被跳過 |

### 8.3 常見陷阱

1. **PKG_LOC 手動填寫無效**：代碼會根據 PKG_NUM 自動重算，手動值被覆蓋
2. **DIE_LOC 在 PKG_TOP_LEFT_PIN=1 時不自動補全**：需手動填寫正確的 L/B/R/T
3. **DIE_NUM 會被重編**：原始值僅用於 D1.xx 參照解析，最終值由代碼決定
4. **相同 DIE_NUM 的列共享 APR pin**：APR PDF 去重，只顯示一次
5. **`%` 在 DIE_PIN_NAME 中有特殊意義**：用於分隔 PKG 顯示名和 APR 顯示名
6. **`0` 和 `-` 含義不同**：`0` 表示「共用/無」，`-` 表示「無效/空」
7. **NC 的 DIE_NUM 必須為 `0`**：否則會被當作正常 pin 參與重編
8. **DOWNBOND 的 DIE_NUM 必須為 `0`**：否則會被當作正常 pin
9. **Header 行末尾的逗號**：CSV 格式中常見，代碼自動去除，不影響解析
10. **空白行**：Header 區和資料區之間、資料區和 Inner_bond 區之間的空白行會被自動跳過

---

## 9. 附錄：欄位別名對照表

代碼使用 `FIELD_ALIASES` 字典進行欄位名稱匹配。CSV 表頭行中，每個欄位可使用以下任一名稱：

| 正式名稱 | 別名 1 | 別名 2 | 別名 3 | 別名 4 |
|---------|--------|--------|--------|--------|
| `PKG_NUM` | `PKG_NUM` | `PIN_NUM` | — | — |
| `PKG_PIN_NAME` | `PKG_PIN_NAME` | `PACKAGE_PIN` | `PKG_PIN` | — |
| `DIE_NUM` | `DIE_NUM` | `DIE_PAD_NUM` | — | — |
| `DIE_PIN_NAME` | `DIE_PIN_NAME` | `PIN_NAME` | — | — |
| `IO_CELL_NAME` | `IO_CELL_NAME` | `CELL_NAME` | `IO_CELL` | `IOCELL` |
| `PKG_LOC` | `PKG_LOC` | `LOCATION` | `PIN_LOCA` | — |
| `DIE_LOC` | `DIE_LOC` | `DIE_PAD_NUM_LOC` | `DIE_LOCA` | — |
| `DIRECTION` | `DIRECTION` | `IO_DIRECTION` | `IO_TYPE` | `DIR` |
| `LOAD` | `LOAD` | `CAP` | `CAPACITANCE` | — |
| `SLEW` | `SLEW` | `TRANSITION` | `SLEW_RATE` | — |
| `SSO` | `SSO` | `SSO_RATIO` | — | — |

**匹配規則**：
- 不區分大小寫
- 欄位名稱先 strip 再 uppercase
- 空值（`""`）在資料列中被轉為 `"-"`

---

## 10. 附錄：內部欄位名稱

代碼內部統一使用以下欄位名稱（不論輸入使用何種別名）：

| 欄位 | 說明 |
|------|------|
| `PKG_NUM` | 封裝腳位編號 |
| `PKG_PIN_NAME` | 封裝側 pin 名稱 |
| `DIE_NUM` | 晶粒墊片編號 |
| `DIE_PIN_NAME` | 晶粒側 pin 名稱 |
| `IO_CELL_NAME` | IO Cell 名稱 |
| `PKG_LOC` | 封裝側邊位置 |
| `DIE_LOC` | 晶粒側邊位置 |
| `DIRECTION` | 腳位方向 |
| `LOAD` | 電容值 |
| `SLEW` | 轉換率 |
| `SSO` | SSO 比值 |
| `INST_NAME` | Instance 名稱（自動填入，非 CSV 欄位） |

---

## 11. 附錄：代碼位置參考

| 功能 | 函數 | 行號（約） |
|------|------|-----------|
| 別名定義 | `FIELD_ALIASES` | 70-82 |
| CSV 解析 | `_parse_csv()` | 121-201 |
| Tab 解析 | `_parse_txt()` | 203-268 |
| Ring Shift | `_ring_shift_data()` | 434-477 |
| PKG_NUM 重編 | `_reindex_pkg_num()` | 479-509 |
| PKG_LOC 重算 | `_reassign_pkg_loc()` | 511-561 |
| DIE_LOC 重算 | `_reassign_die_loc()` | 563-592 |
| Sanity Check | `_sanity_check_list()` | 338-396 |
| DIE_NUM 重編 | `_reorder_and_reindex_apr_data()` | 270-336 |
| Side 計算 | `_get_ring_side()` | 398-432 |
| .new 輸出 | `generate_completed_list()` | 1333-1367 |
| .new.csv 輸出 | `generate_completed_csv()` | 1369-1392 |
