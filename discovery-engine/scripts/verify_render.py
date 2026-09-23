import os
import sys
import re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from dashboard.api import app

client = TestClient(app)
res = client.get('/')
html = res.text

print("=== 1. TOP 5 BREAK REASONS RENDERED ===")
reasons = re.findall(r'<h3 class="font-title-sm[^"]*">([^<]+)</h3>', html)
volumes = re.findall(r'<span class="font-semibold text-on-surface">([^<]+)</span>', html)
for i in range(min(len(reasons), len(volumes))):
    print(f"Card #{i+1}: {reasons[i]} | {volumes[i]}")

print("\n=== 2. CARD #1 BREAK REASON CHECK ===")
if "#1 Break Reason" in html:
    print("WARNING: '#1 Break Reason' card still present in HTML!")
else:
    print("CONFIRMED: '#1 Break Reason' card has been completely removed.")

print("\n=== 3. SALT PATROL / SPAM CHECK ===")
if "Salt Patrol" in html:
    print("WARNING: 'Salt Patrol' still found in HTML!")
else:
    print("CONFIRMED: 'Salt Patrol' and spam reviews are not in HTML.")

print("\n=== 4. SAMPLE VERBATIM REVIEWS RENDERED ===")
reviews = re.findall(r'"([^"\n\r]{30,120})[^"]*"\s*</p>', html)
for i, rev in enumerate(reviews[:4]):
    print(f"Review #{i+1}: \"{rev.strip()}...\"")
