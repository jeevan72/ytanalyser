import os
import sys
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

sys.stdout.reconfigure(encoding='utf-8')

# Paths
processed_dir = r"d:\New folder\processed_data"
takeout_dir = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music"
artifact_dir = r"C:\Users\jeeva\.gemini\antigravity\brain\c7732a9d-2805-4dc2-9742-507f36a223ee"
images_dir = os.path.join(artifact_dir, "images")
os.makedirs(images_dir, exist_ok=True)

watch_path = os.path.join(processed_dir, "watch_history.csv")
search_path = os.path.join(processed_dir, "search_history.csv")
subs_path = os.path.join(takeout_dir, "subscriptions", "subscriptions.csv")

# We might have comments files
comments_files = [
    os.path.join(takeout_dir, "comments", "comments.csv"),
    os.path.join(takeout_dir, "comments", "comments(1).csv"),
    os.path.join(takeout_dir, "comments", "comments(2).csv")
]

print("Starting deep behavior analysis script...")

if not os.path.exists(watch_path):
    print("Error: watch_history.csv not found! Execute parse_data.py first.")
    sys.exit(1)

# Helper function to parse timestamps with timezone codes
tz_offsets = {
    'IST': '+0530', 'EDT': '-0400', 'EST': '-0500',
    'PDT': '-0700', 'PST': '-0800', 'UTC': '+0000',
    'GMT': '+0000', 'BST': '+0100', 'CEST': '+0200',
    'CET': '+0100'
}

def parse_tz_datetime(s):
    if pd.isna(s) or not isinstance(s, str):
        return pd.NaT
    # Strip non-standard timezone names
    parts = s.strip().split()
    if len(parts) < 2:
        return pd.NaT
    tz = parts[-1]
    # Check if last part is timezone letter code
    if tz in tz_offsets:
        offset = tz_offsets[tz]
        s_clean = " ".join(parts[:-1]) + " " + offset
        try:
            return pd.to_datetime(s_clean, format='%d %b %Y, %H:%M:%S %z', errors='coerce')
        except Exception:
            pass
    # Fallback to dateutil/pandas parser
    return pd.to_datetime(s, errors='coerce')

# 1. LOAD DATA
watch_df = pd.read_csv(watch_path)
search_df = pd.read_csv(search_path)

# Apply timezone-aware parsing
print("Parsing watch timestamps...")
watch_df['timestamp'] = watch_df['raw_timestamp'].apply(parse_tz_datetime)
watch_df = watch_df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)

print("Parsing search timestamps...")
search_df['timestamp'] = search_df['raw_timestamp'].apply(parse_tz_datetime)
search_df = search_df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)

# Try loading subscriptions
subs_df = pd.DataFrame()
if os.path.exists(subs_path):
    try:
        subs_df = pd.read_csv(subs_path)
        print(f"Loaded {len(subs_df)} subscriptions.")
    except Exception as e:
        print("Could not load subscriptions:", e)

# Try loading comments
comments_df = pd.DataFrame()
comment_list = []
for cp in comments_files:
    if os.path.exists(cp):
        try:
            cdf = pd.read_csv(cp)
            comment_list.append(cdf)
        except Exception:
            pass
if comment_list:
    comments_df = pd.concat(comment_list, ignore_index=True)
    print(f"Loaded {len(comments_df)} comments.")

# 2. FEATURE ENGINEERING
# Time features
watch_df['year'] = watch_df['timestamp'].dt.year
watch_df['month'] = watch_df['timestamp'].dt.month
watch_df['day_of_week'] = watch_df['timestamp'].dt.day_name()
watch_df['hour'] = watch_df['timestamp'].dt.hour
watch_df['date'] = watch_df['timestamp'].dt.date

# 3. ANALYSIS & VISUALIZATION GENERATION
# Set plotting styles
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']

