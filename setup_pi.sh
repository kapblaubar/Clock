#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/Clock}"
SERVICE_NAME="clock.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

sudo apt update
sudo apt install -y python3-pygame python3-pil

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
chmod +x setup_pi.sh || true

if [[ -f clock.service ]]; then
  sed "s|/home/pi/Clock|$PROJECT_DIR|g; s|User=pi|User=$(whoami)|g" clock.service | sudo tee "$SERVICE_PATH" >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable "$SERVICE_NAME"
  sudo systemctl restart "$SERVICE_NAME" || sudo systemctl start "$SERVICE_NAME"
fi

echo "Setup complete."
echo "Run manually with: cd $PROJECT_DIR && python3 pi_clock.py"
echo "Service status: sudo systemctl status $SERVICE_NAME"
