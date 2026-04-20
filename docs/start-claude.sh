#!/bin/bash
# 啟動 Claude Code (使用 Minimax 中國站端點)

echo "🚀 正在切換供應商至 Minimax (minimaxi.com)..."
# 使用我們修改過的 claude-switch 切換供應商
claude-switch minimax --model minimax-m2.7

# 如果 claude-switch 沒有自動啟動 claude，我們手動啟動它
if [ $? -eq 0 ]; then
    echo "✅ 供應商切換成功，啟動 Claude Code..."
    # 這裡的 claude 指令會繼承 claude-switch 設定的環境變數
    claude
else
    echo "❌ 切換失敗，請檢查 API Key 設定。"
    exit 1
fi
