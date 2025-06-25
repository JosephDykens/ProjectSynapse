#!/usr/bin/env python3
"""
SynapseChat Web Panel - Self-Hosted Version
Panel-only mode for managing remote Discord bot
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# Load environment variables
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def hash_password(password):
    """Hash password for storage using scrypt"""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='scrypt')

def verify_password(password, hashed):
    """Verify password against hash"""
    from werkzeug.security import check_password_hash
    return check_password_hash(hashed, password)

def create_session_token():
    """Create secure session token"""
    return secrets.token_urlsafe(32)

def initialize_admin():
    """Initialize admin account (one-time setup)"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if admin user exists
        cursor.execute("SELECT username FROM users WHERE username = %s", ('Joeyxpk',))
        if cursor.fetchone():
            print("Admin user already exists")
            return True
        
        # Create admin user with password Sept161997!
        admin_password = "Sept161997!"
        admin_hash = hash_password(admin_password)
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active) VALUES (%s, %s, %s, %s)",
            ('Joeyxpk', admin_hash, 'owner', True)
        )
        
        conn.commit()
        print("Admin user created successfully")
        print("Username: Joeyxpk")
        print("Password: Sept161997!")
        return True
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False
    finally:
        conn.close()

@app.route('/')
def index():
    """Serve the main panel page"""
    return render_template_string(PANEL_HTML)

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = %s AND is_active = true", (username,))
        user = cursor.fetchone()
        
        if not user or not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Create session token
        token = create_session_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute(
            "INSERT INTO sessions (token, username, role, expires_at) VALUES (%s, %s, %s, %s) ON CONFLICT (token) DO UPDATE SET expires_at = EXCLUDED.expires_at",
            (token, username, user['role'], expires_at)
        )
        conn.commit()
        
        return jsonify({
            'token': token,
            'username': username,
            'role': user['role']
        })
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500
    finally:
        conn.close()

@app.route('/api/verify', methods=['GET'])
def verify_session():
    """Verify session token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role FROM sessions WHERE token = %s AND expires_at > NOW()",
            (token,)
        )
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        return jsonify({
            'username': session['username'],
            'role': session['role']
        })
        
    except Exception as e:
        print(f"Session verification error: {e}")
        return jsonify({'error': 'Session verification failed'}), 500
    finally:
        conn.close()

@app.route('/api/stats', methods=['GET'])
def get_status():
    """Get system status"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Get bot status
        cursor.execute("SELECT data FROM bot_status WHERE id = 1")
        bot_status = cursor.fetchone()
        
        if bot_status:
            status_data = bot_status['data']
        else:
            status_data = {
                'status': 'offline',
                'uptime': 0,
                'messages_processed': 0
            }
        
        # Get server count
        cursor.execute("SELECT COUNT(*) as count FROM crosschat_channels")
        server_count = cursor.fetchone()['count']
        
        # Get user count
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = true")
        user_count = cursor.fetchone()['count']
        
        return jsonify({
            'bot_status': status_data.get('status', 'offline'),
            'uptime': status_data.get('uptime', 0),
            'messages_processed': status_data.get('messages_processed', 0),
            'server_count': server_count,
            'user_count': user_count
        })
        
    except Exception as e:
        print(f"Status error: {e}")
        return jsonify({'error': 'Failed to get status'}), 500
    finally:
        conn.close()

@app.route('/api/chat-logs', methods=['GET'])
def get_chat_logs():
    """Get recent chat logs"""
    return jsonify([])  # Empty logs for privacy

