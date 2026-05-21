import os
import shutil
import unittest
import pandas as pd
import sys

# Add directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import parse_watch_regex, parse_search_regex, analyze_user_data, USERS_DIR

class TestYouTubeAnalytics(unittest.TestCase):
    def setUp(self):
        # Create a mock user directory
        self.user_id = "test_user_verification"
        self.user_dir = os.path.join(USERS_DIR, self.user_id)
        os.makedirs(self.user_dir, exist_ok=True)
        
        # Paths to the zip file
        self.zip_path = r"d:\New folder\takeout-20260509T082807Z-3-001.zip"
        
    def test_extraction_and_analysis(self):
        # Simulate extraction of the zip file
        import zipfile
        extract_path = os.path.join(self.user_dir, 'extracted')
        os.makedirs(extract_path, exist_ok=True)
        
        print("\nExtracting test zip...")
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        # Locate files
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
                    
        self.assertTrue(len(watch_files) > 0, "No watch history files found")
        self.assertTrue(len(search_files) > 0, "No search history files found")
        self.assertTrue(len(subs_files) > 0, "No subscriptions files found")
        
        # Sort by size to pick the largest
        watch_files = sorted(watch_files, key=os.path.getsize, reverse=True)
        search_files = sorted(search_files, key=os.path.getsize, reverse=True)
        subs_files = sorted(subs_files, key=os.path.getsize, reverse=True)
        
        print(f"Watch history file: {watch_files[0]} (size: {os.path.getsize(watch_files[0])} bytes)")
        print(f"Search history file: {search_files[0]} (size: {os.path.getsize(search_files[0])} bytes)")
        
        # Parse watch history
        print("Parsing watch history...")
        watch_df = parse_watch_regex(watch_files[0])
        print(f"Parsed {len(watch_df)} watch records.")
        self.assertFalse(watch_df.empty, "Watch history dataframe is empty")
        
        # Save CSV
        watch_df.to_csv(os.path.join(self.user_dir, "watch_history.csv"), index=False, encoding='utf-8')
        
        # Parse search history
        print("Parsing search history...")
        search_df = parse_search_regex(search_files[0])
        print(f"Parsed {len(search_df)} search records.")
        self.assertFalse(search_df.empty, "Search history dataframe is empty")
        search_df.to_csv(os.path.join(self.user_dir, "search_history.csv"), index=False, encoding='utf-8')
        
        # Copy subscriptions
        shutil.copyfile(subs_files[0], os.path.join(self.user_dir, "subscriptions.csv"))
        
        # Run analysis
        print("Running user data analysis...")
        summary = analyze_user_data(self.user_dir)
        self.assertIsNotNone(summary, "Analysis summary is None")
        
        print("\n=== VERIFICATION RESULTS ===")
        print("Analysis completed successfully!")
        print("Total watched videos:", summary['total_watched'])
        print("Unique channels:", summary['unique_channels'])
        print("Average daily views:", summary['avg_views_per_day'])
        print("Binge sessions count:", summary['binge_sessions'])
        print("Burnout alert days:", summary['burnout_alert_days'])
        print("Loop percentage:", summary['loop_percentage'])
        print("Subscriptions overlap %:", summary['subs_overlap_pct'])
        print("Subscriptions watched %:", summary['subs_watched_pct'])
        print("Top 3 comfort channels:")
        for idx, ch in enumerate(summary['top_channels'][:3]):
            print(f"  #{idx+1} {ch['channel']}: score={ch['comfort_score']:.1f}, views={ch['views']}, loops={ch['loops']}")
        print("Category Counts:")
        for cat, cnt in summary['category_counts'].items():
            print(f"  {cat}: {cnt}")
        print("Search Intents:")
        for intent, cnt in summary['search_intents'].items():
            print(f"  {intent}: {cnt}")
            
    def tearDown(self):
        # Clean up test user directory
        if os.path.exists(self.user_dir):
            shutil.rmtree(self.user_dir)

if __name__ == '__main__':
    unittest.main()
