---
name: fpad-assign
description: 自動化 IC I/O Assignment 與視覺化驗證工具。用於補完 Pin List 欄位、產生 APR/Package PDF 圖表及 Innovus 約束檔。
---

# FPAD_ASSIGN Skill

本技能讓 Gemini CLI 能夠操作 `fpad_assign.pl` 工具，執行 IC 引腳分配與驗證任務。

## 核心功能

1.  **欄位補完 (-c)**：讀取精簡的 9 欄位 Pin List 與 Verilog Netlist，自動抓取 IO Cell 型號與方向。
2.  **PDF 繪圖 (-apr, -pkg)**：
    *   **APR 圖**：顯示內部 Pad 佈局，跳過 NC，根據 DIE_PAD_NUM 標記。
    *   **PKG 圖**：顯示外部 Pin 佈局，包含 NC，支援腳位排重，根據 PIN_NUM 標記。
3.  **Innovus 約束生成**：自動產出符合 Innovus 語法的 `_chip.const` 檔案（使用 Verilog 實體名稱）。
4.  **Stagger 檢查**：分析 I/O 與電源/接地的分佈密度。

## 使用範例

執行全功能自動化：
`perl fpad_assign.pl -list examples/example.pin_list -v examples/example_top.v -all`

僅生成 Innovus 約束：
`perl fpad_assign.pl -list examples/example.pin_list -v examples/example_top.v -c`

## 繪圖規則

*   **紅色**：Power (Direction: P)
*   **藍色**：Ground (Direction: G)
*   **黑色**：POWERCUT (實心填充)
*   **斜線**：Hatch 填充 (PDGND2/PDVDD2)

## 座標演算法

工具具備「智能自動縮放」功能，當單邊 Pin 數超過 100 時會自動調整字體與盒子厚度，確保圖面清晰不溢出。
