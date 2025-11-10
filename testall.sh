#!/usr/bin/env bash
set -euo pipefail

echo "=== 1) Support Bot: start chat ==="
CHAT_JSON=$(curl -s -X POST https://studio-amp-support-bot.box-of-ai.com/chat/start \
  -H "Content-Type: application/json" \
  -d '{"kb_ids":["amplivo_comp_plan_md"],"message":"What do I need to reach 1 Star?"}')
echo "$CHAT_JSON"

CHAT_ID=$(echo "$CHAT_JSON" | sed -n 's/.*"chat_id":"\([^"]*\)".*/\1/p')

echo
echo "=== 2) Support Bot: follow-up in same chat ($CHAT_ID) ==="
curl -s -X POST https://studio-amp-support-bot.box-of-ai.com/chat/reply \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"'"$CHAT_ID"'","message":"Answer in one short sentence."}'

echo
echo
echo "=== 3) SQL Gen: llama-3-sqlcoder-8b ==="
curl -s -X POST https://studio-amp-sql-gen.box-of-ai.com/nl2sql/compile \
  -H "Content-Type: application/json" \
  -d '{"question":"List the top 5 customers by revenue in the last 30 days","dialect":"postgres","model":"llama-3-sqlcoder-8b:latest"}'

echo
echo
echo "=== 4) SQL Gen: sqlcoder-best ==="
curl -s -X POST https://studio-amp-sql-gen.box-of-ai.com/nl2sql/compile \
  -H "Content-Type: application/json" \
  -d '{"question":"List the top 5 customers by revenue in the last 30 days","dialect":"postgres","model":"sqlcoder-best:latest"}'

echo
echo
echo "=== 5) Translator: English -> Thai ==="
curl -s -X POST https://studio-amp-translator.box-of-ai.com/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","target_lang":"th"}'

echo
echo "=== DONE ==="