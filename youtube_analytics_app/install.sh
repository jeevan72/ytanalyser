#!/bin/bash
# YouTube Behavioral Analytics Auto-Installer for Raspberry Pi
# Sets up Gunicorn systemd daemon, Nginx reverse proxy on port 6767, and configures Git.

# Exit immediately if a command exits with a non-zero status
set -e

echo "============================================="
echo "Starting YouTube Analytics Auto-Installer..."
echo "============================================="

# Get absolute path to the directory containing this script
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
CURRENT_USER=$(whoami)

echo "Installation Directory: $INSTALL_DIR"
echo "System User:             $CURRENT_USER"

# 1. Update and install dependencies
echo "Installing system packages (Python, pip, venv, Git, Nginx)..."
sudo apt update
sudo apt install -y python3-pip python3-venv git nginx

# 2. Setup python virtual environment
echo "Setting up Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install gunicorn

# 3. Configure Git repository (git init fallback)
echo "Checking Git repository status..."
if [ ! -d ".git" ]; then
    echo "No Git repository found. Initializing Git repo..."
    git init
    # Configure generic local credentials for Pi installer if global configs do not exist
    if ! git config --global user.email >/dev/null 2>&1; then
        git config user.email "installer@raspberrypi.local"
        git config user.name "Raspberry Pi Installer"
    fi
    git checkout -b main || git checkout -b master
    git add .
    git commit -m "Initial commit from Raspberry Pi Auto-Installer"
    echo "Local Git repository successfully initialized."
else
    echo "Git repository already initialized."
fi

# 4. Create systemd service
echo "Configuring systemd service..."
sudo tee /etc/systemd/system/youtube_analytics.service << EOF
[Unit]
Description=Gunicorn daemon serving YouTube Behavioral Analytics
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --workers 3 --timeout 120 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
EOF

# 5. Configure Nginx
echo "Configuring Nginx reverse proxy on port 6767..."
sudo tee /etc/nginx/sites-available/youtube_analytics << 'EOF'
server {
    listen 6767 default_server;
    listen [::]:6767 default_server;
    server_name _;

    # Support uploading large takeout zip archives
    client_max_body_size 150M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase proxy timeouts for heavy data processing
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
EOF

# Enable the Nginx site configuration
echo "Activating Nginx site configuration..."
sudo ln -sf /etc/nginx/sites-available/youtube_analytics /etc/nginx/sites-enabled/

# Remove the default Nginx site configuration if it exists to avoid conflicts
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "Disabling default Nginx site configuration..."
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# 6. Reload and restart services
echo "Starting systemd and Nginx services..."
sudo systemctl daemon-reload
sudo systemctl enable youtube_analytics.service
sudo systemctl restart youtube_analytics.service
sudo systemctl restart nginx

echo "============================================="
echo "Installation Complete!"
echo "The application is now running on port 6767"
echo "Access it on your local network at http://<pi-ip>:6767"
echo "============================================="

# Self-deletion
echo "Cleaning up installer script..."
rm -- "$0"
