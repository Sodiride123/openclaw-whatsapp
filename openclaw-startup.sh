
#!/usr/bin/env bash
# openclaw-startup.sh - Register and start OpenClaw services (WhatsApp)
# Usage: ./workspace/openclaw-whatsapp/openclaw-startup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/openclaw-configuration"

echo "OpenClaw Startup"
echo "----------------------------------------"
echo "Removing any previous OpenClaw files..."
rm -rf /root/.openclaw
mkdir -p /root/.openclaw
ln -sf "${CONFIG_DIR}/openclaw.json" /root/.openclaw/openclaw.json > /dev/null 2>&1
echo "Installing WhatsApp plugin..."
openclaw plugins install @openclaw/whatsapp
echo "Linking service definitions to systemd..."
ln -sf "${CONFIG_DIR}/openclaw-settings-sync.service" /etc/systemd/system/openclaw-settings-sync.service > /dev/null 2>&1
ln -sf "${CONFIG_DIR}/openclaw.service" /etc/systemd/system/openclaw.service > /dev/null 2>&1
echo "Reloading systemd daemon and enabling services..."
systemctl daemon-reload
systemctl enable openclaw-settings-sync.service
systemctl enable openclaw.service
echo "Starting openclaw-settings-sync..."
systemctl start openclaw-settings-sync.service
sleep 5
echo "Starting openclaw gateway..."
systemctl start openclaw.service
echo "----------------------------------------"
echo "Services started:"
echo ""
systemctl --no-pager status openclaw-settings-sync.service 2>&1 | head -4
echo ""
systemctl --no-pager status openclaw.service 2>&1 | head -4
echo ""
echo "Useful commands:"
echo "  systemctl status openclaw-settings-sync   # sync service status"
echo "  systemctl status openclaw                  # gateway status"
echo "  journalctl -u openclaw-settings-sync -f    # sync logs"
echo "  journalctl -u openclaw -f                  # gateway logs"
