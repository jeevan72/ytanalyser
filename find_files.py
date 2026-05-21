import os
import glob

base = r"d:\New folder"
files = glob.glob(os.path.join(base, "**", "*.json"), recursive=True)
for f in files:
    print(f)
    
print("Csv files:")
files_csv = glob.glob(os.path.join(base, "**", "*.csv"), recursive=True)
for f in files_csv:
    if "takeout_extracted" not in f:
        print(f)
