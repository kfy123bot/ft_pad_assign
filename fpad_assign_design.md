# FPAD_ASSIGN 腳本製作 - 終極基因藍圖 (v6.0 - Multi-Language Unified)

本文件詳盡記錄了 `fpad_assign` 專案在 Perl, Python 與 C++ 三種語言下的核心設計、解析演算法與 PDF 繪圖邏輯。本專案確保三種語言實作具備功能對等性 (Feature Parity)。

---

## 1. 工具定義與架構

*   **定位**：自動化 IC I/O Assignment 與視覺化驗證工具。
*   **支援語言**：
    *   **Perl (Legacy/Stable)**: `bin/fpad_assign.pl` (使用 `PDF::API2`)。
    *   **Python (Modern/Flexible)**: `bin/fpad_assign.py` (使用 `reportlab`)。
    *   **C++ (High-Performance/Independent)**: `bin/fpad_assign.cpp` (內建 `MiniPDF` 引擎)。
*   **核心模組 (共通架構)**：
    *   **Parser**：解析 Pin List 與 Verilog Netlist，執行資料聯集。
    *   **Bridge**：對齊 Pin 與 Verilog 訊號、Cell 型號及實體名稱。
    *   **PDF Generator**：生成 APR (Pad-view) 與 PKG (Pin-view) 圖表。
    *   **Checker**：執行 Stagger Check 密度檢查。
    *   **Writer**：產出補全後的 List 與 Innovus IO Constraint (`_chip.const`)。

---

## 2. 關鍵字處理規則 (Reserved Logic)

### 2.1 命名解析 (`xx%yy%zz`)
*   **APR 模式**：讀取最後一段 `zz` (Pad Name)。用於訊號匹配與標註。
*   **PKG 模式**：讀取第一段 `xx` (Package Name)。用於封裝視圖標註。

### 2.2 方向 (DIRECTION) 優先級
1.  **強制判定**：若 `DIRECTION` 欄位為 `P` (Power) 或 `G` (Ground)，則無視名稱，一律判定為電源/地線。
2.  **自動填充**：若為空值，則依據 Verilog Port 宣告 (`input/output/inout`) 補全。
3.  **色彩聯動**：`P` = 紅色 (#FF0000), `G` = 藍色 (#0000FF), `POWERCUT` = 黑色 (#000000)。

### 2.3 視圖差異化邏輯
*   **APR 視圖**：完全過濾 `NC` (不繪製、不佔位)。標註 `DIE_PAD_NUM`。
*   **PKG 視圖**：保留 `NC`。執行 `PIN_NUM` 排重（Deduplication），多個 Bond-wire 接到同一 Pin 時合併繪製。標註 `PIN_NUM`。

---

## 3. 解析與聯集演算法 (The Brain)

### 3.1 訊號匹配 (Signal Mode)
*   **Verilog Ports**：掃描 `input/output/inout` 宣告捕捉方向。
*   **Verilog Instances**：掃描 `CellType InstanceName (.PAD(NetName))`，建立 `NetName -> CellType` 與 `NetName -> InstanceName` 的雙向映射。

### 3.2 實體匹配 (Instance Mode)
*   **適用對象**：`POWERCUT` 與 Power/Ground 實體。
*   **規則**：直接比對 Verilog 內的 `Instance Name`。若 Pin List 中的名稱經清洗後與 Verilog 實體名一致，則抓取該實體所屬的 Cell 型號。

---

## 4. PDF 視覺化演算法 (The Face)

### 4.1 智能自動縮放 (Auto-Scaling)
解決單邊 100+ Pins 擁擠問題的核心公式：
1.  **動態步進**：`Step = 邊長 / (MAX(實際 Pin 數, 封裝定義數) + 1)`。
2.  **引腳盒子縮放**：`厚度 = Step * 0.8` (上限 6pt, 下限 1pt)。
3.  **字體縮放**：`大小 = Step * 0.9` (上限 7pt, 下限 2pt)。
4.  **座標對齊**：
    *   **左 (L)**：從上往下繪製。文字向左對齊 (Right-aligned to point)。
    *   **底 (B)**：從左往右繪製。文字旋轉 270 度。
    *   **右 (R)**：從下往上繪製。文字向右對齊 (Left-aligned to point)。
    *   **頂 (T)**：從右往左繪製。文字旋轉 90 度。

### 4.2 各語言繪圖實現
*   **Perl**: 使用 `PDF::API2`。需注意字體物件的獨立實體化以避免多頁警告。
*   **Python**: 使用 `reportlab`。支援 `saveState()` 與 `restoreState()` 處理旋轉座標系。
*   **C++ (MiniPDF)**: 透過直接寫入 PDF 1.4 物件 (Catalog, Pages, GFX stream) 實現。使用 `Tm` 指令矩陣處理文字旋轉。

---

## 5. 設計檢查 (DRC) 與輸出

### 5.1 Stagger Check
*   **邏輯**：連續 I/O 腳位（I, O, B）數量不得超過 8 個。
*   **中斷條件**：遇到電源 (P) 或地線 (G) 時計數器歸零。
*   **輸出**：產出 `_stagger.rpt` 報告。

### 5.2 Innovus IO Constraint
*   **格式**：Version 2。
*   **結構**：按 `left`, `bottom`, `right`, `top` 四邊分組。
*   **語法**：`(inst name="INST_NAME" spacing=0 offset=0 place_status=placed)`。

---

## 6. 專案建置與驗證流程

### 6.1 C++ 版建置 (Makefile)
*   `make`：編譯 `bin/fpad_assign`。
*   `make test`：自動使用 `examples/` 檔案驗證功能。
*   `make clean`：清理執行檔與測試產物。

### 6.2 測試基準 (Test Bench)
*   **輸入 1**：`examples/example.pin_list` (一般 QFP 封裝)。
*   **輸入 2**：`examples/qfn64.pin_list` (高密度 QFN 封裝)。
*   **驗證標準**：確保產出的 `.pdf`, `.new`, `.const`, `.rpt` 四大檔案內容與 Perl 標竿一致。