# HTML Template for the panel
PANEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SynapseChat Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container { 
            background: white;
            padding: 3rem;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        .logo { 
            text-align: center;
            margin-bottom: 2rem;
        }
        .logo h1 { 
            color: #5865f2;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .logo p { 
            color: #6b7280;
            font-size: 1rem;
        }
        .form-group { 
            margin-bottom: 1.5rem;
        }
        label { 
            display: block;
            margin-bottom: 0.5rem;
            color: #374151;
            font-weight: 500;
        }
        input { 
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        input:focus { 
            outline: none;
            border-color: #5865f2;
        }
        .btn { 
            width: 100%;
            padding: 0.75rem;
            background: #5865f2;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .btn:hover { 
            background: #4752c4;
        }
        .error { 
            background: #fee2e2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: none;
        }
        .panel { 
            display: none;
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 90%;
            max-width: 1200px;
            margin: 2rem auto;
        }
        .header { 
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e5e7eb;
        }
        .nav { 
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .nav-item { 
            padding: 0.5rem 1rem;
            background: #f3f4f6;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .nav-item.active, .nav-item:hover { 
            background: #5865f2;
            color: white;
        }
        .tab-content { 
            display: none;
        }
        .tab-content.active { 
            display: block;
        }
        .stats-grid { 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card { 
            background: #f8fafc;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value { 
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
        }
        .stat-label { 
            color: #6b7280;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div id="login-form" class="container">
        <div class="logo">
            <h1>SynapseChat</h1>
            <p>Discord Bot Management Panel</p>
        </div>
        
        <div id="login-error" class="error"></div>
        
        <form onsubmit="handleLogin(event)">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit" class="btn">Sign In</button>
        </form>
    </div>

    <div id="main-panel" class="panel">
        <div class="header">
            <h1>SynapseChat Dashboard</h1>
            <button onclick="logout()" class="btn" style="width: auto; padding: 0.5rem 1rem;">Logout</button>
        </div>
        
        <div class="nav">
            <div class="nav-item active" onclick="showTab('dashboard')">Dashboard</div>
            <div class="nav-item" onclick="showTab('settings')">Settings</div>
        </div>
        
        <div id="dashboard-tab" class="tab-content active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div id="bot-status" class="stat-value">Offline</div>
                    <div class="stat-label">Bot Status</div>
                </div>
                <div class="stat-card">
                    <div id="uptime" class="stat-value">0</div>
                    <div class="stat-label">Uptime (hours)</div>
                </div>
                <div class="stat-card">
                    <div id="messages" class="stat-value">0</div>
                    <div class="stat-label">Messages Processed</div>
                </div>
                <div class="stat-card">
                    <div id="servers" class="stat-value">0</div>
                    <div class="stat-label">Connected Servers</div>
                </div>
            </div>
        </div>
        
        <div id="settings-tab" class="tab-content">
            <h2>Panel Settings</h2>
            <p>Bot management and configuration options will be available here.</p>
        </div>
    </div>

    <script>
        let authToken = localStorage.getItem('auth_token');
        
        if (authToken) {
            checkAuth();
        }
        
        async function handleLogin(event) {
            event.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    authToken = data.token;
                    localStorage.setItem('auth_token', authToken);
                    showPanel();
                } else {
                    showError(data.error || 'Login failed');
                }
            } catch (error) {
                showError('Connection error');
            }
        }
        
        async function checkAuth() {
            try {
                const response = await fetch('/api/verify', {
                    headers: {
                        'Authorization': 'Bearer ' + authToken
                    }
                });
                
                if (response.ok) {
                    showPanel();
                } else {
                    logout();
                }
            } catch (error) {
                logout();
            }
        }
        
        function showPanel() {
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('main-panel').style.display = 'block';
            loadDashboard();
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('login-error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
        
        function logout() {
            authToken = null;
            localStorage.removeItem('auth_token');
            document.getElementById('login-form').style.display = 'block';
            document.getElementById('main-panel').style.display = 'none';
        }
        
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            
            // Remove active class from nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').style.display = 'block';
            event.target.classList.add('active');
        }
        
        async function loadDashboard() {
            try {
                const response = await fetch('/api/stats', {
                    headers: {
                        'Authorization': 'Bearer ' + authToken
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    document.getElementById('bot-status').textContent = data.bot_status || 'Offline';
                    document.getElementById('uptime').textContent = Math.floor((data.uptime || 0) / 3600);
                    document.getElementById('messages').textContent = data.messages_processed || 0;
                    document.getElementById('servers').textContent = data.server_count || 0;
                }
            } catch (error) {
                console.error('Failed to load dashboard data');
            }
        }
        
        // Auto-refresh dashboard every 30 seconds
        setInterval(() => {
            if (authToken && document.getElementById('main-panel').style.display !== 'none') {
                loadDashboard();
            }
        }, 30000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("SynapseChat Web Panel - Self-Hosted Version")
    print("Initializing admin account...")
    
    # Initialize admin user on startup
    if initialize_admin():
        print("Panel ready!")
        print("Access: http://localhost:5000")
        print("Login: Joeyxpk / Sept161997!")
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        print("Failed to initialize admin account")
        exit(1)