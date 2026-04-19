#!/bin/bash

# FPAD_ASSIGN GitHub 上傳腳本
# 請確保你已經撤銷了舊的 Token 並申請了一個新的。

echo "=== FPAD_ASSIGN GitHub Deploy Tool ==="
read -p "請輸入你的 GitHub 使用者名稱: " GH_USER
read -s -p "請輸入你的 GitHub Token (隱藏輸入): " GH_TOKEN
echo ""

REPO_NAME="fpad_assign"

# 1. 建立遠端倉庫 (使用 GitHub API)
echo "[1/4] 正在 GitHub 上建立新倉庫: $REPO_NAME..."
curl -H "Authorization: token $GH_TOKEN" https://api.github.com/user/repos -d "{\"name\":\"$REPO_NAME\", \"private\":false}"

# 2. 初始化本地 Git
echo "[2/4] 正在初始化本地 Git..."
git init
git add .
git commit -m "Initial commit of fpad_assign tool"
git branch -M main

# 3. 設定遠端地址 (安全方式：不保留 Token 在 config)
echo "[3/4] 正在連接遠端倉庫..."
git remote remove origin 2>/dev/null
git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git"

# 4. 推送到 GitHub
echo "[4/4] 正在推送到 GitHub..."
# 這裡會要求你輸入使用者名稱與密碼 (密碼請輸入剛才的 Token)
git push -u origin main

echo "=== 大功告成！專案已上傳至 https://github.com/$GH_USER/$REPO_NAME ==="
