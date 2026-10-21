#!/data/data/com.termux/files/usr/bin/sh
PROJECT_DIR="/sdcard/Antigravity_Projects/moviebox-mesh"
PID_FILE="$PROJECT_DIR/.mesh.pid"
LOG_FILE="$PROJECT_DIR/mesh.log"

is_running() {
  if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
    return 0
  fi
  RUN_PID=$(pgrep -f "mesh_node.py" 2>/dev/null | grep -v "$$" | head -n 1)
  if [ -n "$RUN_PID" ]; then
    echo "$RUN_PID" > "$PID_FILE"
    return 0
  fi
  return 1
}

case "$1" in
  start)
    if is_running; then
      echo "✅ MovieBox Mesh is already running (PID: $(cat "$PID_FILE"))."
      echo "📡 Open in browser: http://10.42.0.1:8080 or http://127.0.0.1:8080"
      exit 0
    fi
    echo "Starting MovieBox Mesh daemon..."
    su -c "iptables -C INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 8080 -j ACCEPT; iptables -C INPUT -p udp --dport 9999 -j ACCEPT 2>/dev/null || iptables -I INPUT -p udp --dport 9999 -j ACCEPT" 2>/dev/null
    python3 "$PROJECT_DIR/mesh_node.py" --daemon
    sleep 1
    if is_running; then
      echo "✅ MovieBox Mesh is running! (PID: $(cat "$PID_FILE"))"
      echo "📡 Open in browser: http://10.42.0.1:8080 or http://127.0.0.1:8080"
    else
      echo "❌ Failed to start. Check $LOG_FILE"
    fi
    ;;
  stop)
    pkill -f "mesh_node.py" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "MovieBox Mesh stopped."
    ;;
  status|ip)
    if is_running; then
      echo "✅ MovieBox Mesh is RUNNING (PID: $(cat "$PID_FILE"))"
      echo "📡 Open in browser: http://10.42.0.1:8080 or http://127.0.0.1:8080"
    else
      echo "❌ MovieBox Mesh is STOPPED."
    fi
    ;;
  log)
    tail -f "$LOG_FILE"
    ;;
  *)
    if is_running; then
      echo "✅ MovieBox Mesh is ALREADY RUNNING in the background (PID: $(cat "$PID_FILE"))."
      echo "📡 Open in browser: http://10.42.0.1:8080 or http://127.0.0.1:8080"
      echo "👉 Run 'mb-mesh stop' to stop, or 'mb-mesh log' to view logs."
      exit 0
    fi
    echo "Starting MovieBox Mesh in foreground (Ctrl+C to stop)..."
    python3 "$PROJECT_DIR/mesh_node.py"
    ;;
esac
