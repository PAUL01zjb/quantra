#!/usr/bin/env bash
set -euo pipefail

# Quantra 一键安装：创建虚拟环境 → 安装依赖 → 交互式配置
PYTHON="${PYTHON:-python3}"

echo "📦 Quantra 安装开始"
echo "─────────────────────────────"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "❌ 未找到 Python：$PYTHON（需要 3.9+）"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "🔧 创建虚拟环境 .venv ..."
  "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "⬇️  安装依赖（production extras：LangGraph / Qdrant / bge / MinerU / Langfuse）..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -e ".[production]" >/dev/null

echo "⚙️  运行配置向导（LLM / Embedding / Vector Store / Parser / Observability，密钥只写入本地 .env）..."
quantra setup

echo ""
echo "✅ 安装完成！接下来你可以："
echo "   quantra ui          # 打开主界面（浏览器）"
echo "   quantra ask \"消费龙头2025年毛利率是多少？\""
echo "   quantra verify      # 端到端验证"
