import os
import re
import pandas as pd
from bs4 import BeautifulSoup
import sys
import glob

# Ensure output handles unicode
sys.stdout.reconfigure(encoding='utf-8')

watch_history_path = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music\history\watch-history.html"
search_history_path = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music\history\search-history.html"
subscriptions_path = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music\subscriptions\subscriptions.csv"
comments_path = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music\comments\comments.csv"

output_dir = r"d:\New folder\processed_data"
os.makedirs(output_dir, exist_ok=True)

# Define regex or parsers for watch history
def parse_watch_history_fast(file_path):
    print(f"Reading and parsing watch history: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    cells = soup.find_all('div', class_='content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1')
    
    records = []
    for cell in cells:
        links = cell.find_all('a')
        text = cell.get_text(separator='|').strip()
        parts = [p.strip() for p in text.split('|') if p.strip()]
        
        # Structure is usually:
        # "Watched" | "Video Title" | "Channel Name" | "Timestamp"
        # Let's extract links
        video_title = None
        video_url = None
        channel_name = None
        channel_url = None
        timestamp = None
        
        if len(links) >= 1:
            video_title = links[0].text.strip()
            video_url = links[0].get('href', '').strip()
        if len(links) >= 2:
            channel_name = links[1].text.strip()
            channel_url = links[1].get('href', '').strip()
            
        # Extract timestamp from parts
        # The timestamp is usually the last part
        if len(parts) >= 1:
            timestamp = parts[-1]
            
        records.append({
            'title': video_title,
            'url': video_url,
            'channel': channel_name,
            'channel_url': channel_url,
            'raw_timestamp': timestamp
        })
        
    df = pd.DataFrame(records)
    print(f"Parsed {len(df)} watch history records.")
    return df

def parse_search_history_fast(file_path):
    print(f"Reading and parsing search history: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    soup = BeautifulSoup(content, 'html.parser')
    cells = soup.find_all('div', class_='content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1')
    
    records = []
    for cell in cells:
        links = cell.find_all('a')
        text = cell.get_text(separator='|').strip()
        parts = [p.strip() for p in text.split('|') if p.strip()]
        
        query = None
        query_url = None
        timestamp = None
        
        if len(links) >= 1:
            query = links[0].text.strip()
            query_url = links[0].get('href', '').strip()
            
        if len(parts) >= 1:
            timestamp = parts[-1]
            
        records.append({
            'query': query,
            'query_url': query_url,
            'raw_timestamp': timestamp
        })
        
    df = pd.DataFrame(records)
    print(f"Parsed {len(df)} search history records.")
    return df

# Perform parsing
watch_df = parse_watch_history_fast(watch_history_path)
watch_df.to_csv(os.path.join(output_dir, "watch_history.csv"), index=False, encoding='utf-8')

search_df = parse_search_history_fast(search_history_path)
search_df.to_csv(os.path.join(output_dir, "search_history.csv"), index=False, encoding='utf-8')

print("Parsing completed and saved to processed_data directory.")
