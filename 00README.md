# 00README — 2026-05-02 + 2026-05-03 Session Changes

## 新增欄位：PKG_PIN_NAME

PKG PDF 上的 pin 名稱現在優先使用 `PKG_PIN_NAME` 欄位，若該欄位為空或 `-`，則 fallback 到 `DIE_PIN_NAME`。同時作用於 standalone PKG PDF 和 Combined PDF 的 PKG 外框。

## PKG_LOC 自動補全

當 `PKG_LOC` 欄位為 `-` 時，根據 PACKAGE header 的 L/B/R/T 數量自動補上對應 side。補全前會先做總數校驗：`sum(L,B,R,T)` 與實際有效 PKG_NUM 數量不一致時報 ERROR。

## PKG_TOP_LEFT_PIN Ring 重排

當 `PKG_TOP_LEFT_PIN` 不等於 1 時，觸發完整 ring 重排：

- `self.data` 以 PKG_TOP_LEFT_PIN 為起點重新排序（L 邊第一根）
- PKG_NUM 從 1 開始重新編號
- PKG_LOC 全部重算（L=1~L_cnt, B 接續, R 接續, T 接續）
- DIE_LOC 跟隨 PKG_LOC 模式（共用 die pad 繼承最近 PKG_LOC）— 僅 aa≠1 時觸發，aa=1 時 DIE_LOC 維持原樣
- DIE_NUM ring 重排從新的第一個 L pin 開始
- `.new` / `.new.csv` 輸出按 ring 順序排列

## APR PDF 顯示所有 Die Pad

移除 `PKG_NUM == '-'` 的 skip 條件，讓共用 PKG pin 的 die pad（有合法 DIE_NUM + DIE_LOC 但 PKG_NUM 為空）也顯示在 APR PDF 上。

## DIE_NUM 重排修正

`_reorder_and_reindex_apr_data()` 和 `bridge_data()` 不再跳過 PKG_NUM 為 `-` 的行，所有合法 DIE_NUM 正常參與 ring 重排，解決 `.new` 中的 DIE_NUM 衝突。

## PRODUCTION NO / PROJECT NO 相容

Header 解析和 prefix 提取同時接受 `PRODUCTION NO` 和 `PROJECT NO`（有無句點皆可）。Header key 正規化為 `PRODUCTION NO`，保持向後相容。Prefix 尾端多餘空白和底線自動去除。

## Innovus/ICC2 Constraint 條件輸出

無 `-v` verilog 輸入時，不再產生 `_chip.inn.const` 和 `_chip.icc2.const`（無 bridging 資料時為無效輸出）。

## `.new` / `.new.csv` 優化

- `.new.csv` 補上與 `.new` 一致的 header 資訊（PACKAGE、PKG_TOP_LEFT_PIN、PRODUCTION NO、VERSION），以 `#` 前綴表示
- 兩者皆跳過 PKG_NUM 和 DIE_NUM 同時為 `-` 的空 row

## Makefile

`make test_py` 改為 `$(wildcard examples/*.csv)` 自動發現所有 CSV 測試檔。

## 程式碼重構

- 新增 `_get_ring_side()` 共用方法，消除四處重複的 side 計算邏輯
- 新增 `_ring_shift_data()` / `_reindex_pkg_num()` / `_reassign_pkg_loc()` / `_reassign_die_loc()`
- `parse_list()` 執行順序標準化：ring_shift → reindex_pkg_num → reassign_pkg_loc → reassign_die_loc → sanity_check → reorder_and_reindex_apr_data
