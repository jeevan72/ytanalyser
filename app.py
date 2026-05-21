import os
import uuid
import re
import zipfile
import json
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, session, jsonify, send_from_directory

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
USERS_DIR = os.path.join(DATA_DIR, 'users')
os.makedirs(USERS_DIR, exist_ok=True)

# Limit uploads to 150MB
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024

# Timezone offsets map
tz_offsets = {
    'IST': '+0530', 'EDT': '-0400', 'EST': '-0500',
    'PDT': '-0700', 'PST': '-0800', 'UTC': '+0000',
    'GMT': '+0000', 'BST': '+0100', 'CEST': '+0200',
    'CET': '+0100'
}

def parse_tz_datetime(s):
    if pd.isna(s) or not isinstance(s, str):
        return pd.NaT
    parts = s.strip().split()
    if len(parts) < 2:
        return pd.NaT
    tz = parts[-1]
    if tz in tz_offsets:
        offset = tz_offsets[tz]
        s_clean = " ".join(parts[:-1]) + " " + offset
        try:
            return pd.to_datetime(s_clean, format='%d %b %Y, %H:%M:%S %z', errors='coerce')
        except Exception:
            pass
    return pd.to_datetime(s, errors='coerce')

def parse_watch_regex(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    cell_re = re.compile(r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">([\s\S]*?)</div>')
    link_re = re.compile(r'<a href="([^"]+)">([\s\S]*?)</a>')
    
    records = []
    cells = cell_re.findall(html)
    
    for cell in cells:
        if "Watched" not in cell:
            continue
            
        links = link_re.findall(cell)
        clean_links = []
        for url, text in links:
            text_clean = re.sub(r'<[^>]+>', '', text).strip()
            clean_links.append((url, text_clean))
            
        video_title = None
        video_url = None
        channel_name = None
        channel_url = None
        
        if len(clean_links) >= 1:
            video_url, video_title = clean_links[0]
        if len(clean_links) >= 2:
            channel_url, channel_name = clean_links[1]
            
        parts = [p.strip() for p in re.split(r'<br/?>', cell) if p.strip()]
        timestamp = None
        if len(parts) >= 1:
            timestamp = re.sub(r'<[^>]+>', '', parts[-1]).strip()
            if "Watched" in timestamp or len(timestamp) < 5:
                timestamp = None
                
        records.append({
            'title': video_title,
            'url': video_url,
            'channel': channel_name or "Unknown",
            'channel_url': channel_url or "",
            'raw_timestamp': timestamp
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df['timestamp'] = df['raw_timestamp'].apply(parse_tz_datetime)
        df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df

def parse_search_regex(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
        
    cell_re = re.compile(r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">([\s\S]*?)</div>')
    link_re = re.compile(r'<a href="([^"]+)">([\s\S]*?)</a>')
    
    records = []
    cells = cell_re.findall(html)
    
    for cell in cells:
        if "Searched for" not in cell:
            continue
            
        links = link_re.findall(cell)
        query = None
        query_url = None
        
        if len(links) >= 1:
            query_url, query_raw = links[0]
            query = re.sub(r'<[^>]+>', '', query_raw).strip()
            
        parts = [p.strip() for p in re.split(r'<br/?>', cell) if p.strip()]
        timestamp = None
        if len(parts) >= 1:
            timestamp = re.sub(r'<[^>]+>', '', parts[-1]).strip()
            if "Searched" in timestamp or len(timestamp) < 5:
                timestamp = None
                
        records.append({
            'query': query,
            'query_url': query_url,
            'raw_timestamp': timestamp
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df['timestamp'] = df['raw_timestamp'].apply(parse_tz_datetime)
        df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df

def calculate_hhi(group):
    shares = group.value_counts(normalize=True)
    return (shares ** 2).sum() * 10000

def get_user_dir():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    user_dir = os.path.join(USERS_DIR, session['user_id'])
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def analyze_user_data(user_dir):
    watch_path = os.path.join(user_dir, "watch_history.csv")
    search_path = os.path.join(user_dir, "search_history.csv")
    subs_path = os.path.join(user_dir, "subscriptions.csv")
    
    if not os.path.exists(watch_path):
        return None
        
    watch_df = pd.read_csv(watch_path)
    watch_df['timestamp'] = pd.to_datetime(watch_df['timestamp'])
    
    search_df = pd.DataFrame()
    if os.path.exists(search_path):
        search_df = pd.read_csv(search_path)
        search_df['timestamp'] = pd.to_datetime(search_df['timestamp'])
        
    subs_df = pd.DataFrame()
    if os.path.exists(subs_path):
        subs_df = pd.read_csv(subs_path)
        
    # Feature engineering
    watch_df['year'] = watch_df['timestamp'].dt.year
    watch_df['month'] = watch_df['timestamp'].dt.month
    watch_df['day_of_week'] = watch_df['timestamp'].dt.day_name()
    watch_df['hour'] = watch_df['timestamp'].dt.hour
    watch_df['date'] = watch_df['timestamp'].dt.date
    
    # 1. Advanced Metrics: Comfort Channels (Engagement Rank)
    # Ranks channels based on (Total views * 0.7) + (Autoplay repeat counts * 0.3)
    watch_df['prev_channel'] = watch_df['channel'].shift(1)
    watch_df['is_loop'] = (watch_df['channel'] == watch_df['prev_channel']).astype(int)
    
    channel_stats = watch_df.groupby('channel').agg(
        views=('channel', 'count'),
        loops=('is_loop', 'sum')
    ).reset_index()
    
    channel_stats['comfort_score'] = (channel_stats['views'] * 0.7) + (channel_stats['loops'] * 0.3 * 10)
    top_comfort = channel_stats.sort_values(by='comfort_score', ascending=False).head(10)
    
    # 2. Search Intent Classification (NLP fallback rules)
    search_intent = {'Informational': 0, 'Entertainment/Music': 0, 'Navigational': 0, 'Other': 0}
    if not search_df.empty:
        intent_rules = {
            'Informational': ['how', 'why', 'tutorial', 'python', 'code', 'learn', 'course', 'explain', 'vs', 'science', 'what'],
            'Entertainment/Music': ['song', 'music', 'lofi', 'funny', 'comedy', 'trailer', 'gaming', 'minecraft', 'play', 'movie'],
            'Navigational': ['channel', 'vlog', 'shorts', 'youtube', 'neon man', 'goswami', 'agamy']
        }
        for q in search_df['query'].dropna():
            q_lower = str(q).lower()
            classified = False
            for intent, keywords in intent_rules.items():
                if any(kw in q_lower for kw in keywords):
                    search_intent[intent] += 1
                    classified = True
                    break
            if not classified:
                search_intent['Other'] += 1
                
    # 3. Autoplay rabbit holes
    loop_percentage = watch_df['is_loop'].mean() * 100
    
    # 4. Binge Sessions (Gap < 20 mins)
    watch_df['time_gap'] = watch_df['timestamp'].diff().dt.total_seconds().fillna(0)
    watch_df['new_session'] = (watch_df['time_gap'] > 1200).astype(int)
    watch_df['session_id'] = watch_df['new_session'].cumsum()
    session_sizes = watch_df.groupby('session_id').size()
    binge_sessions = session_sizes[session_sizes >= 5]
    total_sessions = len(session_sizes)
    binge_count = len(binge_sessions)
    
    # 5. Binge Burnout Alert
    daily_watch = watch_df.groupby('date').size()
    burnout_days = len(daily_watch[daily_watch >= 300]) # >300 videos watched in a day is flagged
    
    # Subscriptions overlap
    subs_overlap_pct = 0.0
    subs_watched_pct = 0.0
    if not subs_df.empty:
        title_col = None
        for col in subs_df.columns:
            if col.lower() in ['channel title', 'channel_title']:
                title_col = col
                break
        if title_col:
            subs_channels = set(subs_df[title_col].dropna().str.lower().str.strip())
            watched_channels = set(watch_df['channel'].dropna().str.lower().str.strip())
            overlap = watched_channels.intersection(subs_channels)
            subs_overlap_pct = (len(overlap) / len(watched_channels)) * 100 if len(watched_channels) > 0 else 0
            watch_df['is_subscribed'] = watch_df['channel'].dropna().str.lower().str.strip().isin(subs_channels)
            subs_watched_pct = watch_df['is_subscribed'].mean() * 100

    # Categorization distribution
    categories = {
        'Technology & AI': ['tech', 'ai', 'python', 'programming', 'code', 'software', 'hardware', 'app', 'developer', 'chatgpt'],
        'Gaming': ['game', 'play', 'walkthrough', 'minecraft', 'gta', 'xbox', 'playstation', 'nintendo'],
        'Finance': ['crypto', 'invest', 'money', 'stock', 'finance', 'economy', 'wealth'],
        'Education': ['how to', 'tutorial', 'learn', 'course', 'science', 'history', 'explain'],
        'Entertainment': ['funny', 'comedy', 'movie', 'trailer', 'vlog', 'prank', 'react'],
        'Music': ['music', 'song', 'cover', 'live', 'album', 'remix', 'dj']
    }
    
    def classify_title(title):
        if pd.isna(title) or not isinstance(title, str):
            return 'Other'
        t_lower = title.lower()
        for cat, keywords in categories.items():
            if any(kw in t_lower for kw in keywords):
                return cat
        return 'Other'
        
    watch_df['category'] = watch_df['title'].apply(classify_title)
    category_counts = watch_df['category'].value_counts().to_dict()

    # Compile JSON summary
    summary = {
        'total_watched': len(watch_df),
        'total_searches': len(search_df),
        'unique_channels': watch_df['channel'].nunique(),
        'avg_views_per_day': float(watch_df.groupby('date').size().mean()) if len(watch_df) > 0 else 0.0,
        'loop_percentage': float(loop_percentage),
        'total_sessions': int(total_sessions),
        'binge_sessions': int(binge_count),
        'burnout_alert_days': int(burnout_days),
        'subs_overlap_pct': float(subs_overlap_pct),
        'subs_watched_pct': float(subs_watched_pct),
        'top_channels': top_comfort[['channel', 'views', 'loops', 'comfort_score']].to_dict(orient='records'),
        'category_counts': category_counts,
        'search_intents': search_intent
    }
    
    with open(os.path.join(user_dir, "analysis_summary.json"), "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
        
    return summary

@app.route('/')
def index():
    user_dir = get_user_dir()
    summary_path = os.path.join(user_dir, "analysis_summary.json")
    has_data = os.path.exists(summary_path)
    return render_template('index.html', has_data=has_data)

@app.route('/upload', methods=['POST'])
def upload_file():
    user_dir = get_user_dir()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400
        
    if file and file.filename.endswith('.zip'):
        zip_path = os.path.join(user_dir, 'takeout.zip')
        file.save(zip_path)
        
        # Extract files in user directory
        extract_path = os.path.join(user_dir, 'extracted')
        os.makedirs(extract_path, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except Exception as e:
            return jsonify({'error': f'Failed to extract zip: {str(e)}'}), 500
            
        # Locate files inside extracted directory (largest size priority)
        watch_files = []
        search_files = []
        subs_files = []
        
        for root, dirs, files in os.walk(extract_path):
            for f in files:
                full_path = os.path.join(root, f)
                if f == 'watch-history.html':
                    watch_files.append(full_path)
                elif f == 'search-history.html':
                    search_files.append(full_path)
                elif f == 'subscriptions.csv':
                    subs_files.append(full_path)
                    
        # Sort by size to pick the real main files first
        if watch_files:
            watch_files = sorted(watch_files, key=os.path.getsize, reverse=True)
            try:
                watch_df = parse_watch_regex(watch_files[0])
                watch_df.to_csv(os.path.join(user_dir, "watch_history.csv"), index=False, encoding='utf-8')
            except Exception as e:
                print("Error parsing watch history:", e)
                
        if search_files:
            search_files = sorted(search_files, key=os.path.getsize, reverse=True)
            try:
                search_df = parse_search_regex(search_files[0])
                search_df.to_csv(os.path.join(user_dir, "search_history.csv"), index=False, encoding='utf-8')
            except Exception as e:
                print("Error parsing search history:", e)
                
        if subs_files:
            subs_files = sorted(subs_files, key=os.path.getsize, reverse=True)
            try:
                # Copy subscriptions.csv to user_dir
                import shutil
                shutil.copyfile(subs_files[0], os.path.join(user_dir, "subscriptions.csv"))
            except Exception as e:
                print("Error copying subscriptions:", e)
                
        # Perform analytics
        try:
            summary = analyze_user_data(user_dir)
            if summary:
                return jsonify({'success': 'Data processed successfully', 'summary': summary})
            else:
                return jsonify({'error': 'Failed to analyze data: Check if zip contains watch-history.html'}), 500
        except Exception as e:
            return jsonify({'error': f'Failed during data analysis: {str(e)}'}), 500
            
    return jsonify({'error': 'Allowed file types are .zip'}), 400

@app.route('/api/stats')
def get_stats():
    user_dir = get_user_dir()
    summary_path = os.path.join(user_dir, "analysis_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'No data found. Please upload Takeout zip file.'}), 404

@app.route('/api/charts')
def get_chart_data():
    user_dir = get_user_dir()
    watch_path = os.path.join(user_dir, "watch_history.csv")
    search_path = os.path.join(user_dir, "search_history.csv")
    
    if not os.path.exists(watch_path):
        return jsonify({'error': 'No data available'}), 404
        
    watch_df = pd.read_csv(watch_path)
    watch_df['timestamp'] = pd.to_datetime(watch_df['timestamp'])
    
    # 1. Volume over time (Monthly aggregation)
    monthly_counts = watch_df.groupby(watch_df['timestamp'].dt.to_period('M')).size()
    monthly_labels = [str(p) for p in monthly_counts.index]
    monthly_values = monthly_counts.values.tolist()
    
    # 2. Circadian heatmap (Day of Week vs Hour of Day)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_raw = watch_df.groupby([watch_df['timestamp'].dt.day_name(), watch_df['timestamp'].dt.hour]).size().unstack(fill_value=0)
    heatmap_raw = heatmap_raw.reindex(days_order).fillna(0)
    
    heatmap_data = []
    for day_idx, day_name in enumerate(days_order):
        for hour in range(24):
            val = int(heatmap_raw.loc[day_name, hour]) if hour in heatmap_raw.columns else 0
            heatmap_data.append({'x': hour, 'y': day_idx, 'v': val})
            
    # 3. Novelty ratio (Exploration score) over time
    watch_df['is_new_channel'] = ~watch_df.duplicated(subset=['channel'])
    novelty_monthly = watch_df.groupby(watch_df['timestamp'].dt.to_period('M'))['is_new_channel'].mean()
    novelty_labels = [str(p) for p in novelty_monthly.index]
    novelty_values = novelty_monthly.values.tolist()
    
    # 4. HHI concentration over time
    hhi_monthly = watch_df.groupby(watch_df['timestamp'].dt.to_period('M'))['channel'].apply(calculate_hhi)
    hhi_labels = [str(p) for p in hhi_monthly.index]
    hhi_values = hhi_monthly.values.tolist()
    
    # 5. Search Top Words (if available)
    search_words_labels = []
    search_words_values = []
    if os.path.exists(search_path):
        search_df = pd.read_csv(search_path)
        from collections import Counter
        all_words = []
        stopwords = {'how', 'why', 'what', 'to', 'in', 'the', 'of', 'and', 'a', 'is', 'for', 'on', 'with', 'from', 'at', 'by', 'an', 'this', 'that', 'it', 'my'}
        for q in search_df['query'].dropna():
            words = [w.lower().strip() for w in re.split(r'\s+', str(q)) if w.strip()]
            for w in words:
                w_clean = re.sub(r'[^\w]', '', w)
                if w_clean and w_clean not in stopwords:
                    all_words.append(w_clean)
        top_words = Counter(all_words).most_common(20)
        search_words_labels = [w[0] for w in top_words]
        search_words_values = [w[1] for w in top_words]

    return jsonify({
        'volume': {'labels': monthly_labels, 'values': monthly_values},
        'circadian': {'days': days_order, 'data': heatmap_data},
        'exploration': {'labels': novelty_labels, 'values': novelty_values},
        'hhi': {'labels': hhi_labels, 'values': hhi_values},
        'search_words': {'labels': search_words_labels, 'values': search_words_values}
    })

if __name__ == '__main__':
    # Hosted locally, open to network access for Raspberry Pi testing
    app.run(host='0.0.0.0', port=5000, debug=True)
