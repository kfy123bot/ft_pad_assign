# 待修正：字元截斷機制 Bug 清單

## 概述

分析 fpad_assign.py 的標籤截斷機制，發現 **4 個 Bug**：
- Standalone APR/PKG PDF 的 L/R/B 邊全部截斷為 `"...X"`（Bug 1、2）
- Combined PDF 的 B side 公式方向錯誤（Bug 3）
- Combined PDF 的 PKG 標籤無截斷限制（Bug 4）

---

## Bug 1 — Standalone APR PDF：L/R/B 邊標籤全截為 `"...X"`

**檔案**：`bin/fpad_assign.py`  
**位置**：第 832 行（`generate_apr_pdf` 函數）

**問題描述**：
- `limit = apr_edge[side]` 傳入的是 APR 框架的**內側**邊緣（frame edge）
- 但 L/R/B 邊的標籤是向**外側**延伸的（outside the frame）
- 導致 truncation 條件永遠成立，`available_width` 為負數

**具體計算**（以 L 邊為例）：
```
cx ≈ 420.94, cy = 255, edge = 280
bx = cx - edge/2 = 280.94
px = bx - box_len = 280.94 - 15 = 265.94
label_end = px - 4 = 261.94
limit = cx - edge/2 = 280.94  ← 框架內側邊，在標籤**右邊**

Truncation 條件：label_end - label_extent < limit
= 261.94 - label_extent < 280.94
= label_extent > -29  ← 永遠為 True！

available_width = px - 4 - limit = 261.94 - 280.94 = -29  ← 負數
max_chars = max(1, int((-29 - ellipsis_width) / char_width)) = 1
→ 所有標籤變成 "...X"（只顯示最後 1 字元）
```

**根本原因**：
- CLAUDE.md 記錄應加 `allow_overflow=True`，但實際未加
- Standalone APR 標籤應該能自由延伸至頁面邊界，不應限制在框架邊

**修正方案**：在第 832 行加 `allow_overflow=True`
```python
# 修改前
self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, 
    getattr(self, f"_{side}_pos")(cx, cy, edge), max_cnt, 'APR', 
    label_inside=False, max_label_extent=limit)

# 修改後
self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, 
    getattr(self, f"_{side}_pos")(cx, cy, edge), max_cnt, 'APR', 
    label_inside=False, max_label_extent=limit, allow_overflow=True)
```

---

## Bug 2 — Standalone PKG PDF：L/R/B 邊相同錯誤

**檔案**：`bin/fpad_assign.py`  
**位置**：第 887–889 行（`generate_pkg_pdf` 函數）

**問題描述**：
- 與 Bug 1 完全相同的問題
- `limit = pkg_edge[side]` 傳入框架內側邊緣
- L/R/B 邊所有標籤都被截為 `"...X"`
- T 邊正確（`limit = 510` = header 底線）

**修正方案**：在第 889 行加 `allow_overflow=True`
```python
# 修改前
self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, 
    getattr(self, f"_{side}_pos")(cx, cy, edge), max_cnt, 'PKG', 
    label_inside=False, max_label_extent=limit)

# 修改後
self._draw_side_boxes(c, side, data_by_side[side], cx, cy, edge, 
    getattr(self, f"_{side}_pos")(cx, cy, edge), max_cnt, 'PKG', 
    label_inside=False, max_label_extent=limit, allow_overflow=True)
```

---

## Bug 3 — B side 截斷公式方向錯誤

**檔案**：`bin/fpad_assign.py`  
**位置**：第 948–965 行（`_draw_side_boxes` 函數，B side 邏輯）

**問題描述**：

B side 標籤繪製方式：
```python
c.saveState()
c.translate(px, py - 4)
c.rotate(270)  # 順時針旋轉 90°
c.drawString(0, 0, display_name)
c.restoreState()
```

rotate(270°) 後：
- 原本的 +x 軸 → 指向頁面下方（y 遞減）
- 文字從 `y = py - 4` 開始，向**下**延伸到 `y = (py - 4) - label_extent`

