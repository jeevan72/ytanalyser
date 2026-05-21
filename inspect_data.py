import os
import glob

base_dir = r"d:\New folder\takeout_extracted"
files = glob.glob(os.path.join(base_dir, "**", "*"), recursive=True)

print("Files in extracted directory:")
for f in files:
    if os.path.isfile(f):
        print(f"{os.path.relpath(f, base_dir)} - {os.path.getsize(f)} bytes")
