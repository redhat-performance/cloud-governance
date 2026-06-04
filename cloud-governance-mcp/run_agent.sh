#!/bin/bash

set -e

echo "Starting Cloud Governance AI Agent..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  vi .env"
    exit 1
fi

# Setup Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
python -m pip install -U pip > /dev/null
python -m pip install -r requirements.txt

# Stop existing Streamlit processes on port 8501
echo "Stopping existing Streamlit processes..."
pids=""
for pid in $(lsof -ti tcp:8501 2>/dev/null); do
  if ps -o cmd= -p "$pid" 2>/dev/null | grep -q "streamlit"; then
    pids="$pids $pid"
  fi
done
if [ -n "$pids" ]; then
  kill $pids 2>/dev/null || true
  sleep 1
  kill -9 $pids 2>/dev/null || true
fi

# Configure Streamlit (skip telemetry prompt)
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml <<EOF
[browser]
gatherUsageStats = false

[client]
showErrorDetails = false
EOF

# Start Streamlit (MCP server starts automatically as a stdio subprocess)
echo "Starting Streamlit on http://localhost:8501"
nohup streamlit run app.py --server.port 8501 --server.headless true > streamlit.log 2>&1 &

# Wait for Streamlit to start
sleep 3

# Check if Streamlit is running
if lsof -i :8501 > /dev/null 2>&1; then
    echo "✅ Streamlit started successfully"
    echo ""
    echo "🌐 Access the UI at: http://localhost:8501"
    echo "📝 View logs: tail -f streamlit.log"
    echo "🛑 Stop server: kill \$(lsof -ti tcp:8501)"
else
    echo "❌ Failed to start Streamlit"
    echo "Check logs: cat streamlit.log"
    exit 1
fi
