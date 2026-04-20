# FPAD_ASSIGN 工具技術設計文件

## 1. 專案簡介
FPAD_ASSIGN 是一個專為 IC 設計人員開發的工具，旨在簡化 I/O 分配、驗證及視覺化過程。它支援從 Pin List 與 Verilog 檔案自動生成封裝圖 (Bonding Map)、打金線報告、以及主流 EDA 工具 (Innovus/ICC2) 的物理佈局約束檔。

## 2. 核心架構：單一腳本模式 (Standalone Architecture)
為了追求最高的移植性與易用性，本專案決定將原本散落在 `lib/` 資料夾下的模組全部整合進各語言的單一腳本中：
- **Python (`bin/fpad_assign.py`)**: 整合了 Parser, Logger, Checker, Writer 與 PDFGen 類別。
- **Perl (`bin/fpad_assign.pl`)**: 透過手寫 PDF 資料串流 (Stream) 實現無依賴繪圖。
- **C++ (`bin/fpad_assign.cpp`)**: 內建 MiniPDF 引擎，追求極致的編譯與執行速度。

這樣做的優點是設計者只需抓取單一個檔案即可在任何伺服器環境運行，無需處理環境變數或安裝複雜的相依套件。

## 3. 視覺化設計：Combined Bonding Diagram
這是本工具最核心的視覺化功能，旨在同一個 PDF 頁面中展示 Die 與 Package 的相對位置。

### 3.1 比例與空間配置
- **外圈 (Package, PKG)**: 尺寸設為 **350**。這是一個在 A4 橫向畫布上既能展示細節又不會壓迫邊界的平衡值。
- **內圈 (Die/APR)**: 尺寸設為 **200**。確保內圈與外圈之間有足夠的空間（約 75 單位）用於繪製金線。
- **畫布偏移**: 將繪圖中心下移至 `cy = 240`，以騰出頂部空間，避免引腳名稱與文件標題重疊。

### 3.2 文字避讓邏輯 (Label Anti-collision)
- **統一向外原則**: 不論是內圈還是外圈，文字標籤一律朝向「遠離方塊」的方向排列。
- **解決轉角衝突**: 內圈文字原本位於框內，經修正後移至框外的「間隙區」，徹底解決了轉角處文字堆疊的問題，同時也讓 Die 內部顯示區域更整潔。

### 3.3 金線連線 (Bonding Wires)
- **物理邊緣觸點**: 金線不再連到方塊中心，而是精確連接到 **PKG 的內緣** 與 **APR 的外緣**，模擬真實的金線焊接情況。
- **顏色區分**:
  - 紅色: Power (P)
  - 藍色: Ground (G)
  - 灰色: 一般信號 (Signal/IO)

## 4. EDA 約束檔格式 (I/O Constraints)
本工具支援產出兩大主流 EDA 工具的 IO 佈局格式：

### 4.1 Innovus (`.inn.const`)
遵循 `innovusUG.md` 的標準嵌套括號格式：
- 使用 `( iopad ( side ( inst ) ) )` 結構。
- 包含 `( globals )` 全域版本定義。
- 加入 `( locals ring_number = 1 )` 區域設定。
- 每個 IO 實例包含 `offset`, `orientation`, `place_status=fixed`, `spacing` 等預設參數。

### 4.2 ICC2 (`.icc2.const`)
產生基於 Tcl 指令的 ICC2 Design Planning 格式：
- 使用 `set_io_pad_constraints` 指令。
- 自動依照邊界 (`-side`) 進行分組。
- 使用 `\` 符號處理換行排版，方便閱讀與手動編輯。

## 5. 特殊邏輯處理
- **POWERCUT 過濾**: 在封裝層級 (PKG View/Combined Outer)，`POWERCUT` 通常不需要連接到外部引腳。因此本工具在繪製 PKG 層時會自動跳過包含 `POWERCUT` 的引腳，但在 APR 層維持顯示，以確保 Die 佈局的完整性。
- **NC 處理**: 全面跳過標記為 `NC` (No Connect) 的引腳。

## 6. 自動化測試 (Makefile)
本專案提供了一套完整的自動化流程：
- `make build`: 編譯 C++ 版本。
- `make test_py / test_pl / test_cpp`: 針對各語言版本跑過所有的 `examples`。
- `make test_all`: 一鍵執行全平台、全範例的集成測試。
- `make clean`: 清理所有暫存、報告與 PDF 產出物。

---
*文件更新日期：2026年4月20日*
