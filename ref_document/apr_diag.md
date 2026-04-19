提示詞：使用 Python 繪製 IC 引腳分佈圖
任務目標
請撰寫一段 Python 代碼（推薦使用 matplotlib 庫），根據提供的規格生成一張精確的積體電路 (IC) 引腳分佈圖 (Pinout Diagram)。

圖形參數規格
中央封裝 (Package):

繪製一個位於中央的正方形，線條寬度為 2。

在正方形內邊緣標註數字：左側 (1, 5, 10)、底部 (15, 20, 25)、右側 (30, 35, 40)、頂部 (45, 50)。

引腳配置 (Pin Distribution):

左側 (Left): 14 個引腳，水平向左伸出。

底部 (Bottom): 14 個引腳，垂直向下伸出。

右側 (Right): 13 個引腳，水平向右伸出。

頂部 (Top): 13 個引腳，垂直向上伸出。

引腳樣式 (Pin Styles):

標準引腳: 簡單的黑色線條。

強調引腳 (實心黑): 標籤為 POWERCUT01, POWERCUT02, POWERCUT03 的引腳需加粗並填充為實心黑色長矩形。

填充引腳 (斜線): 標籤為 PDGND2, PDVDD2 的引腳需使用斜線填充 (Hatched patterns)。

標籤數據 (Label Data):

左邊標籤: PG_RES, FBACK, FREF, LOADB, VPEN, VPRO, PDGND1, POWERCUT01, PL2_DVDD, PDGND2, PDGND2, PL2_DGND, PFD_EN, FSELO

底部標籤: D7, D6, D5, D4, NFOUT2, PDVDD2, PDVDD2, D3, D2, D1, D0, PD3, PD2, PDVDD2

右邊標籤: PAVDD, FOUT, FOUTB, RIN, RINB, PAGND, PL_AVDD1, PL2_AVDD, PL2_AGND, POWERCUT02, SFOUT, PDO, PD1

頂部標籤: FSEL1, FSEL2, SPG, PDVDD1, PL_DGND, PL_DVDD, POWERCUT03, PAGND, DOUT, DOUTB, PL_AVDD2, PL_AGND2, VREF

輸出要求
請使用 Matplotlib 生成圖表。

畫布背景為白色，不顯示坐標軸 (axis off)。

文字必須與引腳對齊：左右側標籤水平對齊，上下側標籤垂直旋轉 90 度。

確保所有文字標籤清晰，不重疊。
