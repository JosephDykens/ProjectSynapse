#!/bin/bash
set -e

echo "🤖 Installing SynapseChat Discord Bot..."
echo ""

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv

# Create user and directory
sudo useradd -r -s /bin/false synapsechat
sudo mkdir -p /opt/synapsechat-bot
sudo mkdir -p /var/log/synapsechat

# Copy files
sudo cp bot.py /opt/synapsechat-bot/
sudo cp requirements.txt /opt/synapsechat-bot/

# Install Python dependencies
cd /opt/synapsechat-bot
sudo python3 -m pip install -r requirements.txt

# Set permissions
sudo chown -R synapsechat:synapsechat /opt/synapsechat-bot
sudo chown -R synapsechat:synapsechat /var/log/synapsechat

# Install systemd service
sudo cp synapsechat-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit /etc/systemd/system/synapsechat-bot.service"
echo "2. Set your environment variables (DISCORD_TOKEN, DATABASE_URL, BOT_OWNER_ID)"
echo "3. Run: sudo systemctl enable synapsechat-bot"
echo "4. Run: sudo systemctl start synapsechat-bot"
echo "5. Check status: sudo systemctl status synapsechat-bot"
echo "6. View logs: sudo journalctl -u synapsechat-bot -f"
echo ""
echo "🤖 Bot will start automatically on system boot"
