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

## Installation on Raspberry Pi

### 1. Clone & Setup Directory
Copy this project folder to your Raspberry Pi user directory (e.g. `/home/pi/youtube_analytics_app`).

```bash
cd /home/pi/youtube_analytics_app
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
# Gunicorn is needed for production hosting
pip install gunicorn
```

### 4. Running the Development Server
```bash
python app.py
```
By default, the server runs on port `5000` and binds to `0.0.0.0` so it can be accessed within your local network (e.g., `http://<pi-ip-address>:5000`).

---

## Production Deployment (Recommended)

To run the application continuously as a background service on startup and handle larger file uploads cleanly, set up Gunicorn, systemd, and Nginx.

### 1. Set Up systemd Service
Create a systemd service file to manage the Flask application process.

```bash
sudo nano /etc/systemd/system/youtube_analytics.service
```

Paste the following configuration:

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
sudo systemctl status youtube_analytics.service
```

### 2. Install and Configure Nginx as a Reverse Proxy
Nginx acts as a reverse proxy, managing network traffic, and buffering file uploads.

```bash
sudo apt update
sudo apt install nginx -y
```

Modify the default Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/default
```

Replace the content of the `server` block with the following, making sure `client_max_body_size` is set to `150M` to support large Google Takeout zip files:

```nginx
server {
    listen 80;
    server_name youtube-analytics.local;

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

Test and reload Nginx:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

Now, the application is accessible on your local network at `http://<raspberry-pi-ip>/` or via `http://youtube-analytics.local/` (if using local DNS / mdns multicast).

---

## Directory Structure
```
youtube_analytics_app/
├── app.py                # Flask application core, parsing regexes & API endpoints
├── requirements.txt      # Dependency listing
├── .gitignore            # Data/cache exclusion rules
├── README.md             # This document
├── templates/
│   └── index.html        # Glassmorphic layout structure
└── static/
    ├── css/
    │   └── style.css     # Premium styling, animations & neon variables
    └── js/
        └── dashboard.js  # File ingestion AJAX progress, dynamic table binding & charts
```
