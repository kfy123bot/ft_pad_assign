#!/bin/bash
# 啟動 Claude Code (使用 Google Gemini API)

echo "🚀 正在切換供應商至 Google Gemini..."

# 使用 claude-switch 切換供應商至 openrouter 並指定 Gemini 模型
# 這裡使用 google/gemini-2.0-pro-exp-02-05:free (你也可以改成付費版 google/gemini-2.0-pro-exp-02-05)
claude-switch openrouter --model google/gemini-2.0-pro-exp-02-05:free

# 如果 claude-switch 沒有自動啟動 claude，我們手動啟動它
if [ $? -eq 0 ]; then
    echo "✅ 供應商切換成功，啟動 Claude Code..."
    # 這裡的 claude 指令會繼承 claude-switch 設定的環境變數
    claude
else
    echo "❌ 切換失敗，請檢查 Gemini API Key 設定。"
    exit 1
fi
