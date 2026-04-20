# FPAD_ASSIGN 工具技術設計文件

## 1. 專案簡介
FPAD_ASSIGN 是一個專為 IC 設計人員開發的工具，旨在簡化 I/O 分配、驗證及視覺化過程。它支援從 Pin List 與 Verilog 檔案自動生成封裝圖 (Bonding Map)、打金線報告、以及主流 EDA 工具 (Innovus/ICC2) 的物理佈局約束檔。

## 2. 核心架構：單一腳本模式 (Standalone Architecture)
為了追求最高的移植性與易用性，本專案決定將原本散落在 `lib/` 資料夾下的模組全部整合進 Python 核心腳本中：
- **Python (`bin/fpad_assign.py`)**: 目前的開發重心。整合了 Parser, Logger, Checker, Writer 與 PDFGen 類別。
- **支援語言**: 雖然保留了 Perl 與 C++ 版本，但所有新功能與視覺優化皆以 Python 版本為準。

## 3. 數據梳理邏輯 (Data Re-indexing)
為了確保產出的 Pin List 與圖檔具有邏輯上的一致性，工具在讀取原始 Pin List 後會執行以下序號重整：

### 3.1 封裝序號 (PIN_NUM)
- **維持原樣**: 為了尊重封裝廠或現有的 Pin 定義，`PIN_NUM` 不會被重新編號。
- **特殊值**: 若原始定義中 `POWERCUT` 標註為 0，則維持為 0。

### 3.2 晶圓序號 (DIE_PAD_NUM)
- **重新標號**: 這是為了確保 Die 端的 Pad 序號是連續且正確的。
- **NC 規則**: 若引腳名稱為 `NC` (No Connect)，其 `DIE_PAD_NUM` 強制設為 **0**。
- **遞增規則**: 其餘所有非 NC 的引腳，依照在 Pin List 中出現的順序，從 **1** 開始依序遞增標號。
- **套用範圍**: 這些梳理後的序號會同步反映在 `.new` 檔案、PDF 標註以及 EDA 約束檔中。

## 4. 視覺化設計：Combined Bonding Diagram
### 4.1 比例與畫布空間
- **尺寸配置**: 外圈 (PKG)=**350**, 內圈 (APR)=**200**。
- **畫布偏移**: 中心點下移至 `cy = 240`，確保上方標籤不與檔頭重疊。

### 4.2 文字佈局與避讓
- **雙向生長**: 
  - **引腳名稱 (Pin Name)**: 標註在方框 **外側**，向外生長。
  - **引腳序號 (1, 5, 10...)**: 標註在方框 **內側**，向內排列。
- **字體一致性**: 引腳序號的字體大小調整至與引腳名稱 **完全相同**，提升閱讀舒適度。
- **底部修正**: 底部 (Bottom) 標籤採用 `drawString` 配合 270 度旋轉，確保文字向下方延伸，不重疊方塊。

### 4.3 起始點與標記 (Start Dot & Indexing)
- **序號標註**: 每隔 5 號標註一次序號 (1, 5, 10, 15...)，方便快速對位。
- **啟始黑點 (Pin 1 Dot)**: 
  - 在引腳 **1 號** 旁邊繪製一個 **半徑 6** 的實心大黑點，視覺效果極其醒目。
  - **過濾邏輯**: 在 `Combined` 視圖中，僅在 **外圈 (PKG)** 標註黑點，**內圈 (APR)** 不標註，以保持 Die 內部圖面清爽。

## 5. EDA 約束檔格式 (I/O Constraints)
### 5.1 Innovus (`.inn.const`)
遵循 `innovusUG.md` 標準格式：
- 使用 `( iopad ( side ( inst ) ) )` 結構。
- 包含 `( globals )` 與 `( locals ring_number = 1 )`。
- IO 狀態預設為 `place_status=fixed`。

### 5.2 ICC2 (`.icc2.const`)
產生 Tcl 指令格式：
- 使用 `set_io_pad_constraints` 指令。
- 自動依照邊界 (`-side`) 分組並處理換行。

## 6. 工作流程自動化
- **Makefile Sync Hook**: 提供 `make sync` 指令。
- **執行內容**: 
  1. 執行 Python 全功能測試。
  2. 測試通過後自動執行 `git add` 與 `git commit`。
  3. 自動產生帶有時間戳記的 Commit Message 並 `push` 到 GitHub。

---
*文件更新日期：2026年4月20日*
