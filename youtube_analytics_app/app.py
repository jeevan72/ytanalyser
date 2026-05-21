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

# Configure directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
USERS_DIR = os.path.join(DATA_DIR, 'users')
os.makedirs(USERS_DIR, exist_ok=True)

# Persistent Secret key to prevent session resets on code changes
secret_key_file = os.path.join(DATA_DIR, 'secret_key.bin')
if os.path.exists(secret_key_file):
    try:
        with open(secret_key_file, 'rb') as f:
            app.secret_key = f.read()
    except Exception:
        key = os.urandom(24)
        with open(secret_key_file, 'wb') as f:
            f.write(key)
        app.secret_key = key
else:
    key = os.urandom(24)
    try:
        with open(secret_key_file, 'wb') as f:
            f.write(key)
    except Exception:
        pass
    app.secret_key = key

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

def get_user_id():
    user_id = request.args.get('user_id')
    if not user_id:
        user_id = request.form.get('user_id')
    if not user_id:
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        user_id = session['user_id']
    return user_id

def get_user_dir():
    user_id = get_user_id()
    user_dir = os.path.join(USERS_DIR, user_id)
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
    
    # 1. Subscriptions map
    subs_channels = set()
    title_col = None
    if not subs_df.empty:
        for col in subs_df.columns:
            if col.lower() in ['channel title', 'channel_title']:
                title_col = col
                break
        if title_col:
            subs_channels = set(subs_df[title_col].dropna().str.lower().str.strip())
            
    # 2. Watch hours, Start & End Dates
    start_date_str = "N/A"
    end_date_str = "N/A"
    estimated_hours = 0.0
    if not watch_df.empty:
        start_date_str = watch_df['timestamp'].min().strftime('%d %b %Y')
        end_date_str = watch_df['timestamp'].max().strftime('%d %b %Y')
        
        # Calculate session-based active watch time
        watch_df['time_gap'] = watch_df['timestamp'].diff().dt.total_seconds().fillna(0)
        watch_df['new_session'] = (watch_df['time_gap'] > 1200).astype(int)
        watch_df['session_id'] = watch_df['new_session'].cumsum()
        
        # For each session: duration is (max_time - min_time) + 600 seconds (10 mins for trailing video)
        session_durations = watch_df.groupby('session_id')['timestamp'].agg(['min', 'max'])
        session_times = (session_durations['max'] - session_durations['min']).dt.total_seconds() + 600
        total_watch_seconds = session_times.sum()
        estimated_hours = round(total_watch_seconds / 3600, 1)
        
    # 3. Comfort Channels (Engagement Rank)
    watch_df['prev_channel'] = watch_df['channel'].shift(1)
    watch_df['is_loop'] = (watch_df['channel'] == watch_df['prev_channel']).astype(int)
    
    channel_stats = watch_df.groupby('channel').agg(
        views=('channel', 'count'),
        loops=('is_loop', 'sum')
    ).reset_index()
    
    channel_urls = watch_df.groupby('channel')['channel_url'].first().to_dict()
    channel_stats['channel_url'] = channel_stats['channel'].map(channel_urls)
    channel_stats['comfort_score'] = (channel_stats['views'] * 0.7) + (channel_stats['loops'] * 0.3 * 10)
    top_comfort = channel_stats.sort_values(by='comfort_score', ascending=False).head(10)
    
    top_comfort_list = []
    for idx, row in top_comfort.iterrows():
        ch_name = row['channel']
        ch_lower = str(ch_name).lower().strip()
        is_sub = ch_lower in subs_channels
        top_comfort_list.append({
            'channel': ch_name,
            'views': int(row['views']),
            'loops': int(row['loops']),
            'comfort_score': float(row['comfort_score']),
            'channel_url': row['channel_url'] or f"https://www.youtube.com/results?search_query={ch_name}",
            'is_subscribed': bool(is_sub)
        })
        
    # 4. Top 5 Repeat-Watched Videos
    video_stats = watch_df.groupby(['title', 'url', 'channel', 'channel_url']).size().reset_index(name='watch_count')
    top_videos = video_stats.sort_values(by='watch_count', ascending=False).head(5)
    
    top_videos_list = []
    for idx, row in top_videos.iterrows():
        ch_name = row['channel']
        ch_lower = str(ch_name).lower().strip()
        is_sub = ch_lower in subs_channels
        top_videos_list.append({
            'title': row['title'],
            'url': row['url'],
            'channel': ch_name,
            'channel_url': row['channel_url'] or f"https://www.youtube.com/results?search_query={ch_name}",
            'watch_count': int(row['watch_count']),
            'is_subscribed': bool(is_sub)
        })
        
    # 5. Search Intent Classification (NLP fallback rules)
    search_intent = {'Informational': 0, 'Entertainment/Music': 0, 'Navigational': 0, 'Other': 0}
    if not search_df.empty:
        intent_rules = {
            'Informational': ['how', 'why', 'tutorial', 'python', 'code', 'learn', 'course', 'explain', 'vs', 'science', 'what', 'programming', 'github', 'install', 'setup'],
            'Entertainment/Music': ['song', 'music', 'lofi', 'funny', 'comedy', 'trailer', 'gaming', 'minecraft', 'play', 'movie', 'show', 'series', 'meme'],
            'Navigational': ['channel', 'vlog', 'shorts', 'youtube', 'neon man', 'goswami', 'agamy', 'instagram', 'facebook', 'twitter']
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
                
    # 6. Autoplay rabbit holes
    loop_percentage = watch_df['is_loop'].mean() * 100 if len(watch_df) > 0 else 0.0
    
    # 7. Binge Sessions (Gap < 20 mins)
    session_sizes = watch_df.groupby('session_id').size()
    binge_sessions = session_sizes[session_sizes >= 5]
    total_sessions = len(session_sizes)
    binge_count = len(binge_sessions)
    
    # 8. Binge Burnout Alert
    daily_watch = watch_df.groupby('date').size()
    burnout_days = len(daily_watch[daily_watch >= 300])
    
    # 9. Subscriptions overlap & penetration
    subs_overlap_pct = 0.0
    subs_watched_pct = 0.0
    if not subs_df.empty and title_col:
        watched_channels = set(watch_df['channel'].dropna().str.lower().str.strip())
        overlap = watched_channels.intersection(subs_channels)
        subs_overlap_pct = (len(overlap) / len(watched_channels)) * 100 if len(watched_channels) > 0 else 0
        watch_df['is_subscribed'] = watch_df['channel'].dropna().str.lower().str.strip().isin(subs_channels)
        subs_watched_pct = watch_df['is_subscribed'].mean() * 100
        
    # 10. Ghost Subscriptions (Subscribed but never watched)
    ghost_subscriptions = []
    if not subs_df.empty and title_col:
        watched_channels_lower = set(watch_df['channel'].dropna().str.lower().str.strip())
        url_col = None
        for col in subs_df.columns:
            if col.lower() in ['channel url', 'channel_url']:
                url_col = col
                break
        for idx, row in subs_df.iterrows():
            ch_name = row[title_col]
            if pd.isna(ch_name):
                continue
            ch_lower = str(ch_name).lower().strip()
            if ch_lower not in watched_channels_lower:
                ch_url = row[url_col] if url_col and not pd.isna(row[url_col]) else f"https://www.youtube.com/results?search_query={ch_name}"
                ghost_subscriptions.append({
                    'channel': ch_name,
                    'channel_url': ch_url
                })
    ghost_count = len(ghost_subscriptions)
    ghost_subscriptions = ghost_subscriptions[:20]
    
    # 11. Late Night Binging Index (%)
    late_night_pct = 0.0
    if not watch_df.empty:
        late_night_views = watch_df[watch_df['hour'].isin([23, 0, 1, 2, 3, 4])]
        late_night_pct = round((len(late_night_views) / len(watch_df)) * 100, 1)
        
    # 12. YoY Activity Trend
    yoy_trend = {}
    if not watch_df.empty:
        yoy_counts = watch_df.groupby('year').size().to_dict()
        yoy_trend = {str(k): int(v) for k, v in yoy_counts.items()}
        
    # 13. Longest Binge Session Record
    longest_binge = {
        'date': 'N/A',
        'duration_mins': 0,
        'video_count': 0,
        'primary_channel': 'Unknown',
        'primary_channel_url': ''
    }
    if not watch_df.empty and 'session_id' in watch_df.columns and not session_sizes.empty:
        max_sess_id = session_sizes.idxmax()
        max_sess_count = int(session_sizes.max())
        sess_df = watch_df[watch_df['session_id'] == max_sess_id]
        if not sess_df.empty:
            sess_min_t = sess_df['timestamp'].min()
            sess_max_t = sess_df['timestamp'].max()
            duration_mins = int(round(((sess_max_t - sess_min_t).total_seconds() + 600) / 60))
            prim_channel = sess_df['channel'].value_counts().idxmax()
            prim_ch_url_series = sess_df[sess_df['channel'] == prim_channel]['channel_url'].dropna()
            prim_ch_url = prim_ch_url_series.iloc[0] if not prim_ch_url_series.empty else ""
            if not prim_ch_url:
                prim_ch_url = f"https://www.youtube.com/results?search_query={prim_channel}"
            longest_binge = {
                'date': sess_min_t.strftime('%d %b %Y'),
                'duration_mins': duration_mins,
                'video_count': max_sess_count,
                'primary_channel': prim_channel,
                'primary_channel_url': prim_ch_url
            }
            
    # 14. Nostalgia Channels (Forgotten Favorites)
    nostalgia_channels = []
    if not watch_df.empty:
        cutoff_date = watch_df['timestamp'].max() - pd.Timedelta(days=180)
        recent_df = watch_df[watch_df['timestamp'] >= cutoff_date]
        older_df = watch_df[watch_df['timestamp'] < cutoff_date]
        
        recent_channels = set(recent_df['channel'].dropna().str.lower().str.strip())
        older_stats = older_df.groupby('channel').size().reset_index(name='old_views')
        older_stats = older_stats[older_stats['old_views'] >= 5]
        older_urls = older_df.groupby('channel')['channel_url'].first().to_dict()
        
        for idx, row in older_stats.iterrows():
            ch_name = row['channel']
            ch_lower = str(ch_name).lower().strip()
            if ch_lower not in recent_channels:
                ch_url = older_urls.get(ch_name) or f"https://www.youtube.com/results?search_query={ch_name}"
                nostalgia_channels.append({
                    'channel': ch_name,
                    'channel_url': ch_url,
                    'past_views': int(row['old_views'])
                })
        nostalgia_channels = sorted(nostalgia_channels, key=lambda x: x['past_views'], reverse=True)[:10]
        
    # 15. Categorization distribution with refined keywords
    categories = {
        'Tech & AI': ['tech', 'ai', 'python', 'programming', 'code', 'software', 'hardware', 'app', 'developer', 'chatgpt', 'science', 'computer', 'review', 'unboxing', 'robot', 'ipad', 'iphone', 'macbook', 'samsung', 'gadget', 'nvidia', 'intel', 'amd'],
        'Vlogs & Lifestyle': ['vlog', 'daily', 'life', 'travel', 'routine', 'home', 'family', 'couple', 'cooking', 'recipe', 'lifestyle', 'vlogger', 'day in', 'what i eat', 'tour', 'cleaning', 'fashion', 'makeup'],
        'Sports': ['sports', 'football', 'cricket', 'basketball', 'soccer', 'tennis', 'ufc', 'match', 'goals', 'highlights', 'nba', 'ipl', 'athlete', 'wwe', 'f1', 'formula 1', 'baseball', 'gym', 'workout', 'training'],
        'Gaming': ['game', 'play', 'walkthrough', 'minecraft', 'gta', 'xbox', 'playstation', 'nintendo', 'gaming', 'streamer', 'fortnite', 'pubg', 'cod', 'csgo', 'esports', 'twitch', 'mods'],
        'Finance': ['crypto', 'invest', 'money', 'stock', 'finance', 'economy', 'wealth', 'bitcoin', 'market', 'trade', 'trading', 'portfolio', 'dividend', 'passive income', 'real estate'],
        'Education': ['how to', 'tutorial', 'learn', 'course', 'science', 'history', 'explain', 'why', 'space', 'math', 'physics', 'school', 'docu', 'documentary', 'biography', 'facts', 'ted', 'lecture'],
        'Music': ['music', 'song', 'cover', 'album', 'remix', 'dj', 'lofi', 'lyrics', 'singing', 'karaoke', 'instrumental', 'soundtrack', 'concert', 'official video', 'live performance'],
        'Entertainment': ['funny', 'comedy', 'movie', 'trailer', 'prank', 'react', 'show', 'series', 'clip', 'meme', 'drama', 'compilation', 'fails', 'cartoon', 'anime', 'tiktok']
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

    # 16. Focus vs. Distraction Index (%)
    focus_score = 70.0
    if not search_df.empty and not watch_df.empty:
        focused_events = 0
        distracted_events = 0
        edu_search_keywords = {'how', 'why', 'tutorial', 'python', 'code', 'learn', 'course', 'explain', 'vs', 'science', 'what', 'programming', 'github', 'install', 'setup', 'doc', 'api', 'error', 'debug'}
        
        searches = search_df[['timestamp', 'query']].dropna().sort_values('timestamp').to_dict('records')
        watches = watch_df[['timestamp', 'category']].dropna().sort_values('timestamp').to_dict('records')
        
        w_idx = 0
        n_watches = len(watches)
        
        for s in searches:
            s_t = s['timestamp']
            query_lower = str(s['query']).lower()
            is_edu_search = any(kw in query_lower for kw in edu_search_keywords)
            if not is_edu_search:
                continue
                
            while w_idx < n_watches and watches[w_idx]['timestamp'] < s_t:
                w_idx += 1
                
            curr_w_idx = w_idx
            while curr_w_idx < n_watches and (watches[curr_w_idx]['timestamp'] - s_t).total_seconds() <= 1800:
                cat = watches[curr_w_idx]['category']
                if cat in ['Education', 'Tech & AI']:
                    focused_events += 1
                elif cat in ['Entertainment', 'Music', 'Gaming']:
                    distracted_events += 1
                curr_w_idx += 1
                
        total_events = focused_events + distracted_events
        if total_events > 0:
            focus_score = round((focused_events / total_events) * 100, 1)
        else:
            edu_tech_views = len(watch_df[watch_df['category'].isin(['Education', 'Tech & AI'])])
            focus_score = round((edu_tech_views / len(watch_df)) * 100, 1) if len(watch_df) > 0 else 70.0

    # Compile JSON summary
    summary = {
        'total_watched': len(watch_df),
        'total_searches': len(search_df),
        'unique_channels': watch_df['channel'].nunique(),
        'avg_views_per_day': float(watch_df.groupby('date').size().mean()) if len(watch_df) > 0 else 0.0,
        'estimated_hours': float(estimated_hours),
        'watch_start_date': start_date_str,
        'watch_end_date': end_date_str,
        'loop_percentage': float(loop_percentage),
        'total_sessions': int(total_sessions),
        'binge_sessions': int(binge_count),
        'burnout_alert_days': int(burnout_days),
        'subs_overlap_pct': float(subs_overlap_pct),
        'subs_watched_pct': float(subs_watched_pct),
        'top_channels': top_comfort_list,
        'top_videos': top_videos_list,
        'ghost_subscriptions': ghost_subscriptions,
        'ghost_count': int(ghost_count),
        'late_night_pct': float(late_night_pct),
        'longest_binge': longest_binge,
        'nostalgia_channels': nostalgia_channels,
        'focus_score': float(focus_score),
        'yoy_trend': yoy_trend,
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
        
    uploaded_files = request.files.getlist('file')
    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        return jsonify({'error': 'No file selected for uploading'}), 400
        
    # Clean the extracted folder first
    extract_path = os.path.join(user_dir, 'extracted')
    if os.path.exists(extract_path):
        import shutil
        try:
            shutil.rmtree(extract_path)
        except Exception:
            pass
    os.makedirs(extract_path, exist_ok=True)
    
    # Process each zip file
    zip_processed = 0
    for i, file in enumerate(uploaded_files):
        if file and file.filename.endswith('.zip'):
            zip_path = os.path.join(user_dir, f'takeout_{i}.zip')
            file.save(zip_path)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                zip_processed += 1
            except Exception as e:
                return jsonify({'error': f'Failed to extract zip {file.filename}: {str(e)}'}), 500
            finally:
                # Clean up temporary zip file
                if os.path.exists(zip_path):
                    try:
                        os.remove(zip_path)
                    except Exception:
                        pass
                        
    if zip_processed == 0:
        return jsonify({'error': 'No valid .zip archives were processed.'}), 400
        
    # Locate all watch, search, and subscriptions files
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
                
    # 1. Parse and merge watch history files
    watch_dfs = []
    for wf in watch_files:
        try:
            df_part = parse_watch_regex(wf)
            if not df_part.empty:
                watch_dfs.append(df_part)
        except Exception as e:
            print(f"Error parsing watch history {wf}:", e)
            
    if watch_dfs:
        try:
            watch_df = pd.concat(watch_dfs, ignore_index=True)
            # Remove duplicates based on title, channel, raw_timestamp
            watch_df = watch_df.drop_duplicates(subset=['title', 'channel', 'raw_timestamp'])
            # Parse datetime and sort chronologically
            watch_df['timestamp'] = watch_df['raw_timestamp'].apply(parse_tz_datetime)
            watch_df = watch_df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            watch_df.to_csv(os.path.join(user_dir, "watch_history.csv"), index=False, encoding='utf-8')
        except Exception as e:
            print("Error merging watch histories:", e)
            
    # 2. Parse and merge search history files
    search_dfs = []
    for sf in search_files:
        try:
            df_part = parse_search_regex(sf)
            if not df_part.empty:
                search_dfs.append(df_part)
        except Exception as e:
            print(f"Error parsing search history {sf}:", e)
            
    if search_dfs:
        try:
            search_df = pd.concat(search_dfs, ignore_index=True)
            search_df = search_df.drop_duplicates(subset=['query', 'raw_timestamp'])
            search_df['timestamp'] = search_df['raw_timestamp'].apply(parse_tz_datetime)
            search_df = search_df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            search_df.to_csv(os.path.join(user_dir, "search_history.csv"), index=False, encoding='utf-8')
        except Exception as e:
            print("Error merging search histories:", e)
            
    # 3. Parse and merge subscriptions files
    subs_dfs = []
    for sub_f in subs_files:
        try:
            df_part = pd.read_csv(sub_f)
            if not df_part.empty:
                subs_dfs.append(df_part)
        except Exception as e:
            print(f"Error parsing subscriptions {sub_f}:", e)
            
    if subs_dfs:
        try:
            subs_df = pd.concat(subs_dfs, ignore_index=True)
            id_col = None
            for col in subs_df.columns:
                if col.lower() in ['channel id', 'channel_id', 'channel title', 'channel_title']:
                    id_col = col
                    break
            if id_col:
                subs_df = subs_df.drop_duplicates(subset=[id_col])
            else:
                subs_df = subs_df.drop_duplicates()
            subs_df.to_csv(os.path.join(user_dir, "subscriptions.csv"), index=False, encoding='utf-8')
        except Exception as e:
            print("Error merging subscriptions:", e)
            
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

@app.route('/api/check_data')
def check_data():
    user_dir = get_user_dir()
    summary_path = os.path.join(user_dir, "analysis_summary.json")
    return jsonify({'has_data': os.path.exists(summary_path)})

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
    app.run(host='0.0.0.0', port=6767, debug=True)