# --- FIGURE 1: Volume over Time ---
print("Generating Plot 1: Volume over time...")
yearly_counts = watch_df.groupby('year').size().reset_index(name='videos_watched')
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(data=yearly_counts, x='year', y='videos_watched', hue='year', palette="viridis", legend=False, ax=ax)
ax.set_title("Year-over-Year Video Consumption Volume", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("Year", fontsize=12)
ax.set_ylabel("Number of Videos Watched", fontsize=12)
plt.tight_layout()
fig.savefig(os.path.join(images_dir, "volume_over_time.png"), dpi=150)
plt.close(fig)

# --- FIGURE 2: Peak Engagement Circadian Heatmap ---
print("Generating Plot 2: Heatmap...")
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
heatmap_data = watch_df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
heatmap_data = heatmap_data.reindex(days_order)
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(heatmap_data, cmap="magma", cbar=True, ax=ax, cbar_kws={'label': 'Watch Count'})
ax.set_title("Circadian Viewing Pattern (Day of Week vs. Hour of Day)", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("Hour of Day (Local Time)", fontsize=12)
ax.set_ylabel("Day of Week", fontsize=12)
plt.tight_layout()
fig.savefig(os.path.join(images_dir, "circadian_heatmap.png"), dpi=150)
plt.close(fig)

# --- FIGURE 3: Category Distribution ---
print("Generating Plot 3: Categories...")
categories = {
    'Technology & AI': ['tech', 'ai', 'python', 'programming', 'code', 'software', 'hardware', 'developer', 'chatgpt', 'machine learning', 'data science', 'css', 'javascript', 'html', 'git', 'computer', 'rust', 'c++', 'linux'],
    'Gaming': ['game', 'play', 'walkthrough', 'xbox', 'playstation', 'nintendo', 'minecraft', 'gta', 'steam', 'gamer', 'cod', 'csgo', 'fortnite', 'esports', 'twitch'],
    'Finance & Business': ['crypto', 'invest', 'money', 'stock', 'finance', 'economy', 'wealth', 'trading', 'bitcoin', 'ethereum', 'market', 'business', 'startup', 'passive income'],
    'Education & Science': ['how to', 'tutorial', 'learn', 'course', 'science', 'history', 'explain', 'why', 'space', 'math', 'physics', 'documentary', 'mit', 'stanford', 'lectures'],
    'Entertainment & Vlogs': ['funny', 'comedy', 'movie', 'trailer', 'vlog', 'prank', 'react', 'show', 'clip', 'drama', 'meme', 'beast', 'challenge'],
    'Music & Audio': ['music', 'song', 'cover', 'live', 'album', 'remix', 'dj', 'lofi', 'rap', 'concert', 'beat', 'lyric', 'soundtrack', 'instrumental'],
    'Productivity & Design': ['productivity', 'design', 'ui', 'ux', 'edit', 'figma', 'notion', 'focus', 'motivation', 'time management', 'minimalism']
}

def classify_title(title):
    if pd.isna(title) or not isinstance(title, str):
        return 'Other'
    title_lower = title.lower()
    for cat, keywords in categories.items():
        if any(kw in title_lower for kw in keywords):
            return cat
    return 'Other'

watch_df['category'] = watch_df['title'].apply(classify_title)
category_counts = watch_df['category'].value_counts()

fig, ax = plt.subplots(figsize=(8, 8))
colors = sns.color_palette("Set2", len(category_counts))
ax.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%', startangle=140, colors=colors, wedgeprops={'edgecolor': 'white'})
ax.set_title("Distribution of Watched Content Categories", fontsize=14, fontweight='bold', pad=15)
plt.tight_layout()
fig.savefig(os.path.join(images_dir, "category_distribution.png"), dpi=150)
plt.close(fig)

# --- FIGURE 4: Exploration vs Exploitation (Novelty Ratio) ---
print("Generating Plot 4: Exploration...")
# Track cumulative unique channels
watch_df['is_new_channel'] = ~watch_df.duplicated(subset=['channel'])
monthly_novelty = watch_df.groupby([watch_df['timestamp'].dt.to_period('M')])['is_new_channel'].mean().reset_index()
monthly_novelty['timestamp_dt'] = monthly_novelty['timestamp'].dt.to_timestamp()

fig, ax = plt.subplots(figsize=(10, 5))
sns.lineplot(data=monthly_novelty, x='timestamp_dt', y='is_new_channel', marker='o', color='crimson', ax=ax)
ax.set_title("Exploration Score Over Time (Ratio of New Channels Discovered)", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("Time (Monthly)", fontsize=12)
ax.set_ylabel("Novel Channel Ratio (Higher = More Exploration)", fontsize=12)
ax.set_ylim(0, 1.0)
plt.tight_layout()
fig.savefig(os.path.join(images_dir, "exploration_score.png"), dpi=150)
plt.close(fig)

# --- FIGURE 5: Herfindahl-Hirschman Herfindahl Index (Channel Concentration) ---
print("Generating Plot 5: Channel concentration...")
# Herfindahl-Hirschman Index (HHI) for channel concentration.
# HHI = sum(market_shares^2). In our context, shares of channel views.
# Values < 1500 (competitive/diverse), 1500-2500 (moderate concentration), > 2500 (high concentration).
def calculate_hhi(group):
    shares = group.value_counts(normalize=True)
    return (shares ** 2).sum() * 10000

monthly_hhi = watch_df.groupby([watch_df['timestamp'].dt.to_period('M')])['channel'].apply(calculate_hhi).reset_index(name='hhi')
monthly_hhi['timestamp_dt'] = monthly_hhi['timestamp'].dt.to_timestamp()

fig, ax = plt.subplots(figsize=(10, 5))
sns.lineplot(data=monthly_hhi, x='timestamp_dt', y='hhi', marker='s', color='navy', ax=ax)
# Add concentration thresholds
ax.axhline(1500, color='green', linestyle='--', alpha=0.5, label='Diverse / High Exploration (<1500)')
ax.axhline(2500, color='orange', linestyle='--', alpha=0.5, label='Moderate Concentration (1500-2500)')
ax.axhline(5000, color='red', linestyle='--', alpha=0.5, label='High Concentration / Echo Chamber (>2500)')
ax.set_title("Algorithmic Concentration (HHI) Over Time", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("Time (Monthly)", fontsize=12)
ax.set_ylabel("HHI (Concentration Score)", fontsize=12)
ax.legend(loc='upper right')
plt.tight_layout()
fig.savefig(os.path.join(images_dir, "channel_concentration.png"), dpi=150)
plt.close(fig)

# 4. RECOMMENDATION LOOPS & ECHO CHAMBERS
# Look for consecutive views of the same channel (a loop index)
watch_df['prev_channel'] = watch_df['channel'].shift(1)
watch_df['is_loop'] = (watch_df['channel'] == watch_df['prev_channel']).astype(int)
loop_percentage = watch_df['is_loop'].mean() * 100

# Binge Sessions
# Videos watched within 20 mins of each other
watch_df['time_gap'] = watch_df['timestamp'].diff().dt.total_seconds().fillna(0)
# A new session starts if gap > 20 mins (1200 seconds)
watch_df['new_session'] = (watch_df['time_gap'] > 1200).astype(int)
watch_df['session_id'] = watch_df['new_session'].cumsum()
session_sizes = watch_df.groupby('session_id').size()
binge_sessions = session_sizes[session_sizes >= 5]
total_sessions = len(session_sizes)
binge_count = len(binge_sessions)

# Top Channels
top_channels = watch_df['channel'].value_counts().head(10).reset_index()
top_channels.columns = ['channel', 'views']

# Subscriptions overlap
subs_overlap_pct = 0.0
subs_watched_pct = 0.0
if not subs_df.empty:
    # Find channel title column case-insensitively
    title_col = None
    for col in subs_df.columns:
        if col.lower() in ['channel title', 'channel_title']:
            title_col = col
            break
    if title_col:
        subs_channels = set(subs_df[title_col].dropna().str.lower().str.strip())
        watched_channels = set(watch_df['channel'].dropna().str.lower().str.strip())
        
        # What percentage of watched channels are subscribed?
        overlap = watched_channels.intersection(subs_channels)
        subs_overlap_pct = (len(overlap) / len(watched_channels)) * 100 if len(watched_channels) > 0 else 0
        
        # What percentage of watch events belong to subscribed channels?
        watch_df['is_subscribed'] = watch_df['channel'].dropna().str.lower().str.strip().isin(subs_channels)
        subs_watched_pct = watch_df['is_subscribed'].mean() * 100

# 5. DUST OFF THE EXECUTIVE SUMMARY STATS
total_watched = len(watch_df)
total_searches = len(search_df)
unique_channels = watch_df['channel'].nunique()
avg_views_per_day = watch_df.groupby('date').size().mean()

print(f"Total Watched: {total_watched}")
print(f"Unique Channels: {unique_channels}")
print(f"Loop percentage: {loop_percentage:.2f}%")
print(f"Binge sessions: {binge_count} of {total_sessions}")

# Print JSON summary
import json
summary = {
    'total_watched': total_watched,
    'total_searches': total_searches,
    'unique_channels': unique_channels,
    'avg_views_per_day': float(avg_views_per_day) if not pd.isna(avg_views_per_day) else 0.0,
    'loop_percentage': float(loop_percentage),
    'total_sessions': int(total_sessions),
    'binge_sessions': int(binge_count),
    'subs_overlap_pct': float(subs_overlap_pct),
    'subs_watched_pct': float(subs_watched_pct),
    'top_channels': top_channels.to_dict(orient='records'),
    'category_counts': category_counts.to_dict()
}

with open(os.path.join(processed_dir, "analysis_summary.json"), 'w', encoding='utf-8') as sf:
    json.dump(summary, sf, indent=4)

print("Analysis script finished successfully and summary saved.")
