# YouTube Behavioral & Recommendation Audit Dashboard

A premium, local-first web application designed to run on a **Raspberry Pi 4 (8GB)** running **Raspberry Pi OS**. This application parses Google Takeout watch and search histories to provide deep behavioral insights, recommendation system audits (diversity, loop frequencies, comfort ranks), and search pattern NLP classification.

---

## Key Privacy Features
- **100% Offline Processing:** All data is parsed, stored, and analyzed locally on the device.
- **Zero Cloud Leakages:** No metrics, watch histories, or search intents are transmitted out of your local network.
- **Session-Based Isolation:** Each user session stores its data in an isolated directory under `data/users/<session_id>/` for simple cleanups and debugging.

---

## Tech Stack
- **Backend:** Flask, Pandas, NumPy, Scikit-learn (NLP rule-based intent parsing)
- **Frontend:** Vanilla CSS (Glassmorphism dark theme), HTML5, JavaScript (AJAX upload with progress tracking)
- **Charts:** Chart.js (client-side rendering for optimal Raspberry Pi resource allocation)

---

## Raspberry Pi Installation

### Method 1: Auto-Installation (Recommended)

To install all dependencies, configure the background service, set up Nginx to serve the app on port **6767**, and automatically clean up the installer:

1. Clone or copy this project folder to your Raspberry Pi user directory (e.g. `/home/pi/youtube_analytics_app`).
2. Open your terminal, navigate to the folder, make the installer executable, and run it:

```bash
cd /home/pi/youtube_analytics_app
chmod +x install.sh
./install.sh
```

*Note: The script requires sudo privileges to install system packages and configure systemd/Nginx. Once successful, `install.sh` will automatically delete itself.*

---

### Method 2: Manual Installation

If you prefer to configure the steps manually:

#### 1. Setup Virtual Environment & Dependencies
```bash
cd /home/pi/youtube_analytics_app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### 2. Configure systemd Service
Create a service file:
```bash
sudo nano /etc/systemd/system/youtube_analytics.service
```
Paste this configuration:
```ini
[Unit]
Description=Gunicorn daemon serving YouTube Behavioral Analytics
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/youtube_analytics_app
Environment="PATH=/home/pi/youtube_analytics_app/venv/bin"
ExecStart=/home/pi/youtube_analytics_app/venv/bin/gunicorn --workers 3 --timeout 120 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable youtube_analytics.service
sudo systemctl start youtube_analytics.service
```

#### 3. Configure Nginx Reverse Proxy (Port 6767)
Install Nginx:
```bash
sudo apt update && sudo apt install nginx -y
```

Modify the Nginx configurations:
```bash
sudo nano /etc/nginx/sites-available/youtube_analytics
```
Paste the following, making sure the client upload limit is `150M` and Nginx listens on port `6767`:
```nginx
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
```

Enable config and restart Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/youtube_analytics /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
```

---

## Verification
Once running, the application is accessible on your local network at:
`http://<your-raspberry-pi-ip>:6767`

---

## Directory Structure
```
youtube_analytics_app/
├── app.py                # Flask application core, parsing regexes & API endpoints (Port 6767 default)
├── requirements.txt      # Dependency listing
├── .gitignore            # Data/cache exclusion rules
├── README.md             # This document
├── install.sh            # Auto-installer shell script (deletes itself after execution)
├── templates/
│   └── index.html        # Glassmorphic layout structure
└── static/
    ├── css/
    │   └── style.css     # Premium styling, animations & neon variables
    └── js/
        └── dashboard.js  # File ingestion AJAX progress, dynamic table binding & charts
```
