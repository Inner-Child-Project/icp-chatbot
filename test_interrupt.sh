#!/usr/bin/env bash
# Full interrupt loop test: approve + reject paths
set -e
cd "$(dirname "$0")"
PORT=8104

.venv/bin/uvicorn src.server:app --port $PORT > /tmp/uv5.log 2>&1 &
UVPID=$!
trap 'kill $UVPID 2>/dev/null' EXIT
sleep 4

echo "=== Build up to proposal (approve path) ==="
curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "I run a dental office needing patients", "thread_id": "approve1"}' > /dev/null
curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "Dr. Ana Perez, ana@dental.com", "thread_id": "approve1"}' > /dev/null

echo "--- Now approve with 'yes' (resume) ---"
R=$(curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "yes that works", "thread_id": "approve1", "resume_value": "yes that works"}')
echo "$R" | python3 -c "import sys,json; d=json.load(sys.stdin); print('submitted:', d['submitted'], '| awaiting:', d['awaiting_approval']); print('reply:', d['reply'][:150])"

echo ""
echo "=== Reject path ==="
curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "I run a gym needing members", "thread_id": "reject1"}' > /dev/null
curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "Carlos Diaz, carlos@gym.com", "thread_id": "reject1"}' > /dev/null

echo "--- Now reject with changes (resume) ---"
R2=$(curl -s -X POST http://localhost:$PORT/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "no, I also need Instagram booking", "thread_id": "reject1", "resume_value": "no, I also need Instagram booking"}')
echo "$R2" | python3 -c "import sys,json; d=json.load(sys.stdin); print('submitted:', d['submitted'], '| awaiting:', d['awaiting_approval']); print('reply:', d['reply'][:150])"
