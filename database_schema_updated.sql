-- SynapseChat Database Schema - Unified System
-- This schema supports both bot and panel with shared tables

-- Bot status tracking
CREATE TABLE IF NOT EXISTS bot_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'offline',
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT single_status_row CHECK (id = 1)
);

-- Web panel users (for authentication)
CREATE TABLE IF NOT EXISTS panel_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Unified command processing table
CREATE TABLE IF NOT EXISTS web_panel_commands (
    id SERIAL PRIMARY KEY,
    command_type VARCHAR(50) NOT NULL,
    command_data JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT
);

-- Chat logs for monitoring
CREATE TABLE IF NOT EXISTS chat_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    username VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    server_name VARCHAR(100),
    message_type VARCHAR(20) DEFAULT 'message'
);

-- Crosschat channel configuration
CREATE TABLE IF NOT EXISTS crosschat_channels (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(20) UNIQUE NOT NULL,
    guild_id VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Guild information
CREATE TABLE IF NOT EXISTS guilds (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    member_count INTEGER DEFAULT 0,
    icon_url TEXT,
    owner_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User warnings
CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    moderator VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User bans
CREATE TABLE IF NOT EXISTS user_bans (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) UNIQUE NOT NULL,
    reason TEXT NOT NULL,
    banned_until TIMESTAMP NOT NULL,
    moderator VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System configuration
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default bot status
INSERT INTO bot_status (id, status, last_update) 
VALUES (1, 'offline', CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;

-- Insert default admin user (password: admin123)
INSERT INTO panel_users (username, password_hash, role)
VALUES ('admin', 'scrypt:32768:8:1$sHnEf78NMgGONe0p$7eb9fcde1ad7bbf1e5f1e4b0e3ad2f28c1a3e9e5f8e3e9d5f0f9f1f8e1d9e3f2c8e3e7e4f1e8d9e5f0f8e1e2e3', 'owner')
ON CONFLICT (username) DO NOTHING;

-- Insert default system config
INSERT INTO system_config (config_key, config_value) VALUES
('crosschat_enabled', 'true'),
('automod_enabled', 'false')
ON CONFLICT (config_key) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_logs_timestamp ON chat_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_web_panel_commands_status ON web_panel_commands(status);
CREATE INDEX IF NOT EXISTS idx_crosschat_channels_enabled ON crosschat_channels(enabled);
CREATE INDEX IF NOT EXISTS idx_user_bans_user_id ON user_bans(user_id);
CREATE INDEX IF NOT EXISTS idx_warnings_user_id ON warnings(user_id);