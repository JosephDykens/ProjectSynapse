-- Unified Database Schema for SynapseChat Self-Hosted Bot
-- Includes web_panel_commands table for unified command processing

-- Bot status tracking
CREATE TABLE IF NOT EXISTS bot_status (
    id SERIAL PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bot statistics
CREATE TABLE IF NOT EXISTS bot_statistics (
    id SERIAL PRIMARY KEY,
    data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Legacy command queue (for backwards compatibility)
CREATE TABLE IF NOT EXISTS command_queue (
    id SERIAL PRIMARY KEY,
    command_type VARCHAR(50) NOT NULL,
    command_data JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSONB
);

-- Unified command processing table
CREATE TABLE IF NOT EXISTS web_panel_commands (
    id SERIAL PRIMARY KEY,
    command_type VARCHAR(50) NOT NULL,
    command_data JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSONB,
    priority INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'web_panel'
);

-- Chat logs for web panel display
CREATE TABLE IF NOT EXISTS chat_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    username VARCHAR(100),
    message TEXT,
    guild_id VARCHAR(50),
    guild_name VARCHAR(100),
    channel_id VARCHAR(50),
    channel_name VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(20) DEFAULT 'message'
);

-- Moderation actions
CREATE TABLE IF NOT EXISTS moderation_actions (
    id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    target_user VARCHAR(50),
    target_username VARCHAR(100),
    moderator VARCHAR(50),
    moderator_username VARCHAR(100),
    reason TEXT,
    duration_hours INTEGER,
    guild_id VARCHAR(50),
    guild_name VARCHAR(100),
    source VARCHAR(50) DEFAULT 'web_panel',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- System configuration
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System alerts
CREATE TABLE IF NOT EXISTS system_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50),
    message TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- User sessions for web panel
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100),
    session_token VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- Panel users
CREATE TABLE IF NOT EXISTS panel_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    discord_user_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for optimal performance
CREATE INDEX IF NOT EXISTS idx_bot_status_updated ON bot_status(updated_at);
CREATE INDEX IF NOT EXISTS idx_bot_statistics_timestamp ON bot_statistics(timestamp);
CREATE INDEX IF NOT EXISTS idx_command_queue_status ON command_queue(status);
CREATE INDEX IF NOT EXISTS idx_command_queue_created ON command_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_web_panel_commands_status ON web_panel_commands(status);
CREATE INDEX IF NOT EXISTS idx_web_panel_commands_created ON web_panel_commands(created_at);
CREATE INDEX IF NOT EXISTS idx_web_panel_commands_priority ON web_panel_commands(priority DESC);
CREATE INDEX IF NOT EXISTS idx_chat_logs_timestamp ON chat_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_guild ON chat_logs(guild_id);
CREATE INDEX IF NOT EXISTS idx_moderation_actions_target ON moderation_actions(target_user);
CREATE INDEX IF NOT EXISTS idx_moderation_actions_active ON moderation_actions(is_active);
CREATE INDEX IF NOT EXISTS idx_moderation_actions_expires ON moderation_actions(expires_at);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_alerts_status ON system_alerts(status);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_panel_users_username ON panel_users(username);
CREATE INDEX IF NOT EXISTS idx_panel_users_discord ON panel_users(discord_user_id);

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value) VALUES 
    ('crosschat_enabled', 'true'),
    ('auto_moderation_enabled', 'true'),
    ('panel_version', '"unified_v1.0"')
ON CONFLICT (config_key) DO NOTHING;

-- Insert default admin user (password: admin123 - CHANGE THIS!)
INSERT INTO panel_users (username, password_hash, role) VALUES 
    ('admin', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'admin')
ON CONFLICT (username) DO NOTHING;