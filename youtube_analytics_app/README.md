# YouTube Behavioral & Recommendation Audit Dashboard

A premium, local-first web application designed to run on a **Raspberry Pi 4 (8GB)** running **Raspberry Pi OS**. This application parses Google Takeout watch and search histories to provide deep behavioral insights, recommendation system audits (diversity, loop frequencies, comfort ranks), and search pattern NLP classification.

---

## Core Features & Analytical Insights

- **Multi-Archive Merging Ingestion:** Seamlessly upload multiple split Google Takeout `.zip` archives at once. The backend extracts, merges, deduplicates (using title, channel, and timestamps), and sorts the records chronologically.
- **Robust Client-Side User Tracking:** Utilizes persistent browser `localStorage` user tokens to bypass browser sandbox cookie blocks (common when self-hosting web apps on raw Raspberry Pi local IP addresses).
- **100% Offline Compatibility:** The dashboard is built with offline-first environments in mind. If the Raspberry Pi lacks internet access, the frontend detects missing external dependencies (like Chart.js) and falls back to clean, non-blocking placeholder messages without crashing JavaScript execution.
- **Key Metrics & Temporal Habits:** Parses total videos watched, estimated watch hours (20-minute active session aggregation), unique creators, average daily watch volume, and late-night binge ratios (11 PM - 4 AM).
- **Longest Binge Sitting Record:** Tracks your single longest uninterrupted watching streak, displaying duration, date, count, and the dominant channel watched.
- **Nostalgia Channels:** Highlights forgotten favorites—creators you watched heavily in the past (5+ views) but haven't watched once in the last 6 months.
- **Ghost Subscriptions Audit:** Compares your `subscriptions.csv` with your actual watch history to identify channels you are subscribed to but have never actually watched.
- **Algorithmic Recommendation Audits:** Calculates comfort autoplay loop frequencies (same-channel plays) and Channel Concentration indices (blended HHI score).
- **Search Focus Index:** Correlates search queries starting educational/technical learning paths with subsequent 30-minute content categories watched to score focus vs. distraction.

---

## Key Privacy Features
- **100% Offline Processing:** All data is parsed, stored, and analyzed locally on the device.
- **Zero Cloud Leakages:** No metrics, watch histories, or search intents are transmitted out of your local network.
- **Local User Storage Isolation:** Each user's uploads, parsed CSVs, and computed summaries are stored inside a dedicated directory under `data/users/<user_id>/` for simple auditing and manual purging.

---

## Tech Stack
- **Backend:** Flask, Pandas, NumPy
- **Frontend:** Vanilla CSS (Glassmorphism dark theme), HTML5, JavaScript (AJAX upload with progress tracking & checklist animations)
- **Charts:** Chart.js (client-side rendering for optimal Raspberry Pi resource allocation, with offline canvas fallbacks)

---

## Raspberry Pi Installation

### Method 1: Auto-Installation (Recommended)

To install all dependencies, configure the background service, set up Nginx to serve the app on port **6767**, and automatically clean up the installer:

1. **Clone the Repository** to your Raspberry Pi user directory (e.g. `/home/pi/youtube_analytics_app`):
   ```bash
   git clone https://github.com/jeevan72/ytanalyser.git /home/pi/youtube_analytics_app
   ```
   *(If you did not clone it and instead copied files manually, run `git init` inside the folder before installing).*

2. **Run the Installer:** Navigate to the folder, make the installer executable, and run it:
   ```bash
   cd /home/pi/youtube_analytics_app
   chmod +x install.sh
   ./install.sh
   ```

*Note: The script requires sudo privileges to install system packages and configure systemd/Nginx. Once successful, `install.sh` will automatically delete itself.*

---

### Method 2: Manual Installation

If you prefer to configure the steps manually:

#### 1. Setup Git & Clone
```bash
# Install git if missing
sudo apt update && sudo apt install git -y

# Clone repo
git clone https://github.com/jeevan72/ytanalyser.git /home/pi/youtube_analytics_app
cd /home/pi/youtube_analytics_app

# (Optional fallback if copied files manually)
# git init
```

#### 2. Setup Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### 3. Configure systemd Service
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

#### 4. Configure Nginx Reverse Proxy (Port 6767)
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
