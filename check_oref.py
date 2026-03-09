"""Quick script to check Oref API status and recent alerts."""
import requests
import json

headers = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Check real-time alerts
print("=== REAL-TIME ALERTS ===")
try:
    r = requests.get("https://www.oref.org.il/WarningMessages/alert/alerts.json", headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    clean = r.text.strip().lstrip("\ufeff").strip()
    print(f"Response length: {len(clean)}")
    if clean:
        try:
            data = json.loads(clean)
            print(f"Parsed: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        except Exception:
            print(f"Raw: [{clean[:200]}]")
    else:
        print("EMPTY - no active alerts right now")
except Exception as e:
    print(f"Error: {e}")

print()
print("=== HISTORY API (last 10) ===")
try:
    r = requests.get("https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json", headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200 and r.text.strip():
        data = r.json()
        print(f"Total alerts today: {len(data)}")
        for a in data[:10]:
            date = a.get("alertDate", "?")
            cat = a.get("category", "?")
            cat_desc = a.get("category_desc", "?")
            area = a.get("data", "?")
            title = a.get("title", "?")
            print(f"  {date} | cat={cat} | {cat_desc} | {title} | area={area}")
    else:
        print(f"Empty or error: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
