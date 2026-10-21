#!/usr/bin/env bash
# MovieBox Mesh - 1-Click Laptop Host Launcher (Linux/Mac)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=================================================="
echo "🎬 Starting MovieBox Mesh on Dell Latitude..."
echo "=================================================="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is not installed on this laptop."
    echo "Please install python3 (e.g., sudo apt install python3)"
    read -p "Press Enter to exit..."
    exit 1
fi

# Run the node
python3 mesh_node.py
