#!/usr/bin/env bash
# End-to-end test of the chatbot interrupt flow
set -e

cd "$(dirname "$0")"
PORT=8103

.venv/bin/uvicorn src.server:app --port $PORT > /tmp/uv_test.log 2>&1 &
UVPID=$!
trap 'kill $UVPID 2>/dev/null' EXIT
sleep 4

echo "=== Turn 1: describe problem ==="
R1=$(curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "I run a med spa in Miami and need more bookings", "thread_id": "t1"}')
echo "$R1" | python3 -c "import sys,json; d=json.load(sys.stdin); print('reply:', d['reply'][:120]); print('awaiting:', d['awaiting_approval'], '| complete:', d['info_complete'])"

echo ""
echo "=== Turn 2: name + email ==="
R2=$(curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "My name is Maria Lopez, email maria@medspa.com", "thread_id": "t1"}')
echo "$R2" | python3 -c "import sys,json; d=json.load(sys.stdin); print('reply:', d['reply'][:160]); print('awaiting:', d['awaiting_approval'], '| complete:', d['info_complete'])"
