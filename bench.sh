#!/bin/bash
# TanzuBench suite wrapper.
# Delegates to tools/bench_suite.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

URL=""
MODEL=""
ENGINE="vllm"
FOUNDATION=""
HARDWARE=""
GPU_COUNT="0"
GPU_MODEL=""
JUDGE_URL=""
JUDGE_MODEL=""
JUDGE_API_KEY=""
CATEGORIES=""
OUTPUT=""
TAG=""
API_KEY=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --url)            URL="$2"; shift 2 ;;
    --api-key)        API_KEY="$2"; shift 2 ;;
    --model)          MODEL="$2"; shift 2 ;;
    --engine)         ENGINE="$2"; shift 2 ;;
    --foundation)     FOUNDATION="$2"; shift 2 ;;
    --hardware)       HARDWARE="$2"; shift 2 ;;
    --gpu-count)      GPU_COUNT="$2"; shift 2 ;;
    --gpu-model)      GPU_MODEL="$2"; shift 2 ;;
    --judge-url)      JUDGE_URL="$2"; shift 2 ;;
    --judge-model)    JUDGE_MODEL="$2"; shift 2 ;;
    --judge-api-key)  JUDGE_API_KEY="$2"; shift 2 ;;
    --categories)     CATEGORIES="$2"; shift 2 ;;
    --output)         OUTPUT="$2"; shift 2 ;;
    --tag)            TAG="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$URL" || -z "$MODEL" || -z "$FOUNDATION" || -z "$HARDWARE" ]]; then
  echo "Usage: $0 --url <url> --model <name> --foundation <name> --hardware cpu|gpu [options]" >&2
  exit 2
fi

ARGS=(
  --url "$URL" --model "$MODEL" --engine "$ENGINE"
  --foundation "$FOUNDATION" --hardware "$HARDWARE"
  --gpu-count "$GPU_COUNT"
)
[[ -n "$API_KEY" ]]       && ARGS+=(--api-key "$API_KEY")
[[ -n "$GPU_MODEL" ]]     && ARGS+=(--gpu-model "$GPU_MODEL")
[[ -n "$JUDGE_URL" ]]     && ARGS+=(--judge-url "$JUDGE_URL")
[[ -n "$JUDGE_MODEL" ]]   && ARGS+=(--judge-model "$JUDGE_MODEL")
[[ -n "$JUDGE_API_KEY" ]] && ARGS+=(--judge-api-key "$JUDGE_API_KEY")
[[ -n "$CATEGORIES" ]]    && ARGS+=(--categories "$CATEGORIES")
[[ -n "$OUTPUT" ]]        && ARGS+=(--output "$OUTPUT")
[[ -n "$TAG" ]]           && ARGS+=(--tag "$TAG")

exec python3 "$SCRIPT_DIR/tools/bench_suite.py" "${ARGS[@]}"
