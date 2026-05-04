#!/usr/bin/env python3
"""Generate CSV Input Specification PDF for FT_PAD_ASSIGN.

English font: Helvetica Neue (Calibri unavailable on macOS; closest sans-serif)
Chinese font: STHeiti Medium (macOS built-in TTF, full CJK coverage)
Code font:    Menlo (macOS monospace)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Font Registration (TTF, not CID — avoids garbled CJK text) ──
pdfmetrics.registerFont(TTFont('HN',        '/System/Library/Fonts/HelveticaNeue.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('HN-Bold',   '/System/Library/Fonts/HelveticaNeue.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('HN-Italic', '/System/Library/Fonts/HelveticaNeue.ttc', subfontIndex=2))
pdfmetrics.registerFont(TTFont('HN-BI',     '/System/Library/Fonts/HelveticaNeue.ttc', subfontIndex=3))
pdfmetrics.registerFont(TTFont('STHeiti',   '/System/Library/Fonts/STHeiti Medium.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('Menlo',     '/System/Library/Fonts/Menlo.ttc', subfontIndex=0))

# Register font family so <b>/<i> tags work inside Paragraphs
addMapping('HN', 0, 0, 'HN')
addMapping('HN', 1, 0, 'HN-Bold')
addMapping('HN', 0, 1, 'HN-Italic')
addMapping('HN', 1, 1, 'HN-BI')

# Shortcuts
EN  = 'HN'          # English body
ENB = 'HN-Bold'     # English bold
CN  = 'STHeiti'     # Chinese (also has Latin glyphs)
CODE = 'Menlo'      # Monospace

# Helper: wrap Chinese text so it renders with STHeiti inside an HN-styled Paragraph
def cn(text):
    """Wrap text in <font> tag for Chinese font. Escapes < > to avoid HTML parse errors."""
    safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return f'<font name="{CN}">{safe}</font>'

# Colors
C_HEADER   = colors.HexColor('#2c3e50')
C_ACCENT   = colors.HexColor('#2980b9')
C_TABLE_H  = colors.HexColor('#34495e')
C_TABLE_ALT = colors.HexColor('#f8f9fa')
C_CODE_BG  = colors.HexColor('#f5f5f5')
C_GREY     = colors.HexColor('#555555')


def build_styles():
    styles = getSampleStyleSheet()
    # All body styles use HN (English); Chinese text wrapped with cn()
    styles.add(ParagraphStyle('S',       fontName=EN, fontSize=10,   leading=16, spaceAfter=4))
    styles.add(ParagraphStyle('S_Title', fontName=EN, fontSize=22,   leading=28, spaceAfter=6,
                              textColor=C_HEADER, alignment=1))
    styles.add(ParagraphStyle('S_Sub',   fontName=EN, fontSize=10,   leading=14, spaceAfter=12,
                              textColor=colors.grey, alignment=1))
    styles.add(ParagraphStyle('S_H1',    fontName=EN, fontSize=16,   leading=22, spaceBefore=18,
                              spaceAfter=8, textColor=C_HEADER))
    styles.add(ParagraphStyle('S_H2',    fontName=EN, fontSize=13,   leading=18, spaceBefore=14,
                              spaceAfter=6, textColor=C_ACCENT))
    styles.add(ParagraphStyle('S_H3',    fontName=EN, fontSize=11,   leading=15, spaceBefore=10,
                              spaceAfter=4, textColor=C_HEADER))
    styles.add(ParagraphStyle('S_Body',  fontName=EN, fontSize=9.5,  leading=15, spaceAfter=4))
    styles.add(ParagraphStyle('S_Code',  fontName=CODE, fontSize=8,  leading=11, spaceAfter=4,
                              leftIndent=12, backColor=C_CODE_BG, borderPadding=4))
    styles.add(ParagraphStyle('S_Note',  fontName=EN, fontSize=9,    leading=13, spaceAfter=4,
                              leftIndent=12, textColor=C_GREY))
    styles.add(ParagraphStyle('S_Bul',   fontName=EN, fontSize=9.5,  leading=14, spaceAfter=2,
                              leftIndent=20, bulletIndent=10))
    styles.add(ParagraphStyle('S_TH',    fontName=EN, fontSize=8.5,  leading=11,
                              textColor=colors.white, alignment=1))
    styles.add(ParagraphStyle('S_TD',    fontName=EN, fontSize=8.5,  leading=12))
    return styles


def P(text, style):
    return Paragraph(text, style)


def make_table(headers, rows, col_widths=None):
    s = build_styles()
    data = [[P(h, s['S_TH']) for h in headers]]
    for row in rows:
        data.append([P(str(c), s['S_TD']) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), C_TABLE_H),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), C_TABLE_ALT))
    t.setStyle(TableStyle(cmds))
    return t


def build_doc():
    s = build_styles()
    story = []

    # ── Title ──
    story.append(Spacer(1, 30))
    story.append(P('FT_PAD_ASSIGN', s['S_Title']))
    story.append(P(cn('CSV 輸入規格說明書'), s['S_Title']))
    story.append(Spacer(1, 8))
    story.append(P('bin/ft_pad_assign.py  -list xx.csv ' + cn('輸入檔案格式完整規範'), s['S_Sub']))
    story.append(P(cn('基於源碼分析，涵蓋所有欄位（必要/選填）、特殊列類型、欄位別名、自動處理規則'), s['S_Sub']))
    story.append(Spacer(1, 6))
    story.append(P(cn('版本') + ': v3.mimo  |  ' + cn('文件日期') + ': 2026-05-03', s['S_Sub']))
    story.append(Spacer(1, 20))

    # ── TOC ──
    story.append(P(cn('目錄'), s['S_H1']))
    for item in [
        '1. ' + cn('檔案整體結構'),
        '2. ' + cn('Header 元資料區'),
        '3. ' + cn('CSV 資料表頭行'),
        '4. 11 ' + cn('個資料欄位詳解'),
        '5. ' + cn('特殊列類型'),
        '6. ' + cn('自動處理流程'),
        '7. ' + cn('PDF 正確生成的欄位需求'),
        '8. ' + cn('完整範例'),
        '9. ' + cn('常見錯誤與注意事項'),
        '10. ' + cn('附錄：欄位別名對照表'),
        '11. ' + cn('附錄：內部欄位名稱'),
        '12. ' + cn('附錄：代碼位置參考'),
    ]:
        story.append(P(item, s['S_Body']))
    story.append(PageBreak())

    # ══════════════════════════════════════════════
    # 1
    # ══════════════════════════════════════════════
    story.append(P('1. ' + cn('檔案整體結構'), s['S_H1']))
    story.append(P(cn('CSV 檔案由四個區塊組成，順序固定：'), s['S_Body']))
    story.append(Spacer(1, 4))

    story.append(make_table(
        [cn('區塊'), cn('內容'), cn('必要性')],
        [
            [cn('Header 元資料區'), cn('key : value 格式的專案資訊'), cn('必要')],
            [cn('空白行分隔'), cn('分隔 Header 與資料表頭'), cn('建議')],
            [cn('CSV 資料表頭行'), cn('欄位名稱，逗號分隔'), cn('必要')],
            [cn('資料列'), cn('每列一個 pin 的完整資訊'), cn('必要')],
            [cn('Inner_bond 模板區'), cn('檔案尾部的佔位/註解列'), cn('選填')],
        ],
        col_widths=[120, 240, 60],
    ))
    story.append(Spacer(1, 6))
    story.append(P(cn('檔案副檔名：'), s['S_H3']))
    story.append(P(cn('- .csv — 以逗號分隔，使用 csv.DictReader 解析'), s['S_Bul']))
    story.append(P(cn('- .pin_list — 以 Tab 分隔，逐行解析（規則相同，僅分隔符不同）'), s['S_Bul']))

    # ══════════════════════════════════════════════
    # 2
    # ══════════════════════════════════════════════
    story.append(P('2. ' + cn('Header 元資料區'), s['S_H1']))
    story.append(P(cn('位於檔案最上方，每行格式為 KEY : VALUE。CSV 格式中 VALUE 後方可帶多餘逗號（會被自動去除）。'), s['S_Body']))

    story.append(P('2.1 ' + cn('必要欄位'), s['S_H2']))

    story.append(P('PRODUCTION NO / PROJECT NO', s['S_H3']))
    story.append(P('PRODUCTION NO  : PRJ8028_QFN48_TEST', s['S_Code']))
    story.append(make_table(
        [cn('項目'), cn('說明')],
        [
            [cn('用途'), cn('專案代號，用於產生所有輸出檔名（.log、.new、.pdf 等）')],
            [cn('別名'), 'PRODUCTION NO, PRODUCTION NO., PROJECT NO, PROJECT NO. ' + cn('四種寫法等價')],
            [cn('正規化'), cn('代碼自動將 PROJECT NO 統一為 PRODUCTION NO')],
            [cn('檔名處理'), cn('非字母數字字元（底線和連字號除外）轉為 _，尾端空白/底線去除')],
            [cn('空值處理'), cn('若缺失，檔名 fallback 為 fpad_out')],
        ],
        col_widths=[80, 340],
    ))
    story.append(Spacer(1, 8))

    story.append(P('PACKAGE', s['S_H3']))
    story.append(P('PACKAGE : 48QFN 12 12 12 12', s['S_Code']))
    story.append(make_table(
        [cn('項目'), cn('說明')],
        [
            [cn('用途'), cn('定義封裝類型及四邊 pin 數量')],
            [cn('格式'), '&lt;' + cn('封裝類型') + '&gt; &lt;L' + cn('數量') + '&gt; &lt;B' + cn('數量') + '&gt; &lt;R' + cn('數量') + '&gt; &lt;T' + cn('數量') + '&gt;'],
            [cn('要求'), cn('至少 5 個以空白分隔的欄位，後四個必須為正整數')],
            [cn('驗證'), 'L + B + R + T ' + cn('必須等於資料列中有效 PKG_NUM 的唯一數量')],
        ],
        col_widths=[80, 340],
    ))
    story.append(Spacer(1, 4))
    story.append(P(cn('常見封裝範例：'), s['S_Body']))
    story.append(make_table(
        ['Value', cn('封裝'), 'L', 'B', 'R', 'T', cn('總計')],
        [
            ['48QFN 12 12 12 12', 'QFN48', '12', '12', '12', '12', '48'],
            ['56QFN 14 14 14 14', 'QFN56', '14', '14', '14', '14', '56'],
            ['40QFN 10 10 10 10', 'QFN40', '10', '10', '10', '10', '40'],
        ],
        col_widths=[120, 60, 40, 40, 40, 40, 40],
    ))

    story.append(P('2.2 ' + cn('選填欄位'), s['S_H2']))

    story.append(P('PKG_TOP_LEFT_PIN', s['S_H3']))
    story.append(P('PKG_TOP_LEFT_PIN : 15', s['S_Code']))
    story.append(make_table(
        [cn('項目'), cn('說明')],
        [
            [cn('用途'), cn('指定 L 邊第一根 pin 的起始編號')],
            [cn('預設值'), '1（L ' + cn('邊從 pin 1 開始') + ')'],
            [cn('觸發條件'), cn('若值不為 1，會觸發 ring shift 重排')],
            [cn('重排後'), 'PKG_NUM ' + cn('從 1 重新編號，此值被重置為 1')],
        ],
        col_widths=[80, 340],
    ))
    story.append(Spacer(1, 6))

    story.append(P('VERSION', s['S_H3']))
    story.append(P('VERSION : V1.0_20240418', s['S_Code']))
    story.append(P(cn('版本資訊，顯示於 PDF header。無格式限制，任意字串。'), s['S_Body']))

    story.append(P('2.3 ' + cn('Header 書寫注意事項'), s['S_H2']))
    for n in [
        cn('Key 不區分大小寫：production no、PRODUCTION NO、Production No 均可'),
        cn('冒號前可有逗號：CSV 格式中常見 PRODUCTION NO  : value,,,,,,,,,,,，代碼會自動處理'),
        cn('Header 行識別依據：行內包含 : 且不以數字、( 或 D 開頭'),
        cn('行順序不固定：四個 Header 欄位可任意排列'),
        cn('可額外增加欄位：非上述四個的 Header 行會被忽略（不報錯）'),
    ]:
        story.append(P('- ' + n, s['S_Bul']))

    # ══════════════════════════════════════════════
    # 3
    # ══════════════════════════════════════════════
    story.append(P('3. ' + cn('CSV 資料表頭行'), s['S_H1']))
    story.append(P('3.1 ' + cn('識別方式'), s['S_H2']))
    story.append(P(cn('代碼透過掃描所有行，找到包含 PKG_NUM（或其別名）的行作為表頭行。表頭行之前的所有行視為 Header 元資料。'), s['S_Body']))

    story.append(P('3.2 ' + cn('標準寫法'), s['S_H2']))
    story.append(P('PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO', s['S_Code']))

    story.append(P('3.3 ' + cn('欄位順序'), s['S_H2']))
    story.append(P(cn('欄位順序不固定。代碼使用 csv.DictReader 按名稱匹配，而非按位置。'), s['S_Body']))

    story.append(P('3.4 ' + cn('多餘欄位'), s['S_H2']))
    story.append(P(cn('表頭行可包含額外欄位（如末尾的多餘逗號產生的空欄位），代碼會忽略不在 FIELD_ALIASES 中的欄位。'), s['S_Body']))

    # ══════════════════════════════════════════════
    # 4
    # ══════════════════════════════════════════════
    story.append(P('4. 11 ' + cn('個資料欄位詳解'), s['S_H1']))

    # 4.1
    story.append(P('4.1 PKG_NUM — ' + cn('封裝腳位編號（必要）'), s['S_H2']))
    story.append(make_table(
        [cn('值類型'), cn('範例'), cn('行為')],
        [
            [cn('正整數'), '1, 2, 48', cn('正常封裝腳位，按數值順序分配到 L→B→R→T 四邊')],
            ['0', '0', cn('共用 die pad（無獨立封裝腳位）。PKG PDF 不顯示；若 DIRECTION=G 則繪製接地符號')],
            ['D1.xx', 'D1.94', cn('Inner Bond 動態參考（無括號）。方向：xx → 當前列的 DIE_NUM')],
            ['(D1.xx)', '(D1.35)', cn('Inner Bond 動態參考（有括號）。方向：當列 DIE_NUM → xx')],
            ['Inner_bond', 'Inner_bond', cn('註解/模板列，不參與 pin 計數和 PDF 繪製')],
            [cn('- 或空'), '-', cn('無效/佔位列，PKG PDF 不顯示')],
        ],
        col_widths=[70, 60, 290],
    ))
    story.append(P(cn('重要：正整數的 PKG_NUM 會在 PKG_TOP_LEFT_PIN != 1 時被重新編號（從 1 開始）。D1.xx 中的 xx 會在 DIE_NUM 重編後動態更新。'), s['S_Note']))

    # 4.2
    story.append(P('4.2 DIE_NUM — ' + cn('晶粒墊片編號（必要）'), s['S_H2']))
    story.append(make_table(
        [cn('值類型'), cn('範例'), cn('行為')],
        [
            [cn('正整數'), '1, 103, 72', cn('正常 die pad。會被重新編號（從 L 邊第一根非 NC pin 開始為 1）')],
            ['0', '0', cn('無 die pad（NC、DOWNBOND、或共用 pad），APR PDF 不顯示')],
            [cn('- 或空'), '-', cn('視為無效列，不參與 DIE_NUM 重編')],
        ],
        col_widths=[70, 80, 270],
    ))
    story.append(P(cn('重編規則：從資料中第一根 L 邊非 NC、非 0 的 pin 開始編號為 1。相同原始 DIE_NUM 的列會被賦予相同的新編號（去重）。NC 和 DIE_NUM=0 的列統一設為 0。'), s['S_Note']))

    # 4.3
    story.append(P('4.3 DIE_PIN_NAME — ' + cn('晶粒側 pin 名稱（必要）'), s['S_H2']))
    story.append(P(cn('最關鍵的欄位，決定 pin 的類型和 PDF 顯示行為。'), s['S_Body']))
    story.append(make_table(
        [cn('特殊值'), 'PKG PDF', 'APR PDF', 'Combined PDF', cn('說明')],
        [
            ['NC', cn('黑色實心方塊'), cn('跳過'), cn('跳過'), 'No Connect'],
            ['DOWNBOND', cn('藍色方塊'), cn('跳過'), cn('跳過'), cn('接地/bonding 端點')],
            ['POWERCUT', cn('跳過'), cn('黑色實心方塊'), cn('跳過'), 'Power cut'],
            [cn('其他值'), cn('正常顯示'), cn('正常顯示'), cn('正常顯示'), cn('一般 pin')],
        ],
        col_widths=[70, 80, 70, 80, 120],
    ))
    story.append(Spacer(1, 4))
    story.append(P(cn('名稱格式與 % 分隔規則：'), s['S_H3']))
    story.append(make_table(
        [cn('格式'), cn('範例'), 'PKG ' + cn('顯示'), 'APR ' + cn('顯示')],
        [
            [cn('一般名稱'), 'MIPI_CSI_RX_L0P', 'MIPI_CSI_RX_L0P', 'MIPI_CSI_RX_L0P'],
            [cn('帶 % 分隔'), 'VDD11%C%U_AIP_TOP/U_VDD11_APR5', cn('VDD11（第一段）'), cn('U_VDD11_APR5（最後段）')],
            [cn('帶 % 多段'), 'VDD33_IOB%IO%U_AIP_TOP/U_VDD33_IOB0', 'VDD33_IOB', 'U_VDD33_IOB0'],
        ],
        col_widths=[70, 170, 90, 90],
    ))
    story.append(P(cn('PKG PDF 取 % 之前第一段；APR PDF 取 % 之後最後一段。若分割後為空，則使用完整名稱。'), s['S_Note']))

    # 4.4
    story.append(P('4.4 PKG_LOC — ' + cn('封裝側邊位置（必要，可自動計算）'), s['S_H2']))
    story.append(make_table(
        [cn('值'), cn('說明')],
        [['L', cn('左邊（Left）')], ['B', cn('下邊（Bottom）')], ['R', cn('右邊（Right）')], ['T', cn('上邊（Top）')], [cn('- 或空'), cn('會被自動補上')]],
        col_widths=[80, 340],
    ))
    story.append(P(cn('PKG_LOC 由 _reassign_pkg_loc() 根據 PKG_NUM 的 ring 順序和 PACKAGE header 自動計算。手動填寫的值會被覆蓋。'), s['S_Note']))
    story.append(P(cn('分配邏輯（以 48QFN 12 12 12 12 為例）：PKG_NUM 1~12→L，13~24→B，25~36→R，37~48→T。'), s['S_Note']))

    # 4.5
    story.append(P('4.5 DIE_LOC — ' + cn('晶粒側邊位置（必要，可自動計算）'), s['S_H2']))
    story.append(make_table(
        [cn('值'), cn('說明')],
        [['L / B / R / T', cn('晶粒四邊')], [cn('- 或空'), cn('在特定條件下會被自動補上')]],
        col_widths=[80, 340],
    ))
    story.append(P(cn('自動補全條件：僅在 PKG_TOP_LEFT_PIN != 1（ring 被 shift）時，_reassign_die_loc() 才會將 DIE_LOC 設為與 PKG_LOC 相同。若 PKG_TOP_LEFT_PIN = 1，則維持手動填寫的原始值。'), s['S_Note']))

    # 4.6
    story.append(P('4.6 PKG_PIN_NAME — ' + cn('封裝側 pin 名稱（選填）'), s['S_H2']))
    story.append(P(cn('有值時 PKG PDF 顯示此名稱；空或 - 時 fallback 到 DIE_PIN_NAME。僅影響 PKG PDF（standalone + combined 外框）的 pin 標籤文字。'), s['S_Body']))

    # 4.7
    story.append(P('4.7 IO_CELL_NAME — IO Cell ' + cn('名稱（選填）'), s['S_H2']))
    story.append(P(cn('有值時直接使用。空、- 或 NOT_FOUND 時，若有提供 Verilog（-v 參數），會自動從 Verilog 中查找填入。'), s['S_Body']))

    # 4.8
    story.append(P('4.8 DIRECTION — ' + cn('腳位方向（選填）'), s['S_H2']))
    story.append(make_table(
        [cn('值'), cn('行為'), 'PDF ' + cn('顏色')],
        [
            ['P', cn('電源（Power）'), cn('紅色')],
            ['G', cn('接地（Ground）'), cn('藍色')],
            [cn('- 或空'), cn('一般訊號'), cn('灰色（wire）/ 空心矩形（pin）')],
        ],
        col_widths=[80, 180, 160],
    ))
    story.append(P(cn('若有提供 Verilog，方向為 - 的一般訊號 pin 會嘗試從 Verilog 的 port direction 自動填入。'), s['S_Note']))

    # 4.9-4.11
    for num, name, desc in [
        ('4.9', 'LOAD', cn('電容值（選填）')),
        ('4.10', 'SLEW', cn('轉換率（選填）')),
        ('4.11', 'SSO', cn('SSO 比值（選填）')),
    ]:
        story.append(P(f'{num} {name} — {desc}', s['S_H2']))
        story.append(P(cn('Stagger check 報告使用，不影響 PDF 顯示。任意字串或數值。'), s['S_Body']))

    # ══════════════════════════════════════════════
    # 5
    # ══════════════════════════════════════════════
    story.append(P('5. ' + cn('特殊列類型'), s['S_H1']))

    # 5.1
    story.append(P('5.1 ' + cn('共用 Die Pad 列（PKG_NUM = 0）'), s['S_H2']))
    story.append(P(cn('多個封裝 pin 對應同一個 die pad，或無獨立封裝 pin 的 die pad：'), s['S_Body']))
    story.append(P('0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX<br/>0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX<br/>0,,3,VSS33_ESD_RX,-,-,L,G,-,-,RX', s['S_Code']))
    story.append(P(cn('- 同一個 DIE_NUM 可出現 N 次'), s['S_Bul']))
    story.append(P(cn('- PKG_NUM 必須為 0'), s['S_Bul']))
    story.append(P(cn('- 接地線數量 = 出現次數（上例 = 3 條接地線）'), s['S_Bul']))
    story.append(P(cn('- APR PDF 中該 die pad 只顯示一次（去重）'), s['S_Bul']))

    # 5.2
    story.append(P('5.2 Inner Bond ' + cn('動態參考列'), s['S_H2']))
    story.append(P(cn('用於連接不同邊的 die pad（跨邊連接）：'), s['S_Body']))
    story.append(P('D1.94,,33,VDD11%C%...,-,-,B,P,-,-,-  ' + cn('（無括號）') + '<br/>(D1.35),,84,VDD33_IOT%...,-,-,T,P,-,-,-  ' + cn('（有括號）'), s['S_Code']))
    story.append(make_table(
        [cn('格式'), 'PKG_NUM', 'DIE_NUM', cn('連接方向')],
        [
            ['D1.xx', 'D1.77', '42', 'DIE_NUM(77) → DIE_NUM(42)'],
            ['(D1.xx)', '(D1.77)', '42', 'DIE_NUM(42) → DIE_NUM(77)'],
        ],
        col_widths=[70, 80, 80, 190],
    ))
    story.append(P(cn('對稱性判定：'), s['S_H3']))
    story.append(make_table(
        [cn('結果'), cn('線條樣式'), 'Log ' + cn('級別')],
        [
            ['A→B ' + cn('且') + ' B→A ' + cn('同時存在'), cn('實線（solid）'), 'INFO'],
            [cn('只有') + ' A→B ' + cn('或只有') + ' B→A', cn('虛線（dashed）'), 'ERROR'],
        ],
        col_widths=[160, 120, 140],
    ))
    story.append(P(cn('多重線偏移：同一 (source, dest) 出現 N 次時，繪製 N 條平行線，偏移量 = (i - (N-1)/2) * 2。'), s['S_Note']))

    # 5.3
    story.append(P('5.3 DOWNBOND ' + cn('列'), s['S_H2']))
    story.append(P('17,,0,DOWNBOND,-,B,-,G,-,-,RX', s['S_Code']))
    story.append(make_table(
        [cn('欄位'), cn('值'), cn('說明')],
        [
            ['PKG_NUM', cn('正整數'), cn('有封裝腳位')],
            ['DIE_NUM', '0', cn('無 die pad')],
            ['DIE_PIN_NAME', 'DOWNBOND', cn('特殊名稱')],
            ['DIRECTION', 'G', cn('接地')],
        ],
        col_widths=[100, 80, 240],
    ))
    story.append(P(cn('PKG PDF：藍色方塊。APR PDF：跳過。Combined PDF：跳過，繪製接地符號（倒 T 形）。'), s['S_Note']))

    # 5.4
    story.append(P('5.4 NC ' + cn('列'), s['S_H2']))
    story.append(P('35,,0,NC,-,R,R,-,-,-,TX', s['S_Code']))
    story.append(P(cn('PKG PDF：黑色實心方塊。APR PDF：跳過。Combined PDF：跳過。'), s['S_Note']))

    # 5.5
    story.append(P('5.5 POWERCUT ' + cn('列'), s['S_H2']))
    story.append(P('0,,84,POWERCUT,-,-,T,-,-,-,-', s['S_Code']))
    story.append(P(cn('PKG PDF：跳過。APR PDF：黑色實心方塊。Combined PDF：跳過。'), s['S_Note']))

    # 5.6
    story.append(P('5.6 Inner_bond ' + cn('模板列（檔案尾部）'), s['S_H2']))
    story.append(P('Inner_bond,,1,I0 (X.Y),I1 (X.Y),,,,,,,,', s['S_Code']))
    story.append(P(cn('- 不參與 pin 計數和 PDF 繪製'), s['S_Bul']))
    story.append(P(cn('- 原樣保留到 .new 輸出'), s['S_Bul']))
    story.append(P(cn('- 用於記錄設計意圖（佔位符）'), s['S_Bul']))

    # 5.7
    story.append(P('5.7 ' + cn('空列 / 佔位列'), s['S_H2']))
    story.append(P('0,,0,-,-,-,B,-,-,-,-', s['S_Code']))
    story.append(P(cn('PKG_NUM = 0，DIE_NUM = 0，DIE_PIN_NAME = -。無實際意義，可用於分隔或佔位。在 .new 輸出中會被跳過。'), s['S_Body']))

    # 5.8
    story.append(P('5.8 ' + cn('無 PKG_NUM 的共享 Die Pad 列'), s['S_H2']))
    story.append(P(',,21,VBAT_PIO_0,-,,B,,,,', s['S_Code']))
    story.append(P(cn('PKG_NUM 為空，DIE_NUM 有值。表示此 die pad 無獨立封裝 pin。APR PDF 會顯示，PKG PDF 不顯示。'), s['S_Body']))

    # ══════════════════════════════════════════════
    # 6
    # ══════════════════════════════════════════════
    story.append(P('6. ' + cn('自動處理流程'), s['S_H1']))
    story.append(P(cn('解析完成後，代碼按以下順序自動處理 self.data：'), s['S_Body']))
    story.append(make_table(
        [cn('步驟'), cn('函數'), cn('條件'), cn('作用')],
        [
            ['1', '_ring_shift_data()', 'PKG_TOP_LEFT_PIN != 1', cn('重排 self.data，使指定 pin 成為第一列')],
            ['2', '_reindex_pkg_num()', 'PKG_TOP_LEFT_PIN != 1', 'PKG_NUM ' + cn('從 1 重新編號，PKG_TOP_LEFT_PIN 重置為 1')],
            ['3', '_reassign_pkg_loc()', cn('始終執行'), cn('根據 PKG_NUM ring 順序重新計算四邊 PKG_LOC')],
            ['4', '_reassign_die_loc()', cn('僅 ring 被 shift 時'), 'DIE_LOC ' + cn('跟隨 PKG_LOC（共用 pad 跟隨最近 side）')],
            ['5', '_sanity_check_list()', cn('始終執行'), cn('驗證四邊 pin 數 = PACKAGE header 定義')],
            ['6', '_reorder_and_reindex_apr_data()', cn('始終執行'), 'DIE_NUM ' + cn('重編 + 更新 D1.xx 參照')],
        ],
        col_widths=[35, 150, 110, 125],
    ))

    story.append(P('6.1 Ring Shift ' + cn('詳解'), s['S_H2']))
    story.append(P(cn('當 PKG_TOP_LEFT_PIN = 15 且 PACKAGE = 56QFN 14 14 14 14 時：'), s['S_Body']))
    story.append(P(cn('- 原始順序：pin 1, 2, 3, ..., 56'), s['S_Bul']))
    story.append(P(cn('- Ring 位置計算：ring_pos = (pin_num - offset - 1) % total，其中 offset = 15 - 1 = 14'), s['S_Bul']))
    story.append(P(cn('- 重排後：pin 15 成為第一列（L 邊起點），pin 14 成為最後一列'), s['S_Bul']))

    story.append(P('6.2 PKG_NUM ' + cn('重編'), s['S_H2']))
    story.append(P(cn('Ring shift 後，PKG_NUM 從 1 重新編號。正整數 PKG_NUM 依序改為 1, 2, 3, ...。0、-、D1.xx、Inner_bond 不參與重編。'), s['S_Body']))

    story.append(P('6.3 PKG_LOC ' + cn('重算'), s['S_H2']))
    story.append(P(cn('根據 PKG_NUM 和 PACKAGE header 的 L/B/R/T 數量，按 ring 順序分配。PKG_NUM 1~L數量→L，L+1~L+B數量→B，以此類推。'), s['S_Body']))

    story.append(P('6.4 Sanity Check', s['S_H2']))
    story.append(P(cn('驗證項目：(1) 每邊唯一 PKG_NUM 數量 = PACKAGE header 對應邊數量；(2) 四邊總計 = L+B+R+T；(3) DOWNBOND 的 PKG_NUM 計入對應邊；(4) 0、D1.xx、Inner_bond 不計入。'), s['S_Body']))

    # ══════════════════════════════════════════════
    # 7 — PDF 正確生成的欄位需求
    # ══════════════════════════════════════════════
    story.append(P('7. ' + cn('PDF 正確生成的欄位需求'), s['S_H1']))
    story.append(P(cn('本節說明要正確產出 APR、PKG、Combined 三份 PDF，CSV 中每個欄位的必要性。'), s['S_Body']))

    # 7.1 必填欄位
    story.append(P('7.1 ' + cn('必填欄位（缺少任一會導致 PDF 不正確）'), s['S_H2']))
    story.append(make_table(
        [cn('欄位'), 'PKG', 'APR', 'Combined', cn('缺少時的影響')],
        [
            [cn('PKG_NUM'), cn('必填'), cn('過濾用'), cn('必填'), cn('無法分配 pin 到四邊，sanity check 失敗')],
            [cn('DIE_NUM'), '—', cn('必填'), cn('必填'), cn('APR 無法顯示 pin，wire 無端點')],
            [cn('DIE_PIN_NAME'), cn('必填'), cn('必填'), cn('必填'), cn('無法判斷 pin 類型（NC/DOWNBOND/POWERCUT），無顯示名稱')],
            [cn('DIE_LOC'), '—', cn('必填*'), cn('必填*'), cn('APR pin 不知道放哪邊，全部消失或位置錯誤')],
            [cn('DIRECTION'), cn('建議'), cn('建議'), cn('建議'), cn('顏色全部變灰色/空心，無法區分 Power/Ground')],
        ],
        col_widths=[80, 50, 55, 70, 165],
    ))
    story.append(P(cn('* DIE_LOC 在 PKG_TOP_LEFT_PIN = 1 時不會自動補全，必須手動填寫。僅在 PKG_TOP_LEFT_PIN != 1 時才由 _reassign_die_loc() 自動計算。'), s['S_Note']))

    # 7.2 自動計算欄位
    story.append(P('7.2 ' + cn('自動計算欄位（不必手動填）'), s['S_H2']))
    story.append(make_table(
        [cn('欄位'), cn('說明')],
        [
            [cn('PKG_LOC'), cn('由 _reassign_pkg_loc() 根據 PKG_NUM 和 PACKAGE header 自動計算，手動值會被覆蓋')],
        ],
        col_widths=[80, 340],
    ))

    # 7.3 選填欄位
    story.append(P('7.3 ' + cn('選填欄位（不影響 PDF 正確性）'), s['S_H2']))
    story.append(make_table(
        [cn('欄位'), cn('影響')],
        [
            [cn('PKG_PIN_NAME'), cn('僅影響 PKG PDF 標籤文字，空時 fallback 到 DIE_PIN_NAME')],
            [cn('IO_CELL_NAME'), cn('不影響 PDF，僅用於 .new 輸出和 Verilog bridging')],
            ['LOAD', cn('不影響 PDF，僅用於 stagger report')],
            ['SLEW', cn('不影響 PDF，僅用於 stagger report')],
            ['SSO', cn('不影響 PDF，僅用於 stagger report')],
        ],
        col_widths=[100, 320],
    ))

    # 7.4 最小可行 CSV
    story.append(P('7.4 ' + cn('最小可行 CSV（5 個欄位即可產出三份 PDF）'), s['S_H2']))
    story.append(P(
        'PRODUCTION NO  : TEST<br/>'
        'PACKAGE : 4QFN 1 1 1 1<br/><br/>'
        'PKG_NUM,DIE_NUM,DIE_PIN_NAME,DIE_LOC,DIRECTION<br/>'
        '1,1,CLK,L,-<br/>'
        '2,2,DATA,B,-<br/>'
        '3,3,VDD,R,P<br/>'
        '4,4,GND,T,G',
        s['S_Code'],
    ))
    story.append(P(cn('5 個欄位：PKG_NUM、DIE_NUM、DIE_PIN_NAME、DIE_LOC、DIRECTION 即可產出正確的三份 PDF。'), s['S_Note']))

    # 7.5 特殊列的欄位需求
    story.append(P('7.5 ' + cn('特殊列的欄位需求'), s['S_H2']))
    story.append(make_table(
        [cn('列類型'), cn('必填欄位'), cn('說明')],
        [
            ['NC', 'PKG_NUM' + cn('（正整數）') + ', DIE_NUM' + cn('（=0）') + ', DIE_PIN_NAME' + cn('（=NC）'),
             cn('PKG 顯示黑塊，APR 跳過')],
            ['DOWNBOND', 'PKG_NUM' + cn('（正整數）') + ', DIE_NUM' + cn('（=0）') + ', DIE_PIN_NAME' + cn('（=DOWNBOND）') + ', DIRECTION' + cn('（=G）'),
             cn('PKG 顯示藍塊，Combined 畫接地符號')],
            [cn('共用 pad'), 'PKG_NUM' + cn('（=0）') + ', DIE_NUM' + cn('（正整數）') + ', DIE_PIN_NAME' + ', DIRECTION',
             cn('多列共享同一 DIE_NUM')],
            ['Inner Bond', 'PKG_NUM' + cn('（=D1.xx）') + ', DIE_NUM' + cn('（正整數）') + ', DIE_PIN_NAME',
             cn('Combined 畫紅線連接')],
        ],
        col_widths=[70, 200, 150],
    ))

    # 7.6 各 PDF 欄位使用對照
    story.append(P('7.6 ' + cn('各 PDF 欄位使用對照總表'), s['S_H2']))
    story.append(make_table(
        [cn('欄位'), 'PKG PDF', 'APR PDF', 'Combined PDF', cn('.new 輸出')],
        [
            [cn('PKG_NUM'), cn('排序+座標鍵'), cn('過濾 Inner_bond'), cn('排序+座標鍵+wire 起點'), cn('輸出')],
            [cn('PKG_PIN_NAME'), cn('PKG 標籤文字'), '—', cn('PKG 標籤文字'), cn('輸出')],
            [cn('DIE_NUM'), '—', cn('去重+座標鍵'), cn('去重+座標鍵+wire 終點'), cn('輸出（會被重編）')],
            [cn('DIE_PIN_NAME'), cn('判斷 NC/POWERCUT + 標籤'), cn('判斷 NC/DOWNBOND + 標籤'), cn('判斷類型 + 標籤'), cn('輸出')],
            [cn('IO_CELL_NAME'), '—', '—', '—', cn('輸出（可自動填入）')],
            [cn('PKG_LOC'), cn('分配到四邊'), '—', cn('分配到四邊'), cn('輸出（自動計算）')],
            [cn('DIE_LOC'), '—', cn('分配到四邊'), cn('分配到四邊'), cn('輸出')],
            [cn('DIRECTION'), cn('紅/藍/空心方塊'), cn('紅/藍/空心方塊'), cn('wire 顏色 + pin 顏色'), cn('輸出')],
            ['LOAD', '—', '—', '—', cn('輸出')],
            ['SLEW', '—', '—', '—', cn('輸出')],
            ['SSO', '—', '—', '—', cn('輸出')],
        ],
        col_widths=[80, 100, 100, 100, 100],
    ))

    # ══════════════════════════════════════════════
    # 8 — 完整範例
    # ══════════════════════════════════════════════
    story.append(P('8. ' + cn('完整範例'), s['S_H1']))

    story.append(P('8.1 ' + cn('最小範例（QFN40，11 欄位）'), s['S_H2']))
    story.append(P(
        'PRODUCTION NO  : PRJ8803_QFN40_TEST<br/>'
        'PKG_TOP_LEFT_PIN : 1<br/>'
        'PACKAGE : 40QFN 10 10 10 10<br/>'
        'VERSION : V1.0_20260428<br/><br/>'
        'PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO<br/>'
        '1,VDD33_ANA,1,,-,L,L,P,,,<br/>'
        '2,MIPI_CSI_RX_L0P,2,MIPI_CSI_RX_L0P,-,L,L,,,<br/>'
        '...<br/>'
        '40,PIO_21,72,PIO_31,-,T,T,,,<br/><br/>'
        'Inner_bond,,1,I0 (X.Y),I1 (X.Y),,,,,,',
        s['S_Code'],
    ))

    story.append(P('8.2 ' + cn('含特殊列的完整範例（QFN48）'), s['S_H2']))
    story.append(P(
        'PRODUCTION NO  : PRJ8028_QFN48_TEST<br/>'
        'PKG_TOP_LEFT_PIN : 1<br/>'
        'PACKAGE : 48QFN 12 12 12 12<br/>'
        'VERSION : V1.0_20240418<br/><br/>'
        'PKG_NUM,PKG_PIN_NAME,DIE_NUM,DIE_PIN_NAME,IO_CELL_NAME,PKG_LOC,DIE_LOC,DIRECTION,LOAD,SLEW,SSO<br/>'
        '1,,103,SCL,-,L,T,-,-,-,-<br/>'
        '0,,107,GND%C%U_AIP_TOP/U_GND_APR8,-,-,T,G,-,-,-<br/>'
        '(D1.94),,1,VDD11%C%...,-,-,L,P,-,-,-<br/>'
        '35,,0,NC,-,R,R,-,-,-,TX<br/>'
        '17,,0,DOWNBOND,-,B,-,G,-,-,RX<br/>'
        'D1.94,,33,VDD11%C%...,-,-,B,P,-,-,-',
        s['S_Code'],
    ))

    # ══════════════════════════════════════════════
    # 9
    # ══════════════════════════════════════════════
    story.append(P('9. ' + cn('常見錯誤與注意事項'), s['S_H1']))

    story.append(P('9.1 ERROR ' + cn('級別'), s['S_H2']))
    story.append(make_table(
        [cn('錯誤訊息'), cn('原因'), cn('解決方式')],
        [
            ['Side X check FAILED', cn('某邊實際 pin 數 ≠ PACKAGE header'), cn('檢查 PKG_NUM 是否正確、遺漏或多餘')],
            ['TOTAL PIN COUNT MISMATCH', cn('四邊總計 ≠ PACKAGE header 總和'), cn('同上')],
            ['Inner Bond ASYMMETRIC', cn('只有 A→B 沒有 B→A'), cn('補上反向的 D1.xx 列')],
            ['PKG_LOC reassign TOTAL MISMATCH', cn('有效 PKG_NUM 數量 ≠ L+B+R+T'), cn('檢查 PKG_NUM 編號連續性和重複')],
        ],
        col_widths=[140, 140, 140],
    ))

    story.append(P('9.2 WARN ' + cn('級別'), s['S_H2']))
    story.append(make_table(
        [cn('警告訊息'), cn('原因'), cn('影響')],
        [
            ['PACKAGE definition missing', cn('Header 缺少 PACKAGE'), cn('無法進行 pin 分配和驗證')],
            ['No L-side signal pin found', cn('沒有 L 邊的非 NC pin'), 'DIE_NUM ' + cn('重編被跳過')],
            ['D1.xx reference target not found', cn('D1.xx 的目標 DIE_NUM 不存在'), cn('該 Inner Bond 連接被跳過')],
        ],
        col_widths=[140, 140, 140],
    ))

    story.append(P('9.3 ' + cn('常見陷阱（10 項）'), s['S_H2']))
    for i, t in enumerate([
        cn('PKG_LOC 手動填寫無效 — 代碼會根據 PKG_NUM 自動重算，手動值被覆蓋'),
        cn('DIE_LOC 在 PKG_TOP_LEFT_PIN=1 時不自動補全 — 需手動填寫正確的 L/B/R/T'),
        cn('DIE_NUM 會被重編 — 原始值僅用於 D1.xx 參照解析，最終值由代碼決定'),
        cn('相同 DIE_NUM 的列共享 APR pin — APR PDF 去重，只顯示一次'),
        cn('% 在 DIE_PIN_NAME 中有特殊意義 — 用於分隔 PKG 顯示名和 APR 顯示名'),
        cn('0 和 - 含義不同 — 0 表示「共用/無」，- 表示「無效/空」'),
        cn('NC 的 DIE_NUM 必須為 0 — 否則會被當作正常 pin 參與重編'),
        cn('DOWNBOND 的 DIE_NUM 必須為 0 — 否則會被當作正常 pin'),
        cn('Header 行末尾的逗號 — CSV 格式中常見，代碼自動去除，不影響解析'),
        cn('空白行 — Header 區和資料區之間的空白行會被自動跳過'),
    ], 1):
        story.append(P(f'{i}. {t}', s['S_Bul']))

    # ══════════════════════════════════════════════
    # 10
    # ══════════════════════════════════════════════
    story.append(P('10. ' + cn('附錄：欄位別名對照表'), s['S_H1']))
    story.append(P(cn('代碼使用 FIELD_ALIASES 字典進行欄位名稱匹配。CSV 表頭行中，每個欄位可使用以下任一名稱（不區分大小寫）：'), s['S_Body']))
    story.append(make_table(
        [cn('正式名稱'), cn('別名') + ' 1', cn('別名') + ' 2', cn('別名') + ' 3', cn('別名') + ' 4'],
        [
            ['PKG_NUM', 'PKG_NUM', 'PIN_NUM', '—', '—'],
            ['PKG_PIN_NAME', 'PKG_PIN_NAME', 'PACKAGE_PIN', 'PKG_PIN', '—'],
            ['DIE_NUM', 'DIE_NUM', 'DIE_PAD_NUM', '—', '—'],
            ['DIE_PIN_NAME', 'DIE_PIN_NAME', 'PIN_NAME', '—', '—'],
            ['IO_CELL_NAME', 'IO_CELL_NAME', 'CELL_NAME', 'IO_CELL', 'IOCELL'],
            ['PKG_LOC', 'PKG_LOC', 'LOCATION', 'PIN_LOCA', '—'],
            ['DIE_LOC', 'DIE_LOC', 'DIE_PAD_NUM_LOC', 'DIE_LOCA', '—'],
            ['DIRECTION', 'DIRECTION', 'IO_DIRECTION', 'IO_TYPE', 'DIR'],
            ['LOAD', 'LOAD', 'CAP', 'CAPACITANCE', '—'],
            ['SLEW', 'SLEW', 'TRANSITION', 'SLEW_RATE', '—'],
            ['SSO', 'SSO', 'SSO_RATIO', '—', '—'],
        ],
        col_widths=[80, 85, 90, 80, 80],
    ))

    # ══════════════════════════════════════════════
    # 11
    # ══════════════════════════════════════════════
    story.append(P('11. ' + cn('附錄：內部欄位名稱'), s['S_H1']))
    story.append(P(cn('代碼內部統一使用以下欄位名稱（不論輸入使用何種別名）：'), s['S_Body']))
    story.append(make_table(
        [cn('欄位'), cn('說明'), cn('來源')],
        [
            ['PKG_NUM', cn('封裝腳位編號'), cn('CSV 輸入')],
            ['PKG_PIN_NAME', cn('封裝側 pin 名稱'), cn('CSV 輸入')],
            ['DIE_NUM', cn('晶粒墊片編號'), cn('CSV 輸入（會被重編）')],
            ['DIE_PIN_NAME', cn('晶粒側 pin 名稱'), cn('CSV 輸入')],
            ['IO_CELL_NAME', cn('IO Cell 名稱'), cn('CSV 輸入或 Verilog 自動填入')],
            ['PKG_LOC', cn('封裝側邊位置'), cn('自動計算（覆蓋手動值）')],
            ['DIE_LOC', cn('晶粒側邊位置'), cn('CSV 輸入或自動計算')],
            ['DIRECTION', cn('腳位方向'), cn('CSV 輸入或 Verilog 自動填入')],
            ['LOAD', cn('電容值'), cn('CSV 輸入')],
            ['SLEW', cn('轉換率'), cn('CSV 輸入')],
            ['SSO', cn('SSO 比值'), cn('CSV 輸入')],
            ['INST_NAME', cn('Instance 名稱'), cn('自動填入（非 CSV 欄位）')],
        ],
        col_widths=[90, 140, 190],
    ))

    # ══════════════════════════════════════════════
    # 12
    # ══════════════════════════════════════════════
    story.append(P('12. ' + cn('附錄：代碼位置參考'), s['S_H1']))
    story.append(make_table(
        [cn('功能'), cn('函數'), cn('行號（約）')],
        [
            [cn('別名定義'), 'FIELD_ALIASES', '70-82'],
            [cn('CSV 解析'), '_parse_csv()', '121-201'],
            [cn('Tab 解析'), '_parse_txt()', '203-268'],
            ['Ring Shift', '_ring_shift_data()', '434-477'],
            ['PKG_NUM ' + cn('重編'), '_reindex_pkg_num()', '479-509'],
            ['PKG_LOC ' + cn('重算'), '_reassign_pkg_loc()', '511-561'],
            ['DIE_LOC ' + cn('重算'), '_reassign_die_loc()', '563-592'],
            ['Sanity Check', '_sanity_check_list()', '338-396'],
            ['DIE_NUM ' + cn('重編'), '_reorder_and_reindex_apr_data()', '270-336'],
            ['Side ' + cn('計算'), '_get_ring_side()', '398-432'],
            ['.new ' + cn('輸出'), 'generate_completed_list()', '1333-1367'],
            ['.new.csv ' + cn('輸出'), 'generate_completed_csv()', '1369-1392'],
        ],
        col_widths=[110, 180, 130],
    ))

    return story


def main():
    import os
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'CSV_INPUT_SPEC.pdf')

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title='FT_PAD_ASSIGN CSV Input Specification',
        author='kfy123bot',
    )

    doc.build(build_doc())
    print(f'PDF generated: {out_path}')


if __name__ == '__main__':
    main()
