import os

source_file = r"C:\Users\shrut\OneDrive\Documents\Google Photo\stitch_dashboard\code.html"
target_dir = r"C:\Users\shrut\OneDrive\Documents\Google Photo\discovery-engine\dashboard\templates"
target_file = os.path.join(target_dir, "index.html")

os.makedirs(target_dir, exist_ok=True)

with open(source_file, "r", encoding="utf-8") as f:
    content = f.read()

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully converted and saved to {target_file}")