但代碼用了**向上**的公式：
```python
elif side == 'B':
    label_end = py + bh + 4 + label_extent      # ← 錯：向上測量
    if label_end > limit:                        # ← 錯：limit 是 y 較小的值
        truncate = True
    ...
    available_width = (py + bh + 4) - limit     # ← 錯：79 而非 56
```

**具體計算**（Combined PDF APR B side）：
```
cy = 265, edge_apr = 200, box_len = 15
by = cy - edge_apr/2 = 165
py = by - box_len = 150

正確方向：
  標籤從 y = 146 向下延伸，底端 = 146 - label_extent
  limit = PKG 底邊 y = 90
  available = 146 - 90 = 56  ← 正確

代碼計算：
  label_end = py + bh + 4 + label_extent = 169 + label_extent
  always > limit (90) → truncation 永遠觸發
  available_width = 169 - 90 = 79  ← 高估

結果：允許 ~13 個字元，但實際只能放 ~11 個
     12–13 字元的標籤會超出 PKG 框約 1.6pt
```

**修正方案**：改用向下的公式
```python
elif side == 'B':
    # 正確：測量向下延伸的終點
    label_end = (py - 4) - label_extent
    # 正確：檢查終點是否超出下邊界（limit 是較小的 y 值）
    if label_end < limit:
        truncate = True
    # 正確：向下的可用空間
    if truncate:
        if side == 'B':
            available_width = (py - 4) - limit
```

---

## Bug 4 — Combined PDF PKG 標籤無截斷限制

**檔案**：`bin/fpad_assign.py`  
**位置**：第 584 行（`generate_combined_pdf` 函數）

**問題描述**：
```python
# 現行代碼
p_coords = self._draw_side_boxes(c, side, pkg_data_by_side[side], 
    cx, cy, edge_pkg, ..., 'PKG', label_inside=False)
    # ↑ 沒有 max_label_extent → 沒有截斷限制
```

PKG 標籤在 Combined PDF 中可能超出頁面邊界。雖然用一般 pin name (~10 字元) 不易發生，但在結構上是個缺口。

**修正方案**（選擇性，補完機制）：傳入頁面邊界
```python
# 修改前
p_coords = self._draw_side_boxes(c, side, pkg_data_by_side[side], 
    cx, cy, edge_pkg, ..., 'PKG', label_inside=False)

# 修改後
page_lim = {'L': 30, 'R': width - 30, 'B': 30, 'T': 510}
p_coords = self._draw_side_boxes(c, side, pkg_data_by_side[side], 
    cx, cy, edge_pkg, ..., 'PKG', label_inside=False, 
    max_label_extent=page_lim[side])
```

---

## 修正優先順序

| Bug | 嚴重性 | 檔案:行 | 修正方式 |
|-----|--------|---------|---------|
| Bug 1 | **高** | `832` | 加 `allow_overflow=True` |
| Bug 2 | **高** | `889` | 加 `allow_overflow=True` |
| Bug 3 | **高** | `948–965` | 改 B side 公式（向下） |
| Bug 4 | 低 | `584` | 加 page limits（可選） |

---

## 測試驗證清單

修正後應檢查：

```bash
python3 bin/fpad_assign.py -list examples/example.pin_list -o test_out -all
python3 bin/fpad_assign.py -list examples/qfn48.8028.pin_list.csv -o test_out -all
```

- ✓ Standalone APR PDF：L/R/B 邊顯示完整標籤（非 `"...X"`）
- ✓ Standalone PKG PDF：L/R/B 邊顯示完整標籤（非 `"...X"`）
- ✓ Combined APR B side：超過 ~11 字元的標籤在 PKG 框邊被截斷
- ✓ Combined APR B side：≤11 字元的標籤顯示完整（不被截斷）
- ✓ Combined PKG：標籤不超出頁面邊界

---

## 相關檔案

- 分析計畫：`.claude/plans/pkg-serialized-ritchie.md`
- 舊計畫（B side limit 修正，已部分實施）：`.claude/plans/nested-sauteeing-cocke.md`
