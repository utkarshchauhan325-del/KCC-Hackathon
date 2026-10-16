#!/usr/bin/env bash
# ==============================================================================
# FloodGuard CivicEye - Unified Startup Script
# Starts both the Stitch FastAPI backend (port 8000) and Streamlit UI (port 8501)
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# 1. Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  No virtualenv found at .venv or venv. Using system python3."
fi

# 2. Check and initialize Database if needed
echo "🔧 Checking database and seeds..."
python3 -c "from app.db.session import init_db; init_db()" || true

# 3. Clean up any existing instances on ports 8000 and 8501
echo "🧹 Checking ports 8000 and 8501..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8501 | xargs kill -9 2>/dev/null || true

# 4. Start FastAPI Stitch Backend (port 8000)
echo "🚀 Starting Stitch FastAPI Operations Server on http://localhost:8000 ..."
python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Trap signals to shut down both cleanly on Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Shutting down FloodGuard services..."
    kill "$FASTAPI_PID" 2>/dev/null || true
    kill "$STREAMLIT_PID" 2>/dev/null || true
    wait "$FASTAPI_PID" 2>/dev/null || true
    wait "$STREAMLIT_PID" 2>/dev/null || true
    echo "✅ Shutdown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Give FastAPI a moment to bind
sleep 2

# 5. Start Streamlit Dashboard (port 8501)
echo "🚀 Starting Streamlit Console on http://localhost:8501 ..."
echo "------------------------------------------------------------------"
echo "✨ SYSTEM READY:"
echo "   • Stitch Priority Queue:  http://localhost:8000/priority-queue"
echo "   • Streamlit Console:      http://localhost:8501"
echo "   • API Docs (Swagger):     http://localhost:8000/docs"
echo "------------------------------------------------------------------"

python3 -m streamlit run app/ui/dashboard.py --server.port 8501 --server.headless true --browser.serverAddress localhost &
STREAMLIT_PID=$!

# Wait for background processes
wait "$FASTAPI_PID" "$STREAMLIT_PID"
