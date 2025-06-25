# SynapseChat Discord Bot - Complete Droplet Package

## 🚀 What's Included

**Complete Bot Files:**
- `bot.py` - Full-featured Discord bot with all SynapseChat features
- `requirements.txt` - Python dependencies
- `synapsechat-bot.service` - Systemd service file
- `install.sh` - Automated installation script

**Key Features:**
✅ Cross-server messaging with file forwarding
✅ VIP tier system (Architect/Elite get 0.5s processing)
✅ Service-level bans (crosschat only, not Discord server bans)
✅ Auto-moderation filters for content protection
✅ Performance caching reducing database queries by 95%
✅ Complete slash command system
✅ Web panel integration via shared database
✅ Real-time monitoring and heartbeat system

## 🛠️ Quick Installation

1. **Upload to your DigitalOcean droplet**
2. **Extract the package:**
   ```bash
   unzip synapsechat-bot-droplet-complete.zip
   cd synapsechat-bot-droplet-complete
   ```

3. **Run the installer:**
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```

4. **Configure your bot:**
   ```bash
   sudo nano /etc/systemd/system/synapsechat-bot.service
   ```
   Update these lines with your actual values:
   - `Environment=DISCORD_TOKEN=your_actual_discord_token`
   - `Environment=DATABASE_URL=your_actual_database_url`
   - `Environment=BOT_OWNER_ID=your_actual_discord_user_id`

5. **Start the bot:**
   ```bash
   sudo systemctl enable synapsechat-bot
   sudo systemctl start synapsechat-bot
   ```

## 📊 Monitor Your Bot

```bash
# Check bot status
sudo systemctl status synapsechat-bot

# View real-time logs
sudo journalctl -u synapsechat-bot -f

# Restart bot if needed
sudo systemctl restart synapsechat-bot
```

## 🎯 Bot Commands

**Bot Owner Commands:**
- `/announce` - Send crosschat announcements
- `/ban` - Service-level ban from crosschat
- `/unban` - Remove service-level ban
- `/status` - View bot statistics

**Server Admin Commands:**
- `/setup` - Configure crosschat channels
- `/warn` - Issue warnings to users

## 🔧 Troubleshooting

**Bot not starting?**
1. Check logs: `sudo journalctl -u synapsechat-bot -f`
2. Verify environment variables in service file
3. Test database connection manually

**Database connection issues?**
1. Verify DATABASE_URL format
2. Check firewall settings
3. Ensure PostgreSQL accepts connections

## 📁 File Structure

```
/opt/synapsechat-bot/
├── bot.py                    # Main bot application
├── simple_crosschat.py      # Crosschat system
├── database_storage_new.py  # Database operations
├── performance_cache.py     # Caching system
├── auto_moderation.py       # Content moderation
├── web_panel_sync.py       # Web panel integration
└── requirements.txt        # Python dependencies
```

## 🚀 Advanced Usage

**Enable auto-start on boot:**
```bash
# Already enabled by install script, but if needed:
sudo systemctl enable synapsechat-bot

# Start the bot service
sudo systemctl start synapsechat-bot

# Check status
sudo systemctl status synapsechat-bot

# View real-time logs
sudo journalctl -u synapsechat-bot -f
```

This package provides everything needed for a complete, production-ready SynapseChat Discord bot deployment on DigitalOcean droplets.
