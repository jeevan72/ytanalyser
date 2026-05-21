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
   cd /home/pi/youtube_analytics_app/youtube_analytics_app
   chmod +x install.sh
   ./install.sh
   ```

*Note: The script requires sudo privileges to install system packages and configure systemd/Nginx. Once successful, `install.sh` will automatically delete itself.*

---

## Directory Structure
```
ytanalyser/ (Git Root)
├── README.md                 # This document (Root repository description)
├── analyze_data.py           # Standalone analysis script
├── parse_data.py             # Standalone watch/search history parsing script
├── youtube_analytics_app/    # Main web application folder
│   ├── app.py                # Flask application core (Port 6767 default)
│   ├── requirements.txt      # Dependency listing
│   ├── install.sh            # Auto-installer shell script (deletes itself after execution)
│   ├── README.md             # Sub-directory README copy
│   ├── templates/
│   │   └── index.html        # Glassmorphic layout structure
│   └── static/
│       ├── css/
│       │   └── style.css     # Premium styling, animations & neon variables
│       └── js/
│           └── dashboard.js  # File ingestion AJAX progress, dynamic table binding & charts
```
