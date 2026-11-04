#!/usr/bin/env bash
set -e

echo "=== Deploying Pocket TTS on Hostinger VPS ==="

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env" || export PATH="$HOME/.local/bin:$PATH"
fi

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UV_BIN="$(which uv || echo "$HOME/.local/bin/uv")"

echo "Working directory: $INSTALL_DIR"
echo "UV binary: $UV_BIN"

# 2. Setup systemd unit
SERVICE_FILE="/etc/systemd/system/pocket-tts.service"

echo "Creating systemd service at $SERVICE_FILE..."
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Kyutai Pocket TTS Service (DrOpenSource)
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$UV_BIN run pocket-tts serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 3. Reload & restart service
echo "Reloading systemd and restarting pocket-tts service..."
sudo systemctl daemon-reload
sudo systemctl enable --now pocket-tts
sudo systemctl restart pocket-tts

echo "=== Pocket TTS is now running! ==="
echo "Status check: sudo systemctl status pocket-tts"
echo "Logs: sudo journalctl -u pocket-tts -f"
