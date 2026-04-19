# FPAD_ASSIGN 腳本製作 - 終極基因藍圖 (v5.0 - Final)

本文件詳盡記錄了 `fpad_assign.pl` 的核心設計、解析演算法與 PDF 繪圖邏輯，確保本專案的功能可完全透過此文檔復刻。

---

## 1. 工具定義與架構

*   **定位**：自動化 IC I/O Assignment 與視覺化驗證工具。
*   **語言**：Perl 5.10+。
*   **核心模組**：
    *   `FPAD::Parser`：解析 List 與 Verilog，執行資料聯集。
    *   `FPAD::PDF`：生成 APR (Pad-view) 與 PKG (Pin-view) 圖表。
    *   `FPAD::Checker`：執行 Stagger Check 密度檢查。
    *   `FPAD::Logger`：標準化日誌輸出。

---

## 2. 關鍵字處理規則 (Reserved Logic)

### 2.1 命名解析 (`xx%yy%zz`)
*   **APR 模式**：讀取最後一段 `zz` (Pad Name)。
*   **PKG 模式**：讀取第一段 `xx` (Package Name)。

### 2.2 方向 (DIRECTION) 優先級
1.  **強制判定**：若 `DIRECTION` 欄位為 `P` 或 `G`，則無視名稱，一律判定為 Power/Ground。
2.  **自動填充**：若為空值，則依據 `VDD` 或 `VSS` 前綴自動補全。
3.  **色彩聯動**：`P` = 紅色, `G` = 藍色, `POWERCUT` = 黑色。

### 2.3 過濾與排重
*   **APR 視圖**：完全過濾 `NC` (不繪製、不佔位)。使用 `DIE_PAD_NUM` 標註。
*   **PKG 視圖**：保留 `NC`。執行 `PIN_NUM` 排重（Deduplication），重複腳位合併繪製。使用 `PIN_NUM` 標註。

---

## 3. 解析演算法 (The Brain)

### 3.1 訊號匹配 (Signal Mode)
*   掃描 Verilog `input/output/inout` 宣告捕捉方向。
*   掃描 `CellType InstanceName (.PAD(NetName))`，建立 `NetName -> CellType` 映射。

### 3.2 實體匹配 (Instance Mode)
*   適用對象：`POWERCUT` 與電源。
*   規則：直接在 Verilog 內文搜尋「實體名稱 (Instance Name)」與「關鍵字清洗後名稱」一致的物件，抓取其型號。

---

## 4. PDF 視覺化演算法 (The Face)

### 4.1 智能自動縮放 (Auto-Scaling)
解決單邊 100+ Pins 擁擠問題的核心公式：
1.  **動態步進**：`Step = 邊長 / (MAX(實際 Pin 數, 封裝定義數) + 1)`。
2.  **引腳盒子縮放**：`厚度 = Step * 0.8` (上限 6pt)。
3.  **字體縮放**：`大小 = Step * 0.9` (上限 7pt, 下限 2pt)。
4.  **座標對齊**：
    *   左側：從上往下。
    *   底部：從左往右。
    *   右側：從下往上。
    *   頂部：從右往左。

### 4.2 標頭佈局 (Header Block)
*   **畫布中心 (Landscape)**：`421, 260`。
*   **標頭對齊**：
    *   左：Project (PRODUCTION NO.)。
    *   中：Package (64QFN 16 16 16 16)。
    *   右：Version。

---

## 5. 繪圖細節 Checkpoint

1.  **獨立文字物件**：為避開 PDF::API2 警告，每段 Text 需使用 `$page->text()` 獨立實體化。
2.  **動態編號**：內邊緣數字僅在編號為 `1` 或 `5 的倍數` 時繪製，且需根據邊向進行內縮對齊。
3.  **封裝框大小**：動態計算，範圍限制在 `250pt` 至 `480pt` 之間，確保不溢出。
