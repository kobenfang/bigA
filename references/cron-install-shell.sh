# BigA Cron 安装命令模板
# cron message 仅引用SKILL.md，行为由SKILL.md驱动，更新SKILL.md即更新行为
# 安装时请替换 CHANNEL 和 TARGET 为实际值：
#   openclaw directory  # 获取当前渠道和目标，或从会话上下文读取
#   CHANNEL = feishu / discord / telegram 等
#   TARGET = ou_xxx / channel_id / chat_id 等

# 0. 创建本地发送配置（不上传到skill仓库）
#    script 的 --send-segments 会从这里读取默认 channel/target
cat > ~/.openclaw/workspace/memory/biga-send-config.json << 'EOF'
{"channel": "CHANNEL", "target": "TARGET"}
EOF

# 1. 开盘前瞻（早8:30）
#    消息内容会直接传给模型，模型再结合 SKILL.md 执行完整流程
openclaw cron add \
  --name biga-morning \
  --cron "30 8 * * 1-5" \
  --tz "Asia/Shanghai" \
  --message "biga-morning: 开盘前瞻。严格执行SKILL.md：web_search×2(隔夜外围+当日热点), python3 scripts/biga-scan.py --segments扫描, 按开盘/复盘格式输出。池外部分必须按新规范——从强势板块筛选3-5支池外候选, 每支写详细(板块·长线·短线·催化·操作建议), 用--codes扫描评分, 双信号对齐校验通过才推。无候选也要说明原因。" \
  --timeout-seconds 600 \
  --channel CHANNEL \
  --to TARGET \
  --session isolated \
  --no-deliver

# 2. 盘中扫描（9:30/10:30/11:30/13:30/14:30）
openclaw cron add \
  --name biga-scan \
  --cron "30 9,10,11,13,14 * * 1-5" \
  --tz "Asia/Shanghai" \
  --message "biga-scan: 盘中扫描(涨跌幅>5%或成交量>50%才有异动)。读stock-pool.mdBigA总分,执行python3 scripts/biga-scan.py --segments检查异动,有异动时模型补全BigA总分后构造内容+--send-segments发送,无异动不推送" \
  --timeout-seconds 600 \
  --channel CHANNEL \
  --to TARGET \
  --session isolated \
  --no-deliver

# 3. 收盘复盘（15:30）
openclaw cron add \
  --name biga-evening \
  --cron "30 15 * * 1-5" \
  --tz "Asia/Shanghai" \
  --message "biga-evening: 收盘复盘。web_search×2(大盘+强势板块→池外候选), 从强势板块挑3-5支池外候选, python3 scripts/biga-scan.py --codes <候选>扫描评分, 双信号对齐校验。输出按开盘/复盘格式, 池外每支必须写详细(板块·长线·短线·催化·操作建议), 无候选也要写原因。" \
  --timeout-seconds 600 \
  --channel CHANNEL \
  --to TARGET \
  --session isolated \
  --no-deliver
