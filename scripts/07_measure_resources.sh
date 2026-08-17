#!/usr/bin/env bash
# 采集 SLAM 节点 CPU/内存占用（用于双 SLAM 对比数据）
# 在【建图开始前】另开终端运行，采集 N 秒后 Ctrl+C 结束，日志写到 scripts/logs/
# 用法：./scripts/07_measure_resources.sh <进程关键字> <秒数>
#   例：./scripts/07_measure_resources.sh cartographer_node 120        # 方法一
#       ./scripts/07_measure_resources.sh async_slam_toolbox_node 120  # 方法二
set -e

KEYWORD="${1:?用法: $0 <进程关键字> <秒数> 例: $0 cartographer_node 120}"
SECONDS="${2:-120}"

LOGDIR="$(cd "$(dirname "$0")" && pwd)/logs"
mkdir -p "$LOGDIR"
OUT="$LOGDIR/top_${KEYWORD}.log"

echo "开始采集进程 [$KEYWORD] 资源占用，共 ${SECONDS}s，输出到 $OUT"
echo "时刻(秒)  %CPU  物理内存RSS(MB)  进程名" | tee "$OUT"

for i in $(seq 1 "$SECONDS"); do
    ps -eo pcpu,rss,comm --no-headers \
        | awk -v k="$KEYWORD" '$3 ~ k {printf "%d  %5.1f  %8.1f   %s\n", '"$i"', $1, $2/1024, $3}' \
        | tee -a "$OUT"
    sleep 1
done

echo "采集完成。汇总均值（平均%CPU / 平均RSS MB）："
awk '$2 ~ /^[0-9]/ {sum+=$2; cnt++; rss+=$3} END {if(cnt>0) printf "  平均%%CPU=%.1f  平均RSS=%.1fMB  (%d 个采样点)\n", sum/cnt, rss/cnt, cnt}' "$OUT"
