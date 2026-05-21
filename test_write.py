import os
out_dir = r"d:\New folder\processed_data"
os.makedirs(out_dir, exist_ok=True)
file_path = os.path.join(out_dir, "test.txt")
with open(file_path, "w") as f:
    f.write("hello")
print("Exists:", os.path.exists(file_path))
print("Listdir:", os.listdir(out_dir))
