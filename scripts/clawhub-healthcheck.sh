#!/bin/bash
# ClawHub search healthcheck - parallel curl, output results
# Usage: bash scripts/clawhub-healthcheck.sh

QUERIES=(
  "全球热点:eyes"
  "国际新闻:eyes"
  "大眼看世界:eyes"
  "智能选股:biga"
  "选股分析:biga"
  "股票池:biga"
  "水果价格:fruit-pi"
  "水果派:fruit-pi"
  "智能表单:listform"
  "智能记事本:listform"
  "智能账单:listform"
  "万能信息记录:listform"
  "闪念:bigseed"
  "人生拼图:bigseed"
  "种一个世界:bigseed"
)

PASS=0
FAIL=0
RESULTS=""

for entry in "${QUERIES[@]}"; do
  q="${entry%%:*}"
  expected="${entry##*:}"
  (
    encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$q'))" 2>/dev/null)
    result=$(curl -s --max-time 10 "https://clawhub.ai/api/search?q=$encoded&limit=10" 2>/dev/null)
    slug=$(echo "$result" | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)
    slugs = [res['slug'] for res in r.get('results', [])]
    print(slugs[0] if slugs else 'NOT_FOUND')
except: print('PARSE_ERROR')
" 2>/dev/null)
    if [ "$slug" = "$expected" ]; then
      echo "✅ $q → $slug (期望 $expected)"
    elif [ "$slug" = "NOT_FOUND" ]; then
      echo "❌ $q → 未找到 (期望 $expected)"
    else
      echo "❌ $q → $slug (期望 $expected)"
    fi
  ) &
done

wait
