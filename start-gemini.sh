#!/bin/bash
# 啟動 Claude Code (直接連接 Google Gemini API)

# 確保清除 Token，避免與 API Key 產生 Auth conflict
unset ANTHROPIC_AUTH_TOKEN

# 優先使用環境變數中的 GEMINI_API_KEY
if [ -z "$GEMINI_API_KEY" ]; then
    export GEMINI_API_KEY="AIzaSyDW_rQfoGeWJXlhjACDivfxrhvIBaJ6jlI"
fi

# 設定 Google 的 OpenAI 相容介面網址
export ANTHROPIC_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export ANTHROPIC_API_KEY="$GEMINI_API_KEY"

# 使用 Gemini 1.5 Pro (目前最穩定的專業版)
# 如果你想嘗試 2.0 版本，可以改回 gemini-2.0-pro-exp-02-05
export ANTHROPIC_MODEL="gemini-1.5-pro"

echo "🚀 正在直連 Google Gemini API 啟動 Claude Code..."
echo "📍 模型: $ANTHROPIC_MODEL"
echo "🌐 終端: $ANTHROPIC_BASE_URL"
echo "------------------------------------------------"

# 啟動 Claude
claude
