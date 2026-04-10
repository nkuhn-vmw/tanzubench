#!/bin/bash
# bosh_tunnel.sh — stable port-forward from a BOSH worker to localhost.
#
# Spawns a `bosh ssh` with `-L <local>:127.0.0.1:<remote>` and a heartbeat
# loop that health-checks the tunnel every 30s. If the tunnel dies (SSH
# drops, worker restarts, etc.) it reopens it automatically.
#
# Usage:
#   ./tools/bosh_tunnel.sh <om-cli.yml> <deployment> <instance> <local-port> [remote-port]
#
# Example:
#   ./tools/bosh_tunnel.sh /path/to/om-cli.yml \
#     genai-models <bosh-instance-id> 4000 4000 &
#
# The script runs in the foreground until killed. A log of tunnel
# events is written to /tmp/bosh-tunnel-<local-port>.log. Health checks
# hit http://127.0.0.1:<local-port>/v1/models with a 5s timeout; any
# non-200 triggers a reopen.
#
# Kill with: pkill -f "bosh_tunnel.sh.*<local-port>"

set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 <om-cli.yml> <deployment> <instance> <local-port> [remote-port]" >&2
  exit 2
fi

OM_FILE="$1"
DEPLOYMENT="$2"
INSTANCE="$3"
LOCAL_PORT="$4"
REMOTE_PORT="${5:-4000}"

LOG="/tmp/bosh-tunnel-${LOCAL_PORT}.log"
HEARTBEAT_SEC=30

log() {
  echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"
}

resolve_env() {
  # `om bosh-env` emits `export BOSH_ENVIRONMENT=... BOSH_CA_CERT=...` etc.
  # Source it so subsequent `bosh` calls know where to go.
  eval "$(om -e "$OM_FILE" bosh-env 2>/dev/null)"
}

start_tunnel() {
  log "starting tunnel :$LOCAL_PORT -> $INSTANCE:$REMOTE_PORT"
  resolve_env
  bosh -d "$DEPLOYMENT" -n ssh "$INSTANCE" \
    --opts="-L ${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
    -c 'sleep 86400' >> "$LOG" 2>&1 &
  TUNNEL_PID=$!
  log "tunnel pid=$TUNNEL_PID, waiting 8s for handshake"
  sleep 8
}

stop_tunnel() {
  if [[ -n "${TUNNEL_PID:-}" ]]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
    # bosh ssh spawns a child ssh process — kill it too
    pkill -f "ssh.*-L ${LOCAL_PORT}:" 2>/dev/null || true
    sleep 1
  fi
}

is_healthy() {
  # curl exits 0 only if connection succeeded AND we got an HTTP 2xx/3xx.
  curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    "http://127.0.0.1:${LOCAL_PORT}/v1/models" 2>/dev/null \
    | grep -qE "^(200|401|403)$"
}

trap 'log "shutting down"; stop_tunnel; exit 0' INT TERM

> "$LOG"
log "bosh_tunnel.sh starting: om=$OM_FILE dep=$DEPLOYMENT inst=$INSTANCE port=$LOCAL_PORT"
start_tunnel

# Heartbeat loop: check health, reopen on failure, loop forever.
FAILS=0
while true; do
  sleep "$HEARTBEAT_SEC"
  if is_healthy; then
    FAILS=0
  else
    FAILS=$((FAILS + 1))
    log "health check failed ($FAILS)"
    if [[ $FAILS -ge 2 ]]; then
      log "restarting tunnel after $FAILS consecutive failures"
      stop_tunnel
      start_tunnel
      FAILS=0
    fi
  fi
done
