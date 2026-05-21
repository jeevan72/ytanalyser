import os
import re
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

watch_history_path = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music\history\watch-history.html"
search_history_path = r"d:\New folder\takeout_extracted\Takeout\YouTube and YouTube Music\history\search-history.html"
output_dir = r"d:\New folder\processed_data"
os.makedirs(output_dir, exist_ok=True)

# Regex for Watch History
# A typical cell is:
# <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
#  Watched
#  <a href="URL">Title</a>
#  <br/>
#  <a href="URL">Channel</a>
#  <br/>
#  Timestamp
#  <br/>
# </div>
def parse_watch_regex(file_path):
    print(f"Regex parsing watch history: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Find all divs of class content-cell
    # Using a non-greedy dotall regex to capture each cell
    cell_re = re.compile(r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">([\s\S]*?)</div>')
    link_re = re.compile(r'<a href="([^"]+)">([\s\S]*?)</a>')
    
    records = []
    cells = cell_re.findall(html)
    print(f"Found {len(cells)} cells total.")
    
    for cell in cells:
        if "Watched" not in cell:
            continue
            
        links = link_re.findall(cell)
        # Strip html tags from link text
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
            
        # The timestamp is usually before the end of the div, after the last <br/> or link
        # Let's extract all text parts
        parts = [p.strip() for p in re.split(r'<br/?>', cell) if p.strip()]
        # The timestamp is usually the last part, before or after tag cleaning
        timestamp = None
        if len(parts) >= 1:
            # clean any remaining html tags from the last part
            timestamp = re.sub(r'<[^>]+>', '', parts[-1]).strip()
            # If the timestamp contains "Watched", it's not the timestamp (e.g. malformed cell)
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
    print(f"Parsed {len(df)} watch history records using regex.")
    return df

def parse_search_regex(file_path):
    print(f"Regex parsing search history: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
        
    cell_re = re.compile(r'<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">([\s\S]*?)</div>')
    link_re = re.compile(r'<a href="([^"]+)">([\s\S]*?)</a>')
    
    records = []
    cells = cell_re.findall(html)
    print(f"Found {len(cells)} cells total.")
    
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
    print(f"Parsed {len(df)} search history records using regex.")
    return df

# Run regex parsers
watch_df = parse_watch_regex(watch_history_path)
watch_df.to_csv(os.path.join(output_dir, "watch_history.csv"), index=False, encoding='utf-8')

search_df = parse_search_regex(search_history_path)
search_df.to_csv(os.path.join(output_dir, "search_history.csv"), index=False, encoding='utf-8')

print("Regex parsing completed successfully!")
print("Listing files in output directory:", os.listdir(output_dir))
