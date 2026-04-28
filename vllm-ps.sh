#!/usr/bin/env bash
# vllm-ps — closest analogue to `ollama ps` for the vLLM stack.
#
# vLLM serves one model per process; the 9 names in /v1/models are aliases
# to a single loaded backend. This script prints:
#   1. container status
#   2. backend model + aliases (alias → root, max_model_len)
#   3. live engine stats (running/waiting requests, KV cache util, throughput)
#   4. GPU memory the engine is holding
#
# Usage: ./vllm-ps.sh [host:port]    (default: localhost:8001)

set -euo pipefail

ENDPOINT="${1:-localhost:8001}"
BASE="http://${ENDPOINT}"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
dim()  { printf '\033[2m%s\033[0m\n' "$*"; }

bold "── container ──"
if docker ps --filter name=^vllm$ --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -q .; then
  docker ps --filter name=^vllm$ --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
else
  echo "vllm container not running"
  exit 1
fi
echo

bold "── health (${BASE}/health) ──"
if curl -fs --max-time 3 "${BASE}/health" >/dev/null; then
  echo "OK"
else
  echo "UNHEALTHY — engine not responding on ${BASE}/health"
  exit 2
fi
echo

bold "── served models (${BASE}/v1/models) ──"
curl -fs --max-time 5 "${BASE}/v1/models" \
  | jq -r '.data
      | group_by(.root)[]
      | "backend: \(.[0].root)  (max_model_len=\(.[0].max_model_len))",
        (.[] | "  └─ \(.id)")'
echo

bold "── engine stats (${BASE}/metrics) ──"
# vLLM emits Prometheus metrics; pull the human-interesting ones.
metrics=$(curl -fs --max-time 5 "${BASE}/metrics" || true)
if [[ -z "$metrics" ]]; then
  dim "no metrics endpoint (or empty response)"
else
  echo "$metrics" | awk '
    /^vllm:num_requests_running/ && !/^#/      { printf "  running requests : %s\n", $NF }
    /^vllm:num_requests_waiting/ && !/^#/      { printf "  waiting requests : %s\n", $NF }
    /^vllm:kv_cache_usage_perc/ && !/^#/       { printf "  KV cache util    : %.1f%%\n", $NF * 100 }
    /^vllm:prefix_cache_hits_total/ && !/^#/   { hits=$NF }
    /^vllm:prefix_cache_queries_total/ && !/^#/{ qs=$NF }
    END { if (qs+0 > 0) printf "  prefix cache hit : %.1f%% (%d/%d)\n", (hits/qs)*100, hits, qs }
    /^vllm:prompt_tokens_total/ && !/^#/       { printf "  prompt tokens    : %s (cumulative)\n", $NF }
    /^vllm:generation_tokens_total/ && !/^#/   { printf "  generated tokens : %s (cumulative)\n", $NF }
  '
fi
echo

bold "── GPU memory ──"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader \
    | awk -F', ' 'BEGIN{print "  PID\tPROCESS\t\tVRAM"} {printf "  %s\t%-16s\t%s\n",$1,$2,$3}'
else
  dim "nvidia-smi not on PATH"
fi
