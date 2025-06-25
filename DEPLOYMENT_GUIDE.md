# SynapseChat Bot Deployment Guide

## Quick Setup

1. Upload all files to your server
2. Install dependencies: `bash install.sh`
3. Set environment variables in `.env`
4. Run: `python3 bot.py`

## Environment Variables

```bash
DISCORD_TOKEN=your_discord_bot_token
BOT_OWNER_ID=your_discord_user_id
DATABASE_URL=postgresql://user:pass@host:port/database
STAFF_ROLE_ID=optional_staff_role_id
VIP_ROLE_ID=optional_vip_role_id
```

## Requirements

- Python 3.8+
- Discord bot token
- PostgreSQL database

The bot will automatically connect to Discord and start processing commands.